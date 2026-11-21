"""Coinbase / Kraken / Bybit connector — shapes, failures and live evidence.

Los tests de unidad usan un exchange falso (sin red). Los tests marcados
``network`` verifican contra las APIs públicas reales sin credenciales: si la
API no responde, el test falla en vez de fingir que el conector funciona.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import connection_manager
from cores.brokers import cex_client
from cores.connections.catalog import API_SYNC_PROVIDERS, INVESTMENT_GLOBAL


class FakeExchange:
    def __init__(
        self,
        markets: dict[str, Any] | None = None,
        ticker: dict[str, Any] | None = None,
        balance: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._markets = markets if markets is not None else {"BTC/USD": {}, "ETH/USDT": {}}
        self._ticker = ticker if ticker is not None else {"symbol": "BTC/USD", "last": 64000.5, "timestamp": 1_700_000_000_000}
        self._balance = (
            balance
            if balance is not None
            else {
                "total": {"BTC": 0.25, "USD": 100.0, "ETH": 0.0},
                "free": {"BTC": 0.25, "USD": 100.0},
                "used": {"BTC": 0.0},
            }
        )
        self._error = error
        self.closed = False

    def load_markets(self) -> dict[str, Any]:
        if self._error:
            raise self._error
        return self._markets

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        if self._error:
            raise self._error
        return {**self._ticker, "symbol": symbol}

    def fetch_balance(self) -> dict[str, Any]:
        if self._error:
            raise self._error
        return self._balance

    def close(self) -> None:
        self.closed = True


# ── Catálogo ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("provider", ["coinbase", "kraken", "bybit"])
def test_catalog_entries_are_read_only_api_connections(provider: str) -> None:
    setup = INVESTMENT_GLOBAL[provider]
    assert setup.sync_mode == "api"
    assert setup.domain == "investment_global"
    assert "PORTFOLIO_READ" in setup.permissions
    assert "ORDER_CONFIRM" not in setup.permissions
    assert "WITHDRAW" not in setup.permissions
    assert provider in API_SYNC_PROVIDERS


# ── Verificación pública ──────────────────────────────────────────────────


def test_verify_public_returns_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cex_client, "_exchange", lambda *a, **kw: FakeExchange())
    evidence = cex_client.verify_public("kraken")

    assert evidence["reachable"] is True
    assert evidence["authenticated"] is False
    assert evidence["markets_count"] == 2
    assert evidence["last_price"] == 64000.5
    assert evidence["ticker_time"] is not None
    assert evidence["ticker_time_source"] == "exchange"
    assert evidence["latency_ms"] >= 0
    assert evidence["error"] is None


def test_verify_public_reports_failure_instead_of_claiming_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cex_client, "_exchange", lambda *a, **kw: FakeExchange(error=RuntimeError("boom")))
    evidence = cex_client.verify_public("coinbase")

    assert evidence["reachable"] is False
    assert evidence["last_price"] is None
    assert evidence["ticker_time_source"] == "unavailable"
    assert "boom" in str(evidence["error"])


def test_verify_public_rejects_unknown_exchange() -> None:
    with pytest.raises(cex_client.CEXUnavailableError):
        cex_client.verify_public("binance-us-x")


# ── Sync solo lectura ─────────────────────────────────────────────────────


def test_sync_requires_credentials() -> None:
    with pytest.raises(cex_client.CEXAuthError):
        cex_client.sync_cex_account("bybit", "", "")


def test_sync_maps_rejected_credentials_to_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cex_client, "_exchange", lambda *a, **kw: FakeExchange(error=Exception("Invalid API key")))
    with pytest.raises(cex_client.CEXAuthError):
        cex_client.sync_cex_account("bybit", "k", "s")


def test_sync_maps_network_failure_to_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cex_client, "_exchange", lambda *a, **kw: FakeExchange(error=TimeoutError("timed out")))
    with pytest.raises(cex_client.CEXUnavailableError):
        cex_client.sync_cex_account("kraken", "k", "s")


def test_sync_returns_read_only_balance_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cex_client, "_exchange", lambda *a, **kw: FakeExchange())
    snapshot = cex_client.sync_cex_account("coinbase", "key", "secret")

    assert snapshot["authenticated"] is True
    assert snapshot["permissions"] == "read_only"
    assert snapshot["balances"]["total"] == {"BTC": 0.25, "USD": 100.0}  # ceros descartados
    assert snapshot["balances"]["free"]["BTC"] == 0.25
    assert "USD" not in snapshot["quotes"]  # el efectivo no se cotiza contra sí mismo
    assert snapshot["quotes"]["BTC"]["symbol"] == "BTC/USD"
    assert snapshot["fetched_at"]


# ── API ───────────────────────────────────────────────────────────────────


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(connection_manager.router)
    return TestClient(app)


def test_api_verify_route_returns_evidence_and_records_event(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        connection_manager,
        "verify_public",
        lambda provider, symbol=None: {
            "provider": provider,
            "symbol": symbol or "BTC/USD",
            "reachable": True,
            "latency_ms": 42.0,
            "markets_count": 10,
            "last_price": 1.0,
            "error": None,
        },
    )
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(connection_manager, "record_event", lambda provider, event: events.append((provider, event)))

    resp = client.get("/api/connection-manager/accounts/kraken/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["reachable"] is True
    assert events and events[0][0] == "kraken"
    assert events[0][1]["kind"] == "verify_public"


def test_api_sync_uses_cex_client_with_stored_credentials(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Wiring del sync: creds del vault → sync_cex_account → snapshot persistido."""

    class FakeVault:
        SUPPORTED_PROVIDERS: list[str] = []

        def get_account(self, provider: str) -> dict[str, Any]:
            return {"provider_name": provider, "has_credentials": True, "health_status": "healthy"}

        def get_credentials(self, provider: str) -> dict[str, str]:
            return {"email": "alias", "token": "KEYVALUE123", "password": "SEKRETVALUE456"}

        def record_sync(self, provider: str, meta: dict[str, Any]) -> None:
            self.last_sync = (provider, meta)

        def update_session_state(self, provider: str, state: str) -> None:
            pass

        def update_health(self, provider: str, status: str) -> None:
            pass

    vault = FakeVault()
    monkeypatch.setattr(connection_manager, "get_identity_vault", lambda: vault)
    monkeypatch.setattr(connection_manager, "record_event", lambda provider, event: None)
    monkeypatch.setattr(
        connection_manager,
        "save_snapshot",
        lambda provider, payload, source="manual": {"provider": provider, "source": source, "synced_at": "2026-01-01T00:00:00+00:00"},
    )
    monkeypatch.setattr(connection_manager.financial_normalizer, "normalize_provider", lambda *a, **kw: None)
    called: dict[str, Any] = {}

    def fake_sync(provider: str, api_key: str, api_secret: str) -> dict[str, Any]:
        called.update({"provider": provider, "api_key": api_key, "api_secret": api_secret})
        return {"authenticated": True, "exchange": provider, "permissions": "read_only"}

    monkeypatch.setattr(connection_manager, "sync_cex_account", fake_sync)

    resp = client.post("/api/connection-manager/accounts/bybit/sync", json={})
    assert resp.status_code == 200, resp.text
    assert called == {"provider": "bybit", "api_key": "KEYVALUE123", "api_secret": "SEKRETVALUE456"}
    # Los valores de las credenciales nunca vuelven al cliente.
    assert "KEYVALUE123" not in resp.text and "SEKRETVALUE456" not in resp.text


