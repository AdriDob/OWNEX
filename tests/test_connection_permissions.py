"""Tests for per-connection permission modes (Investment Hub §H).

Cada conexión tiene su propio nivel de autonomía, deny-by-default, con escalado
contiguo, confirmación humana para órdenes reales y revocación auditable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import connection_manager
from cores.connections import permissions


@pytest.fixture(autouse=True)
def _isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Nunca tocar el data dir real del usuario."""
    monkeypatch.setattr(permissions, "_base_dir", lambda: tmp_path / "connections")


def _walk_to_live(provider: str) -> None:
    for mode in permissions.MODE_LADDER[1:]:
        permissions.set_mode(
            provider,
            mode,
            acknowledge_risk=mode is permissions.PermissionMode.LIVE_TRADING_AUTHORIZED,
        )


def test_unknown_provider_is_disconnected_by_default() -> None:
    assert permissions.get_mode("nunca-configurado") is permissions.PermissionMode.DISCONNECTED
    assert permissions.capabilities("nunca-configurado") == frozenset()
    assert permissions.allows("nunca-configurado", permissions.Capability.PORTFOLIO_READ) is False


def test_read_only_grants_reads_but_never_orders() -> None:
    permissions.set_mode("binance", "READ_ONLY")
    assert permissions.allows("binance", permissions.Capability.PORTFOLIO_READ) is True
    assert permissions.allows("binance", permissions.Capability.PAPER_ORDER) is False
    assert permissions.allows("binance", permissions.Capability.LIVE_ORDER) is False
    assert permissions.live_orders_allowed("binance") is False


def test_require_raises_permission_denied_when_not_granted() -> None:
    with pytest.raises(permissions.PermissionDeniedError):
        permissions.require("iol", permissions.Capability.LIVE_ORDER)


def test_invalid_mode_is_rejected_not_defaulted() -> None:
    with pytest.raises(ValueError):
        permissions.parse_mode("TODOS_LOS_PERMISOS")


def test_escalation_cannot_skip_rungs() -> None:
    with pytest.raises(permissions.PermissionDeniedError):
        permissions.set_mode("ppi", "PAPER_TRADING")
    assert permissions.get_mode("ppi") is permissions.PermissionMode.DISCONNECTED


def test_live_trading_requires_explicit_acknowledgement() -> None:
    for mode in permissions.MODE_LADDER[1:6]:
        permissions.set_mode("alpaca", mode)
    with pytest.raises(permissions.PermissionDeniedError):
        permissions.set_mode("alpaca", "LIVE_TRADING_AUTHORIZED")
    assert permissions.live_orders_allowed("alpaca") is False

    record = permissions.set_mode("alpaca", "LIVE_TRADING_AUTHORIZED", acknowledge_risk=True)
    assert record["mode"] == "LIVE_TRADING_AUTHORIZED"
    assert record["acknowledged"] is True
    assert permissions.live_orders_allowed("alpaca") is True


def test_funds_transfer_and_withdraw_are_never_granted() -> None:
    _walk_to_live("ibkr")
    for cap in permissions.FORBIDDEN_CAPABILITIES:
        assert permissions.allows("ibkr", cap) is False


def test_downgrade_is_always_allowed_and_audited() -> None:
    _walk_to_live("ccxt")
    assert permissions.live_orders_allowed("ccxt") is True

    permissions.set_mode("ccxt", "READ_ONLY", reason="bajar exposición")
    assert permissions.live_orders_allowed("ccxt") is False

    events = permissions.get_audit(50)
    assert any(e["event"] == "mode_changed" and e["to"] == "READ_ONLY" for e in events)


def test_revoke_returns_to_disconnected() -> None:
    _walk_to_live("binance")
    record = permissions.revoke("binance", reason="kill switch")
    assert record["mode"] == "DISCONNECTED"
    assert record["capabilities"] == []
    assert any(e["event"] == "revoked" for e in permissions.get_audit(20))


def test_snapshot_and_matrix_expose_the_ladder() -> None:
    permissions.set_mode("iol", "READ_ONLY")
    snap = permissions.snapshot()
    assert snap["ladder"][0] == "DISCONNECTED"
    assert snap["providers"]["iol"]["mode"] == "READ_ONLY"
    live_row = next(m for m in snap["matrix"] if m["mode"] == "LIVE_TRADING_AUTHORIZED")
    assert live_row["live_orders"] is True
    assert live_row["requires_human_ack"] is True
    assert "WITHDRAW" in snap["forbidden_capabilities"]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    app = FastAPI()
    app.include_router(connection_manager.router)
    return TestClient(app)


def test_api_matrix_and_provider_permissions(client: TestClient) -> None:
    matrix = client.get("/api/connection-manager/permissions/matrix")
    assert matrix.status_code == 200
    assert matrix.json()["ladder"][-1] == "LIVE_TRADING_AUTHORIZED"

    current = client.get("/api/connection-manager/accounts/binance/permissions")
    assert current.status_code == 200
    assert current.json()["mode"] == "DISCONNECTED"


def test_api_rejects_live_escalation_without_ack(client: TestClient) -> None:
    resp = client.post("/api/connection-manager/accounts/binance/permissions", json={"mode": "LIVE_TRADING_AUTHORIZED"})
    assert resp.status_code in (403, 400)


def test_api_full_ladder_then_revoke(client: TestClient) -> None:
    for mode in ("READ_ONLY", "MONITORING", "PAPER_TRADING", "PRE_TRADE_VALIDATION", "CONFIRMATION_REQUIRED"):
        resp = client.post("/api/connection-manager/accounts/alpaca/permissions", json={"mode": mode})
        assert resp.status_code == 200, resp.text

    live = client.post(
        "/api/connection-manager/accounts/alpaca/permissions",
        json={"mode": "LIVE_TRADING_AUTHORIZED", "acknowledge_risk": True, "reason": "cuenta propia"},
    )
    assert live.status_code == 200, live.text
    assert live.json()["capabilities"].count("LIVE_ORDER") == 1

    revoked = client.post("/api/connection-manager/accounts/alpaca/permissions/revoke", json={"reason": "test"})
    assert revoked.json()["mode"] == "DISCONNECTED"


def test_api_unknown_provider_permissions_404(client: TestClient) -> None:
    assert client.get("/api/connection-manager/accounts/no-such-broker/permissions").status_code == 404
