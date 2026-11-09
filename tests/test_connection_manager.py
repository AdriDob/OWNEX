"""Tests for the unified Connection Manager API."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import connection_manager


class FakeVault:
    SUPPORTED_PROVIDERS = ["github", "hackerone", "bugcrowd"]

    def __init__(self) -> None:
        self.data: dict[str, dict] = {}

    def _public(self, provider: str, data: dict) -> dict:
        return {
            "provider_name": provider,
            "email": data.get("email", ""),
            "session_state": data.get("session_state", "disconnected"),
            "last_checked": data.get("last_checked"),
            "health_status": data.get("health_status", "unknown"),
            "has_credentials": bool(data.get("token") or data.get("password")),
        }

    def list_accounts(self) -> list[dict]:
        return [self._public(p, d) for p, d in self.data.items()]

    def get_account(self, provider: str) -> dict | None:
        data = self.data.get(provider)
        return self._public(provider, data) if data else None

    def store_credentials(self, provider, email, token="", password="", metadata=None) -> None:
        self.data[provider] = {
            "email": email,
            "session_state": "disconnected",
            "last_checked": "2026-01-01T00:00:00+00:00",
            "health_status": "unknown",
            "token": token,
            "password": password,
        }

    def remove_credentials(self, provider: str) -> None:
        self.data.pop(provider, None)

    def check_session_health(self, provider: str) -> dict:
        return {"provider": provider, "health": "unknown"}


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    vault = FakeVault()
    monkeypatch.setattr(connection_manager, "get_identity_vault", lambda: vault)
    app = FastAPI()
    app.include_router(connection_manager.router)
    return TestClient(app)


def test_list_accounts_includes_catalog_and_states(client: TestClient) -> None:
    resp = client.get("/api/connection-manager/accounts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total"] > 0
    states = {a["state"] for a in body["accounts"]}
    assert "NOT_CONNECTED" in states
    assert all(a["provider"] for a in body["accounts"])
    assert all("token" not in a and "password" not in a for a in body["accounts"])


def test_connect_requires_email(client: TestClient) -> None:
    resp = client.post("/api/connection-manager/accounts/github/connect", json={"token": "x"})
    assert resp.status_code == 400


def test_connect_email_only_marks_manual_setup(client: TestClient) -> None:
    resp = client.post(
        "/api/connection-manager/accounts/superteam/connect",
        json={"email": "dev@example.com"},
    )
    assert resp.status_code == 200
    account = resp.json()
    assert account["has_credentials"] is False
    assert account["state"] == "MANUAL_SETUP"


def test_connect_disconnect_lifecycle(client: TestClient) -> None:
    resp = client.post(
        "/api/connection-manager/accounts/github/connect",
        json={"email": "dev@example.com", "token": "ghp_x"},
    )
    assert resp.status_code == 200
    account = resp.json()
    assert account["provider"] == "github"
    assert account["has_credentials"] is True
    assert account["state"] in connection_manager.CONNECTION_STATES

    status = client.get("/api/connection-manager/accounts/github/status")
    assert status.status_code == 200
    assert status.json()["session_health"]["provider"] == "github"

    removed = client.post("/api/connection-manager/accounts/github/disconnect")
    assert removed.status_code == 200
    assert removed.json()["state"] == "NOT_CONNECTED"


def test_status_unknown_provider_404(client: TestClient) -> None:
    resp = client.get("/api/connection-manager/accounts/unknown-provider/status")
    assert resp.status_code == 404