def test_api_sync_rejects_missing_cex_credentials(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class EmptyVault:
        SUPPORTED_PROVIDERS: list[str] = []

        def get_account(self, provider: str) -> dict[str, Any]:
            return {"provider_name": provider, "has_credentials": True}

        def get_credentials(self, provider: str) -> dict[str, str]:
            return {"email": "alias", "token": "", "password": ""}

    monkeypatch.setattr(connection_manager, "get_identity_vault", lambda: EmptyVault())
    resp = client.post("/api/connection-manager/accounts/coinbase/sync", json={})
    assert resp.status_code == 400
    assert "credenciales" in resp.json()["detail"].lower()


def test_api_verify_route_rejects_non_cex_provider(client: TestClient) -> None:
    resp = client.get("/api/connection-manager/accounts/iol/verify")
    assert resp.status_code == 400
    assert "coinbase" in resp.json()["detail"]


def test_api_catalog_exposes_new_exchanges(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(connection_manager, "get_identity_vault", lambda: type("V", (), {"list_accounts": lambda self: [], "SUPPORTED_PROVIDERS": []})())
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: None)
    accounts = {a["provider"]: a for a in client.get("/api/connection-manager/accounts").json()["accounts"]}

    for provider in ("coinbase", "kraken", "bybit"):
        assert accounts[provider]["domain"] == "investment_global"
        assert accounts[provider]["auth_mechanism"] == "api_key_secret"
        assert accounts[provider]["permission_mode"] == "DISCONNECTED"
        assert accounts[provider]["setup"]["sync_mode"] == "api"


# ── Verificación live contra las APIs reales ──────────────────────────────


@pytest.mark.network
@pytest.mark.parametrize(
    ("provider", "expected_symbol"),
    [("coinbase", "BTC/USD"), ("kraken", "BTC/USD"), ("bybit", "BTC/USDT")],
)
def test_live_public_api_reachable(provider: str, expected_symbol: str) -> None:
    """Sin credenciales: prueba que el exchange real responde y da precio."""
    evidence = cex_client.verify_public(provider)

    assert evidence["reachable"] is True, evidence["error"]
    assert evidence["markets_count"] > 0
    assert evidence["last_price"] is not None and float(evidence["last_price"]) > 0
    assert expected_symbol in str(evidence["symbol"])
    # Frescura declarada honesta: exchange si publica timestamp, unavailable si no.
    assert evidence["ticker_time_source"] in {"exchange", "unavailable"}
    if evidence["ticker_time_source"] == "unavailable":
        assert evidence["ticker_time"] is None
    else:
        assert evidence["ticker_time"] is not None
    assert evidence["checked_at"]
