"""Tests for the Stability Guardian consolidated SYSTEM STATUS panel.

The router consolidates existing engines (HealthCenter, capability registry,
backup engine, update manager, version engine). We isolate the singletons
with monkeypatch so the endpoint is deterministic and doesn't depend on the
production environment state.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import stability


def _dummy_health():
    return {
        "status": "green",
        "score": 95.0,
        "checks": {
            "total": 4,
            "passed": 4,
            "failed": 0,
            "details": {
                "event_bus": True,
                "scheduler": True,
                "database": True,
                "hook_registry": True,
                "memory": True,
                "agent_bus": True,
                "agents_health": True,
                "identity_vault": True,
            },
        },
        "system_state": "ready",
        "process": {
            "pid": 1,
            "uptime_seconds": 3600.0,
            "memory_rss_mb": 150.0,
            "cpu_percent": 3.0,
        },
        "database": {"targets": 10, "findings": 5, "verdicts": 3, "confirmed": 2},
    }


def _dummy_tools():
    return {
        "total_entries": 4,
        "unique_capabilities": 4,
        "active": 4,
        "broken": 0,
        "categories": ["ai", "automation"],
        "total_usage_count": 12,
    }


def _dummy_backup():
    return {
        "total_backups": 2,
        "latest_backup": {"file": "/tmp/x.zip", "size_mb": 1.2},
        "total_backup_size_mb": 2.4,
    }


def _dummy_updates():
    return {
        "current_version": "7.0.0",
        "remote_version": "7.0.0",
        "update_available": False,
        "last_checked": 1700000000,
    }


def _dummy_rollback():
    return {"rollback_available": True, "previous_versions": ["6.5.0"], "history_count": 2}


def make_client(monkeypatch) -> TestClient:
    monkeypatch.setattr(
        stability, "get_health_center", lambda *a: type("H", (), {"unified_summary": lambda s: _dummy_health()})()
    )
    monkeypatch.setattr(
        stability, "get_capability_registry", lambda *a: type("R", (), {"stats": lambda s: _dummy_tools()})()
    )
    monkeypatch.setattr(stability, "backup_status", _dummy_backup)
    monkeypatch.setattr(stability, "UpdateManager", lambda *a: type("U", (), {"status": lambda s: _dummy_updates()})())
    monkeypatch.setattr(stability, "_rollback_status", _dummy_rollback)
    app = FastAPI()
    app.include_router(stability.router)
    return TestClient(app)


def test_stability_status_shape(monkeypatch) -> None:
    client = make_client(monkeypatch)
    resp = client.get("/api/stability/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "version" in body and body["version"]["current"] == "7.0.0"
    assert "sections" in body
    for section in ("core", "memory", "agents", "security", "tools", "storage", "updates"):
        assert section in body["sections"]
    assert body["sections"]["storage"]["total_backups"] == 2
    assert body["sections"]["updates"]["rollback"]["rollback_available"] is True


def test_stability_status_core_aggregation(monkeypatch) -> None:
    client = make_client(monkeypatch)
    body = client.get("/api/stability/status").json()
    core = body["sections"]["core"]
    assert core["healthy"] is True
    assert set(core["checks"]) == {"event_bus", "scheduler", "database", "hook_registry"}
    tools = body["sections"]["tools"]
    assert tools["broken"] == 0 and tools["integrated"] == 4


def test_stability_status_handles_failed_checks(monkeypatch) -> None:
    def _health_with_failure():
        h = _dummy_health()
        h["checks"]["details"]["agent_bus"] = False
        h["status"] = "red"
        return h

    monkeypatch.setattr(
        stability,
        "get_health_center",
        lambda *a: type("H", (), {"unified_summary": lambda s: _health_with_failure()})(),
    )
    monkeypatch.setattr(
        stability, "get_capability_registry", lambda *a: type("R", (), {"stats": lambda s: _dummy_tools()})()
    )
    monkeypatch.setattr(stability, "backup_status", _dummy_backup)
    monkeypatch.setattr(stability, "UpdateManager", lambda *a: type("U", (), {"status": lambda s: _dummy_updates()})())
    monkeypatch.setattr(stability, "_rollback_status", _dummy_rollback)
    app = FastAPI()
    app.include_router(stability.router)
    body = TestClient(app).get("/api/stability/status").json()
    assert body["sections"]["agents"]["healthy"] is False
