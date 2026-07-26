"""Tests for VerdictAutoLearner — FeedbackTuner ↔ AcceptanceLearner bridge."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ── Mock finding payloads ──────────────────────────────────────────────

CONFIRMED_PAYLOAD = {
    "id": 1,
    "new_status": "confirmed",
    "old_status": "validating",
    "title": "SQL Injection on /api/users",
}

REJECTED_PAYLOAD = {
    "id": 2,
    "new_status": "rejected",
    "old_status": "validating",
    "title": "Self XSS on profile page",
}

SKIP_PAYLOAD = {
    "id": 3,
    "new_status": "validating",
    "old_status": "pending",
    "title": "Still in progress",
}

NO_ID_PAYLOAD = {
    "new_status": "confirmed",
    "old_status": "validating",
    "title": "Missing ID",
}


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def mock_finding_details():
    """Return a fake finding for DB lookup."""
    return {
        "id": 1,
        "vulnerability_type": "sql_injection",
        "severity": "critical",
        "title": "SQL Injection on /api/users",
        "status": "confirmed",
    }


@pytest.fixture
def mock_learner():
    """Mock AcceptanceLearner."""
    with patch("core.learning.verdict_learner.get_acceptance_learner") as mock:
        instance = MagicMock()
        instance.record_manual_outcome.return_value = None
        instance.get_summary.return_value = {
            "total_observations": 5,
            "acceptance_rate": 0.8,
            "platforms": ["hackerone", "bugcrowd"],
        }
        instance.get_weights.return_value = {
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        }
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_bus():
    """Mock EventBus."""
    with patch("core.learning.verdict_learner.get_bus") as mock:
        instance = MagicMock()
        instance.publish = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def verdict_learner(mock_learner, mock_bus):
    """VerdictAutoLearner with mocked dependencies."""
    from core.learning.verdict_learner import VerdictAutoLearner

    vl = VerdictAutoLearner()
    vl._learner = mock_learner
    vl._event_count = 0
    return vl


# ── Tests: handle_finding_status_changed ─────────────────────────────


class TestHandleFindingStatusChanged:
    def test_confirmed_records_accepted_outcome(self, verdict_learner, mock_learner):
        with (
            patch(
                "core.learning.verdict_learner.get_finding_details",
                return_value={
                    "id": 1,
                    "vulnerability_type": "sql_injection",
                    "severity": "critical",
                    "title": "SQL Inj",
                    "status": "confirmed",
                },
            ),
            patch(
                "core.learning.verdict_learner.get_quality_dimensions",
                return_value={
                    "evidence": 0.9,
                    "reproducibility": 0.8,
                    "clarity": 0.85,
                    "impact_severity": 0.95,
                    "completeness": 0.8,
                    "confidence": 0.9,
                },
            ),
        ):
            result = verdict_learner.handle_finding_status_changed(CONFIRMED_PAYLOAD)

        assert result["action"] == "recorded"
        assert result["finding_id"] == 1
        assert result["outcome"] == "accepted"
        assert verdict_learner._event_count == 1

        mock_learner.record_manual_outcome.assert_called_once()
        kwargs = mock_learner.record_manual_outcome.call_args[1]
        assert kwargs["outcome"] == "accepted"
        assert kwargs["vulnerability_type"] == "sql_injection"
        assert kwargs["score"] > 80

    def test_rejected_records_rejected_outcome(self, verdict_learner, mock_learner):
        with (
            patch(
                "core.learning.verdict_learner.get_finding_details",
                return_value={
                    "id": 2,
                    "vulnerability_type": "xss",
                    "severity": "low",
                    "title": "Self XSS",
                    "status": "rejected",
                },
            ),
            patch(
                "core.learning.verdict_learner.get_quality_dimensions",
                return_value={
                    "evidence": 0.3,
                    "reproducibility": 0.4,
                    "clarity": 0.5,
                    "impact_severity": 0.2,
                    "completeness": 0.3,
                    "confidence": 0.2,
                },
            ),
        ):
            result = verdict_learner.handle_finding_status_changed(REJECTED_PAYLOAD)

        assert result["action"] == "recorded"
        assert result["outcome"] == "rejected"

        mock_learner.record_manual_outcome.assert_called_once()
        kwargs = mock_learner.record_manual_outcome.call_args[1]
        assert kwargs["outcome"] == "rejected"
        assert kwargs["score"] < 50

    def test_skip_non_terminal_status(self, verdict_learner, mock_learner):
        result = verdict_learner.handle_finding_status_changed(SKIP_PAYLOAD)
        assert result["action"] == "skip"
        mock_learner.record_manual_outcome.assert_not_called()

    def test_skip_no_finding_id(self, verdict_learner, mock_learner):
        result = verdict_learner.handle_finding_status_changed(NO_ID_PAYLOAD)
        assert result["action"] == "skip"
        mock_learner.record_manual_outcome.assert_not_called()

    def test_error_on_missing_finding(self, verdict_learner, mock_learner):
        with patch("core.learning.verdict_learner.get_finding_details", return_value=None):
            result = verdict_learner.handle_finding_status_changed(CONFIRMED_PAYLOAD)
        assert result["action"] == "error"
        mock_learner.record_manual_outcome.assert_not_called()


# ── Tests: publish events ────────────────────────────────────────────


class TestPublishEvents:
    def test_publishes_accepted_outcome_events(self, verdict_learner, mock_bus):
        verdict_learner._publish_events(1, "hackerone", "accepted", 87.5, {})
        assert mock_bus.publish.call_count == 2

        calls = mock_bus.publish.call_args_list
        types = [c[0][0] for c in calls]
        assert "acceptance:outcome:recorded" in types
        assert "acceptance:prediction:made" in types

    def test_publishes_rejected_outcome_events(self, verdict_learner, mock_bus):
        verdict_learner._publish_events(2, "bugcrowd", "rejected", 35.0, {})
        assert mock_bus.publish.call_count == 2


# ── Tests: status ────────────────────────────────────────────────────


class TestStatus:
    def test_status_returns_summary(self, verdict_learner, mock_learner):
        verdict_learner._event_count = 3
        s = verdict_learner.status()
        assert s["events_processed"] == 3
        assert s["total_observations"] == 5
        assert s["acceptance_rate"] == 0.8
        assert "hackerone" in s["platforms"]

    def test_status_error_handling(self):
        from core.learning.verdict_learner import VerdictAutoLearner

        vl = VerdictAutoLearner()
        vl._learner = object()  # type: ignore
        s = vl.status()
        assert "error" in s


# ── Tests: get_quality_dimensions ────────────────────────────────────


class TestGetQualityDimensions:
    def test_quality_dimensions_success(self):
        mock_score = MagicMock()
        mock_score.dimensions = {
            "evidence": 0.9,
            "reproducibility": 0.8,
            "clarity": 0.85,
            "impact_severity": 0.95,
            "completeness": 0.8,
            "confidence": 0.9,
        }

        with patch("core.reports.quality.scorer.QualityScorer.score", return_value=mock_score):
            from core.learning.verdict_learner import get_quality_dimensions

            dims = get_quality_dimensions(1)
            assert dims is not None
            assert dims["evidence"] == 0.9
            assert dims["clarity"] == 0.85

    def test_quality_dimensions_failure_returns_defaults(self):
        with patch("core.reports.quality.scorer.QualityScorer", side_effect=ImportError("no scorer")):
            from core.learning.verdict_learner import get_quality_dimensions

            dims = get_quality_dimensions(1)
            assert dims is None


# ── Tests: _detect_platform ──────────────────────────────────────────


class TestDetectPlatform:
    def test_detects_hackerone_from_target_name(self):
        with patch("database.db.SessionLocal") as m:
            mock_session = MagicMock()
            m.return_value.__enter__.return_value = mock_session

            mock_finding = MagicMock()
            mock_finding.target_id = 42

            mock_target = MagicMock()
            mock_target.name = "hackerone_testcorp"

            def query_side_effect(model):
                q = MagicMock()
                if model.__name__ == "Finding":
                    q.filter.return_value.first.return_value = mock_finding
                else:
                    q.filter.return_value.first.return_value = mock_target
                return q

            mock_session.query.side_effect = query_side_effect

            from core.learning.verdict_learner import VerdictAutoLearner

            vl = VerdictAutoLearner()
            result = vl._detect_platform(1)
            assert result == "hackerone"

    def test_defaults_to_hackerone_when_unknown(self):
        with patch("database.db.SessionLocal") as m:
            m.return_value.__enter__.return_value.query.return_value.filter.return_value.first.return_value = None

            from core.learning.verdict_learner import VerdictAutoLearner

            vl = VerdictAutoLearner()
            result = vl._detect_platform(999)
            assert result == "hackerone"


# ── Tests: get_verdict_learner singleton ─────────────────────────────


class TestSingleton:
    def test_get_verdict_learner_returns_singleton(self):
        from core.learning import verdict_learner as _vl_mod

        _vl_mod._LEARNER = None
        v1 = _vl_mod.get_verdict_learner()
        v2 = _vl_mod.get_verdict_learner()
        assert v1 is v2
