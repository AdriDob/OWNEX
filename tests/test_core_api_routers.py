"""Tests for core/api/routers.py — extension, secrets, health endpoints."""

from __future__ import annotations

# Build a minimal FastAPI app with just the core router
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.api.routers import router as core_router
from core.health.engine import get_health_center

app = FastAPI()
app.include_router(core_router)
client = TestClient(app)


class TestExtensionEndpoints:
    def test_list_extensions(self):
        resp = client.get("/api/core/extensions")
        assert resp.status_code == 200
        data = resp.json()
        # Should be a dict of extension_id -> status
        assert isinstance(data, dict)

    def test_list_hooks(self):
        resp = client.get("/api/core/hooks")
        assert resp.status_code == 200
        data = resp.json()
        assert "hooks" in data
        assert len(data["hooks"]) > 0

    def test_list_capabilities(self):
        resp = client.get("/api/core/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "capabilities" in data


class TestSecretsEndpoints:
    def test_list_secrets(self):
        resp = client.get("/api/core/secrets")
        assert resp.status_code == 200
        data = resp.json()
        assert "keys" in data

    def test_get_nonexistent_secret(self):
        resp = client.get("/api/core/secrets/NONEXISTENT_TEST_KEY")
        assert resp.status_code == 404

    def test_set_and_get_secret(self):
        resp = client.put(
            "/api/core/secrets/TEST_API_KEY",
            json={"value": "test-value-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["stored"] is True

        resp = client.get("/api/core/secrets/TEST_API_KEY")
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == "test-value-123"

        # Cleanup
        client.delete("/api/core/secrets/TEST_API_KEY")

    def test_delete_secret(self):
        client.put("/api/core/secrets/TEST_DELETE", json={"value": "delete-me"})
        resp = client.delete("/api/core/secrets/TEST_DELETE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True

    def test_secrets_health(self):
        resp = client.get("/api/core/secrets/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "secrets" in data
        assert "vault_available" in data["secrets"]


class TestHealthEndpoints:
    def test_health_summary(self):
        center = get_health_center()
        center.register("test_ok", lambda: True, "system")
        resp = client.get("/api/core/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    def test_run_health_check(self):
        center = get_health_center()
        center.register("test_run", lambda: True, "system")
        resp = client.post("/api/core/health/run")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "checks" in data

    def test_list_health_checks(self):
        resp = client.get("/api/core/health/checks")
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data
