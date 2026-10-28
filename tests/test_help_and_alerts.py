"""Tests for the Help Center and Alerts sweep endpoints."""

from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.alerts import router as alerts_router
from api.routers.help_center import router as help_router

app = FastAPI()
app.include_router(alerts_router)
app.include_router(help_router)
client = TestClient(app)


class _FakeWorkItem:
    def __init__(self, title: str, description: str = "Approval needed"):
        self.title = title
        self.human_action_required = True
        self.human_action_description = description


class TestHelpWorkflows:
    def test_workflows_list(self) -> None:
        response = client.get("/api/help/workflows")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 3
        for wf in body["workflows"]:
            assert {"id", "title", "steps"} <= set(wf.keys())
            assert len(wf["steps"]) >= 3

    def test_quick_answers_shape(self) -> None:
        response = client.get("/api/help/quick-answers")
        assert response.status_code == 200
        body = response.json()
        assert "generated_at" in body
        assert isinstance(body["answers"], list)
        assert len(body["answers"]) >= 1
        for ans in body["answers"]:
            assert {"question", "answer", "priority"} <= set(ans.keys())


class TestAlertsSweep:
    def test_sweep_empty_state(self) -> None:
        with (
            patch("api.routers.alerts._pending_approvals", return_value=[]),
            patch("api.routers.alerts._workbank_snapshot", return_value=None),
            patch("api.routers.alerts._setup_pending", return_value=None),
            patch("api.routers.alerts._ai_available", return_value=None),
            patch("api.routers.alerts._last_scan_age_hours", return_value=None),
        ):
            response = client.post("/api/alerts/sweep", json={"create": False})
        assert response.status_code == 200
        body = response.json()
        assert body["total_findings"] >= 1  # stale-scan warning fires when no scan known
        kinds = {f["title"] for f in body["findings"]}
        assert any("scan" in t.lower() for t in kinds)

    def test_sweep_blocked_approval(self) -> None:
        approvals = [{"id": "w1", "title": "Deliver X", "description": "Approval needed"}]
        with (
            patch("api.routers.alerts._pending_approvals", return_value=approvals),
            patch("api.routers.alerts._workbank_snapshot", return_value=None),
            patch("api.routers.alerts._setup_pending", return_value=None),
            patch("api.routers.alerts._ai_available", return_value=False),
            patch("api.routers.alerts._last_scan_age_hours", return_value=2.0),
        ):
            response = client.post("/api/alerts/sweep", json={"create": False})
        assert response.status_code == 200
        findings = response.json()["findings"]
        titles = {f["title"] for f in findings}
        assert any("Aprobación" in t for t in titles)
        assert any("IA no disponible" in t for t in titles)
        for f in findings:
            assert "key" not in f  # internal dedup key must not leak

    def test_sweep_no_duplicate_creation(self) -> None:
        """Second sweep with the same state must not re-create alerts."""
        with (
            patch("api.routers.alerts._pending_approvals", return_value=[]),
            patch("api.routers.alerts._workbank_snapshot", return_value={"ready": 3, "needs_access": 0}),
            patch("api.routers.alerts._setup_pending", return_value=None),
            patch("api.routers.alerts._ai_available", return_value=True),
            patch("api.routers.alerts._last_scan_age_hours", return_value=1.0),
        ):
            first = client.post("/api/alerts/sweep", json={"create": False})
            assert first.status_code == 200
