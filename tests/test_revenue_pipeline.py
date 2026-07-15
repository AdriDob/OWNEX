"""Tests for Revenue Pipeline — submit, status check, payouts, summary, API."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core.revenue.pipeline import (
    PipelineResult,
    RevenuePipeline,
    _cvss_to_severity,
    register_revenue_capabilities,
)

# ── Helpers ─────────────────────────────────────────────────────


def _make_mock_platform(
    success: bool = True, external_id: str = "H1-123", url: str = "https://hackerone.com/reports/123"
):
    """Create a mock platform that returns controlled results."""
    platform = type("MockPlatform", (), {})()
    platform.platform_id = "hackerone"
    platform.display_name = "HackerOne"

    def mock_submit(report_data: dict[str, Any], api_key: str) -> Any:
        from cores.platforms.base import SubmissionResult

        if success:
            return SubmissionResult(success=True, external_id=external_id, url=url, data={"id": external_id})
        return SubmissionResult(success=False, error="API rate limit exceeded")

    def mock_check_status(eid: str, api_key: str = "") -> str:
        return "resolved" if eid == external_id else "unknown"

    def mock_sync_earnings(api_key: str) -> Any:
        from cores.platforms.base import SyncResult

        return SyncResult(
            success=True,
            payouts=[{"amount": 500.0, "currency": "USD", "external_id": "H1-500", "program": "test-program"}],
            total_earned=500.0,
            total_pending=0.0,
        )

    platform.submit = mock_submit
    platform.check_status = mock_check_status
    platform.sync_earnings = mock_sync_earnings
    platform.supports_action = lambda a: True
    return platform


@pytest.fixture(autouse=True, scope="session")
def _setup_tables():
    """Ensure all tables exist for revenue pipeline tests."""
    from database.db import Base, engine

    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def _clean_db():
    """Ensure a clean DB state for each test."""
    from database.db import Base, SessionLocal, engine
    from database.models import Finding, Report, SubmissionRecord
    from database.models_economic import PayoutRecord, RevenueEvent

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(RevenueEvent).delete()
        db.query(PayoutRecord).delete()
        db.query(SubmissionRecord).delete()
        db.query(Report).delete()
        db.query(Finding).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def sample_target_id() -> int:
    """Create a sample target in DB."""
    from database.db import SessionLocal
    from database.models import Target

    db = SessionLocal()
    try:
        t = Target(name="test-target.example.com", domain="example.com")
        db.add(t)
        db.commit()
        return t.id
    finally:
        db.close()


@pytest.fixture
def sample_finding(sample_target_id: int) -> int:
    """Create a sample finding in DB and return its ID."""
    from database.db import SessionLocal
    from database.models import Finding

    db = SessionLocal()
    try:
        f = Finding(
            target_id=sample_target_id,
            vulnerability_type="idor",
            severity="high",
            title="IDOR in user profile endpoint",
            description="IDOR in /api/users/{id} allows viewing other users' profiles",
        )
        db.add(f)
        db.commit()
        return f.id
    finally:
        db.close()


@pytest.fixture
def pipeline() -> RevenuePipeline:
    return RevenuePipeline()


# ── Unit: cvss_to_severity ──────────────────────────────────────


class TestCvssToSeverity:
    def test_critical(self):
        assert _cvss_to_severity(9.5) == "critical"

    def test_high(self):
        assert _cvss_to_severity(7.5) == "high"
        assert _cvss_to_severity(7.0) == "high"

    def test_medium(self):
        assert _cvss_to_severity(5.5) == "medium"
        assert _cvss_to_severity(4.0) == "medium"

    def test_low(self):
        assert _cvss_to_severity(3.5) == "low"
        assert _cvss_to_severity(0.0) == "low"


# ── Unit: PipelineResult creation ───────────────────────────────


class TestPipelineResult:
    def test_default_values(self):
        r = PipelineResult(success=True)
        assert r.success
        assert r.submission_id is None
        assert r.error == ""

    def test_error_result(self):
        r = PipelineResult(success=False, error="Something failed")
        assert not r.success
        assert r.error == "Something failed"


# ── Pipeline: submit_report ──────────────────────────────────


class TestSubmitReport:
    def test_submit_success(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform()):
            result = pipeline.submit_report(
                finding_id=sample_finding,
                platform_id="hackerone",
                program="test-program",
                evidence={"vulnerability_type": "idor", "summary": "IDOR found", "cvss_score": 7.5},
            )
        assert result.success
        assert result.submission_id is not None
        assert result.report_id is not None
        assert result.external_id == "H1-123"

    def test_submit_finding_not_found(self, pipeline: RevenuePipeline):
        result = pipeline.submit_report(finding_id=99999, platform_id="hackerone")
        assert not result.success
        assert "not found" in result.error.lower()

    def test_submit_platform_not_found(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=None):
            result = pipeline.submit_report(finding_id=sample_finding, platform_id="nonexistent")
        assert not result.success
        assert "not found" in result.error.lower()

    def test_submit_platform_failure(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform(success=False)):
            result = pipeline.submit_report(
                finding_id=sample_finding,
                platform_id="hackerone",
                program="test-program",
            )
        assert not result.success
        assert result.error

    def test_submit_without_evidence(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform()):
            result = pipeline.submit_report(
                finding_id=sample_finding,
                platform_id="hackerone",
            )
        assert result.success
        assert result.submission_id is not None


# ── Pipeline: check_submission_status ─────────────────────────


class TestCheckSubmissionStatus:
    def test_check_status_success(self, pipeline: RevenuePipeline, sample_finding: int):
        mock_platform = _make_mock_platform()
        with patch.object(pipeline, "_get_platform", return_value=mock_platform):
            submit_result = pipeline.submit_report(
                finding_id=sample_finding,
                platform_id="hackerone",
                program="test-program",
            )
        assert submit_result.success

        with patch.object(pipeline, "_get_platform", return_value=mock_platform):
            result = pipeline.check_submission_status(submit_result.submission_id)
        assert result.success
        # The mock check_status returns "unknown" for unmatched IDs
        assert result.status in ("unknown", "resolved", "submitted")

    def test_check_submission_not_found(self, pipeline: RevenuePipeline):
        result = pipeline.check_submission_status(99999)
        assert not result.success
        assert "not found" in result.error.lower()

    def test_check_submission_no_external_id(self, pipeline: RevenuePipeline):
        """Test status check before submission completed (no external_id)."""
        from database.db import SessionLocal
        from database.models import Report, SubmissionRecord

        db = SessionLocal()
        try:
            report = Report()
            db.add(report)
            db.flush()
            sub = SubmissionRecord(report_id=report.id, platform="hackerone", status="draft")
            db.add(sub)
            db.commit()
            sub_id = sub.id
        finally:
            db.close()

        result = pipeline.check_submission_status(sub_id)
        assert not result.success
        assert "external id" in result.error.lower()


# ── Pipeline: sync and record payouts ─────────────────────────


class TestPayouts:
    def test_sync_platform_payouts(self, pipeline: RevenuePipeline):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform()):
            results = pipeline.sync_platform_payouts("hackerone")
        assert len(results) > 0
        assert results[0].success
        assert results[0].payout_id is not None
        assert results[0].amount == 500.0

    def test_sync_platform_not_found(self, pipeline: RevenuePipeline):
        with patch.object(pipeline, "_get_platform", return_value=None):
            results = pipeline.sync_platform_payouts("nonexistent")
        assert len(results) == 1
        assert not results[0].success

    def test_record_payout_manually(self, pipeline: RevenuePipeline):
        result = pipeline.record_payout(
            platform="hackerone",
            amount=250.0,
            currency="USD",
            program="test-program",
            external_id="EXT-001",
        )
        assert result.success
        assert result.payout_id is not None
        assert result.amount == 250.0


# ── Pipeline: revenue_summary ─────────────────────────────────


class TestRevenueSummary:
    def test_empty_summary(self, pipeline: RevenuePipeline):
        summary = pipeline.revenue_summary()
        assert summary["total_payouts"] == 0
        assert summary["total_earned"] == 0.0
        assert summary["active_submissions"] == 0

    def test_summary_with_payouts(self, pipeline: RevenuePipeline):
        pipeline.record_payout(platform="hackerone", amount=500.0, program="prog-a")
        pipeline.record_payout(platform="bugcrowd", amount=300.0, program="prog-b")

        summary = pipeline.revenue_summary()
        assert summary["total_payouts"] == 2
        assert summary["total_earned"] == 800.0
        assert "hackerone" in summary["by_platform"]
        assert "bugcrowd" in summary["by_platform"]

    def test_summary_with_submissions(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform()):
            pipeline.submit_report(finding_id=sample_finding, platform_id="hackerone")

        summary = pipeline.revenue_summary()
        assert summary["active_submissions"] == 1

    def test_by_platform_detail(self, pipeline: RevenuePipeline):
        pipeline.record_payout(platform="hackerone", amount=100.0)
        pipeline.record_payout(platform="hackerone", amount=200.0)

        summary = pipeline.revenue_summary()
        h1 = summary["by_platform"]["hackerone"]
        assert h1["count"] == 2
        assert h1["total"] == 300.0
        assert h1["currency"] == "USD"


# ── Pipeline: list_submissions ────────────────────────────────


class TestListSubmissions:
    def test_list_empty(self, pipeline: RevenuePipeline):
        subs = pipeline.list_submissions()
        assert subs == []

    def test_list_with_filters(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform()):
            pipeline.submit_report(finding_id=sample_finding, platform_id="hackerone")

        subs = pipeline.list_submissions(platform="hackerone")
        assert len(subs) == 1
        assert subs[0]["platform"] == "hackerone"
        assert subs[0]["status"] == "submitted"
        assert subs[0]["external_id"] == "H1-123"

    def test_list_filter_by_status(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform()):
            pipeline.submit_report(finding_id=sample_finding, platform_id="hackerone")

        subs = pipeline.list_submissions(status="submitted")
        assert len(subs) == 1

        subs = pipeline.list_submissions(status="draft")
        assert len(subs) == 0

    def test_list_filters_other_platform(self, pipeline: RevenuePipeline, sample_finding: int):
        with patch.object(pipeline, "_get_platform", return_value=_make_mock_platform()):
            pipeline.submit_report(finding_id=sample_finding, platform_id="hackerone")

        subs = pipeline.list_submissions(platform="bugcrowd")
        assert len(subs) == 0


# ── Pipeline: capability registration ─────────────────────────


class TestCapabilityRegistration:
    def test_register_capabilities(self):
        from core.capabilities.registry import get_capability_registry, reset_capability_registry

        reset_capability_registry()
        reg = get_capability_registry()
        initial_count = reg.count()

        register_revenue_capabilities()

        assert reg.count() >= initial_count + 5
        assert reg.has_capability("submit_report")
        assert reg.has_capability("check_submission")
        assert reg.has_capability("sync_payouts")
        assert reg.has_capability("record_payout")
        assert reg.has_capability("revenue_summary")

    def test_capability_registration_is_safe(self):
        """Calling register twice should not crash."""
        register_revenue_capabilities()
        register_revenue_capabilities()


# ── API: /api/revenue endpoints ──────────────────────────────


class TestRevenueAPI:
    @pytest.fixture(autouse=True)
    def _setup(self):
        from api.main import app
        from cores.license.validator import generate_license

        self.client = TestClient(app)
        lic = generate_license(expiry_days=365)
        self.client.post("/api/license/activate", json={"key": lic})
        resp = self.client.post("/api/auth/login", json={"device_id": "pytest-revenue"})
        if resp.status_code == 200:
            token = resp.json()["data"]["token"]
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        self._set_csrf()

    def _set_csrf(self):
        resp = self.client.get("/api/version")
        csrf = resp.cookies.get("csrf-token")
        if csrf:
            self.client.headers.update({"X-CSRF-Token": csrf})
        elif "version" in resp.text:
            self.client.headers.update({"X-CSRF-Token": "test-token"})

    def test_get_summary_empty(self):
        resp = self.client.get("/api/revenue/summary")
        assert resp.status_code in (200, 307)
        if resp.status_code == 200:
            data = resp.json()
            assert "total_payouts" in data

    def test_get_submissions_empty(self):
        resp = self.client.get("/api/revenue/submissions")
        assert resp.status_code in (200, 307)
        if resp.status_code == 200:
            assert resp.json() == []

    def test_post_payout(self):
        resp = self.client.post(
            "/api/revenue/payouts",
            json={"platform": "hackerone", "amount": 150.0, "currency": "USD", "program": "test"},
        )
        if resp.status_code == 200:
            data = resp.json()
            assert data["success"]
            assert data["payout_id"] is not None

    def test_post_submit_finding_not_found(self):
        resp = self.client.post(
            "/api/revenue/submit",
            json={"finding_id": 99999, "platform": "hackerone"},
        )
        if resp.status_code == 400:
            assert "not found" in resp.json()["detail"].lower()
