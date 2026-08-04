"""Tests for the Daily Operation Mode (GOOD MORNING) panel."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def _make_client() -> TestClient:
    from fastapi import FastAPI

    from api.routers.daily_mode import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _health_ok() -> dict:
    return {
        "generated_at": "2026-08-04T10:00:00+0000",
        "version": {"current": "7.0.0", "codename": "own"},
        "system": {"status": "ok", "score": 100, "uptime_seconds": 100, "memory_rss_mb": 100, "cpu_percent": 1},
    }


def test_good_morning_complete_panel() -> None:
    client = _make_client()
    with (
        patch("api.routers.daily_mode.stability_status", return_value=_health_ok()),
        patch("api.routers.daily_mode._memory_stats") as mem,
        patch("api.routers.daily_mode._unfinished_work") as work,
        patch("api.routers.daily_mode._opportunities") as opps,
        patch("api.routers.daily_mode._improvements") as imp,
        patch("api.routers.daily_mode._pending_approvals") as appr,
    ):
        mem.return_value = {"healthy": True, "entries": 42, "namespaces": {"cateye": 1}}
        work.return_value = {
            "ready_to_deliver": [{"title": "X", "platform": "opire", "reward": 50}],
            "needs_access": [],
            "targets": {},
        }
        opps.return_value = {
            "scanned_sources": 135,
            "best_sources": [
                {"name": "HackerOne", "category": "bug_bounty", "trust_score": 90.0, "earning_potential": "HIGH"},
            ],
        }
        imp.return_value = [{"type": "capability", "name": "Kubernetes", "benefit": "devops", "priority": "high"}]
        appr.return_value = [{"id": "ap-1", "message": "Aprobar pago", "level": "high"}]

        resp = client.get("/api/system/good-morning")
        assert resp.status_code == 200
        body = resp.json()
        assert body["system"]["status"] == "ok"
        assert body["memory"]["entries"] == 42
        assert body["important_tasks"][0]["title"] == "X"
        assert body["opportunities"]["best_sources"][0]["name"] == "HackerOne"
        assert len(body["improvements_suggested"]) == 1
        assert len(body["pending_approvals"]) == 1
        assert "Ready" in body["summary"]


def test_good_morning_degrades_gracefully() -> None:
    """Each failing engine must not break the whole panel."""
    client = _make_client()
    with (
        patch("api.routers.daily_mode.stability_status", return_value=_health_ok()),
        patch("api.routers.daily_mode._memory_stats", side_effect=RuntimeError("boom")),
        patch("api.routers.daily_mode._unfinished_work", side_effect=RuntimeError("boom")),
        patch("api.routers.daily_mode._opportunities", side_effect=RuntimeError("boom")),
        patch("api.routers.daily_mode._improvements", side_effect=RuntimeError("boom")),
        patch("api.routers.daily_mode._pending_approvals", side_effect=RuntimeError("boom")),
    ):
        resp = client.get("/api/system/good-morning")
        assert resp.status_code == 200
        body = resp.json()
        assert body["system"]["status"] == "ok"
        assert body["important_tasks"] == []
        assert body["pending_approvals"] == []
