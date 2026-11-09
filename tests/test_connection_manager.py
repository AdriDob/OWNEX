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
            "last_sync_at": data.get("last_sync_at"),
            "last_sync_meta": data.get("last_sync_meta"),
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

    def record_sync(self, provider: str, meta: dict | None = None) -> None:
        if provider in self.data:
            self.data[provider]["last_sync_at"] = "2026-01-02T00:00:00+00:00"
            self.data[provider]["last_sync_meta"] = meta

    def update_session_state(self, provider: str, state: str) -> None:
        if provider in self.data:
            self.data[provider]["session_state"] = state

    def update_health(self, provider: str, status: str) -> None:
        if provider in self.data:
            self.data[provider]["health_status"] = status

    def get_credentials(self, provider: str) -> dict:
        data = self.data.get(provider)
        if not data:
            return {}
        return {"email": data.get("email", ""), "token": data.get("token", ""), "password": data.get("password", "")}

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


def test_accounts_expose_setup_actions_and_domains(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: None)
    body = client.get("/api/connection-manager/accounts").json()
    by_provider = {a["provider"]: a for a in body["accounts"]}

    iol = by_provider["iol"]
    assert iol["domain"] == "investment_ar"
    assert iol["setup"]["sync_mode"] == "api"
    assert iol["setup"]["login_url"]
    assert "sync" in iol["actions"]

    perchai = by_provider["perchai"]
    assert perchai["domain"] == "ai_tool"
    assert perchai["setup"]["sync_mode"] == "cli"

    opensandbox = by_provider["opensandbox"]
    assert opensandbox["domain"] == "infra"
    assert opensandbox["setup"]["sync_mode"] == "none"
    assert "sync" not in opensandbox["actions"]

    github = by_provider["github"]
    assert github["domain"] == "opportunity"


def test_sync_requires_connection(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: None)
    resp = client.post("/api/connection-manager/accounts/cocos/sync", json={"snapshot": {"total": 1}})
    assert resp.status_code == 404


def test_manual_snapshot_sync_roundtrip(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    saved: dict[str, dict] = {}
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: saved.get(provider))
    monkeypatch.setattr(
        connection_manager,
        "save_snapshot",
        lambda provider, payload, source="manual": saved.setdefault(provider, {"provider": provider, "source": source, "synced_at": "t", "data": payload}),
    )

    client.post("/api/connection-manager/accounts/cocos/connect", json={"email": "u@x.com"})
    resp = client.post(
        "/api/connection-manager/accounts/cocos/sync",
        json={"snapshot": {"portfolio_total_ars": 150000, "positions": 3}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_sync_at"] == "2026-01-02T00:00:00+00:00"
    assert body["has_snapshot"] is True
    assert body["sync_result"]["source"] == "manual"
    assert "portfolio_total_ars" in body["sync_result"]["snapshot_keys"]

    latest = client.get("/api/connection-manager/accounts/cocos/sync/latest")
    assert latest.status_code == 200
    assert latest.json()["data"]["portfolio_total_ars"] == 150000


def test_manual_sync_requires_snapshot(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: None)
    client.post("/api/connection-manager/accounts/uala/connect", json={"email": "u@x.com"})
    resp = client.post("/api/connection-manager/accounts/uala/sync", json={})
    assert resp.status_code == 400


def test_iol_api_sync_uses_stored_credentials(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: None)
    captured: dict[str, str] = {}

    def fake_sync(email: str, password: str, refresh_token: str | None = None) -> dict:
        captured["email"] = email
        captured["password"] = password
        return {"authenticated": True, "balances": {"ars": {"available": 100}}, "positions": [], "movements": []}

    monkeypatch.setattr(connection_manager, "sync_iol_account", fake_sync)
    saved: dict[str, dict] = {}
    monkeypatch.setattr(
        connection_manager,
        "save_snapshot",
        lambda provider, payload, source="api": saved.setdefault(provider, {"provider": provider, "source": source, "synced_at": "t", "data": payload}),
    )

    client.post(
        "/api/connection-manager/accounts/iol/connect",
        json={"email": "io@x.com", "password": "secret123"},
    )
    resp = client.post("/api/connection-manager/accounts/iol/sync", json={})
    assert resp.status_code == 200
    assert captured == {"email": "io@x.com", "password": "secret123"}
    body = resp.json()
    assert body["sync_result"]["source"] == "api"
    assert "balances" in body["sync_result"]["snapshot_keys"]


def test_iol_api_sync_without_password_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: None)
    client.post("/api/connection-manager/accounts/iol/connect", json={"email": "io@x.com"})
    resp = client.post("/api/connection-manager/accounts/iol/sync", json={})
    assert resp.status_code == 400
