"""Tests for financial connections milestone: PPI, Binance, importer, history."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import connection_manager
from cores.brokers import binance_client, iol_client, ppi_client
from cores.connections import financial_normalizer, importer, mcp_consent, portfolio_view, sync_history


class FakeVault:
    SUPPORTED_PROVIDERS = []

    def __init__(self) -> None:
        self.data: dict[str, dict] = {}
        self.secrets: dict[tuple[str, str], str] = {}

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
            "last_checked": "t",
            "health_status": "unknown",
            "token": token,
            "password": password,
            "metadata": metadata or {},
        }

    def remove_credentials(self, provider: str) -> None:
        self.data.pop(provider, None)

    def record_sync(self, provider: str, meta: dict | None = None) -> None:
        if provider in self.data:
            self.data[provider]["last_sync_at"] = "t2"
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
        return {
            "email": data.get("email", ""),
            "token": data.get("token", ""),
            "password": data.get("password", ""),
            **data.get("metadata", {}),
        }

    def check_session_health(self, provider: str) -> dict:
        return {"provider": provider, "health": "unknown"}

    def set_secret(self, provider: str, name: str, value: str) -> None:
        self.secrets[(provider, name)] = value

    def get_secret(self, provider: str, name: str) -> str:
        return self.secrets.get((provider, name), "")


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    vault = FakeVault()
    monkeypatch.setattr(connection_manager, "get_identity_vault", lambda: vault)
    monkeypatch.setattr(connection_manager, "load_snapshot", lambda provider: None)
    monkeypatch.setattr(connection_manager, "record_event", lambda *a, **k: None)
    monkeypatch.setattr(
        connection_manager,
        "save_snapshot",
        lambda provider, payload, source="manual": {"provider": provider, "source": source, "synced_at": "t", "data": payload},
    )
    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(importer, "get_config", lambda: fake_cfg)
    monkeypatch.setattr(sync_history, "get_config", lambda: fake_cfg)
    app = FastAPI()
    app.include_router(connection_manager.router)
    return TestClient(app)


# ── Catalog v2 ────────────────────────────────────────────────────────────


def test_catalog_exposes_permissions_and_methods(client: TestClient) -> None:
    body = client.get("/api/connection-manager/accounts").json()
    by_provider = {a["provider"]: a for a in body["accounts"]}

    for name in ("iol", "ppi", "binance"):
        setup = by_provider[name]["setup"]
        assert setup["integration_method"] == "api_rest"
        assert "PORTFOLIO_READ" in setup["permissions"]
        assert "TRADE_REQUIRES_CONFIRMATION" not in setup["permissions"]

    assert by_provider["ripio"]["setup"]["integration_method"] == "manual_import"
    assert by_provider["bullmarket"]["domain"] == "investment_ar"
    assert by_provider["banza"]["domain"] == "investment_ar"
    assert by_provider["inviu"]["domain"] == "investment_ar"


# ── PPI client (mocked HTTP) ──────────────────────────────────────────────


def test_ppi_login_and_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeResp:
        def __init__(self, payload):
            self._payload = payload
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_post(url, headers=None, timeout=None):
        calls.append(url)
        assert headers["ApiKey"] == "k"
        assert headers["AuthorizedClient"] == "ac"
        return FakeResp([{"accessToken": "tok", "refreshToken": "ref", "expires": 3600}])

    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/Account/Accounts"):
            return FakeResp([{"accountNumber": "123", "name": "Principal"}])
        if url.endswith("/Account/BalancesAndPositions"):
            return FakeResp({"groupedAvailability": [], "groupedInstruments": []})
        if url.endswith("/Account/AvailableBalance"):
            return FakeResp([{"name": "ARS", "simbol": "$", "amount": 1000, "settlement": "INMEDIATA"}])
        if url.endswith("/Account/Movements"):
            return FakeResp([{"description": "Compra", "amount": -500, "currency": "ARS"}])
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr(ppi_client.httpx, "post", fake_post)
    monkeypatch.setattr(ppi_client.httpx, "get", fake_get)

    snap = ppi_client.sync_ppi_account("k", "s", "ac", "ck")
    assert snap["authenticated"] is True
    assert snap["accounts"][0]["accountNumber"] == "123"
    detail = snap["account_details"][0]
    assert detail["available_balance"][0]["amount"] == 1000
    assert detail["movements"][0]["description"] == "Compra"
    assert any("LoginApi" in c for c in calls)


def test_ppi_sync_requires_all_credentials(client: TestClient) -> None:
    client.post("/api/connection-manager/accounts/ppi/connect", json={"email": "ppi@x.com", "token": "k"})
    resp = client.post("/api/connection-manager/accounts/ppi/sync", json={})
    assert resp.status_code == 400
    assert "AuthorizedClient" in resp.json()["detail"]


def test_ppi_api_sync_dispatch(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_sync(api_key, api_secret, authorized_client, client_key, base_url=None):
        captured.update(api_key=api_key, authorized_client=authorized_client)
        return {"authenticated": True, "accounts": []}

    monkeypatch.setattr(connection_manager, "sync_ppi_account", fake_sync)
    client.post(
        "/api/connection-manager/accounts/ppi/connect",
        json={
            "email": "ppi@x.com",
            "token": "apikey",
            "password": "apisecret",
            "metadata": {"authorized_client": "AC", "client_key": "CK"},
        },
    )
    resp = client.post("/api/connection-manager/accounts/ppi/sync", json={})
    assert resp.status_code == 200
    assert captured["api_key"] == "apikey"
    assert captured["authorized_client"] == "AC"


# ── Binance client (mocked ccxt) ──────────────────────────────────────────


def test_binance_sync_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeExchange:
        def fetch_balance(self):
            return {"total": {"BTC": 0.5, "USDT": 100.0, "XRP": 0}, "free": {"BTC": 0.5}, "used": {}}

    import sys
    from types import SimpleNamespace

    fake_ccxt = SimpleNamespace(binance=staticmethod(lambda cfg: FakeExchange()))
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)
    snap = binance_client.sync_binance_account("key", "secret")
    assert snap["permissions"] == "read_only"
    assert snap["balances"]["total"]["BTC"] == 0.5
    assert "XRP" not in snap["balances"]["total"]  # zero balances dropped


def test_binance_sync_requires_credentials(client: TestClient) -> None:
    client.post("/api/connection-manager/accounts/binance/connect", json={"email": "b@x.com"})
    resp = client.post("/api/connection-manager/accounts/binance/sync", json={})
    assert resp.status_code == 400


# ── Importer ──────────────────────────────────────────────────────────────

CSV = b"Fecha;Tipo;Ticker;Cantidad;Precio;Moneda\n2026-01-01;Compra;GGAL;10;1500;ARS\n2026-01-02;Venta;GGAL;5;1600;ARS\n"


def test_importer_preview_csv(client: TestClient) -> None:
    resp = client.post(
        "/api/connection-manager/accounts/cocos/import/preview",
        files={"file": ("mov.csv", io.BytesIO(CSV), "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["format"] == "csv"
    assert body["total_rows"] == 2
    assert body["mapping"]["date"] == "Fecha"
    assert body["mapping"]["ticker"] == "Ticker"
    assert len(body["preview"]) == 2


def test_importer_confirm_dedup_and_provenance(client: TestClient) -> None:
    r1 = client.post(
        "/api/connection-manager/accounts/cocos/import/confirm",
        files={"file": ("mov.csv", io.BytesIO(CSV), "text/csv")},
    )
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["imported"] == 2
    assert b1["batch_id"]

    # re-import same file -> all duplicates within batch; new batch still stores
    r2 = client.post(
        "/api/connection-manager/accounts/cocos/import/confirm",
        files={"file": ("mov.csv", io.BytesIO(CSV), "text/csv")},
    )
    assert r2.status_code == 200

    listing = client.get("/api/connection-manager/accounts/cocos/imports").json()
    assert len(listing["imports"]) == 2
    first = listing["imports"][0]
    assert first["source_hash"]
    assert "records" not in first  # metadata only


def test_importer_rejects_unknown_provider(client: TestClient) -> None:
    resp = client.post(
        "/api/connection-manager/accounts/nonexistent/import/preview",
        files={"file": ("x.csv", io.BytesIO(CSV), "text/csv")},
    )
    assert resp.status_code == 404


def test_importer_json_format() -> None:
    payload = json.dumps([{"date": "2026-01-01", "ticker": "BTC", "amount": "1.5", "currency": "USDT"}]).encode()
    prev = importer.preview_import("binance", "ops.json", payload)
    assert prev["format"] == "json"
    assert prev["mapping"]["ticker"] == "ticker"


# ── Sync history ──────────────────────────────────────────────────────────


def test_sync_history_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(sync_history, "get_config", lambda: fake_cfg)
    sync_history.record_event("cocos", {"kind": "sync", "source": "manual"})
    sync_history.record_event("cocos", {"kind": "import", "imported": 5})
    events = sync_history.get_history("cocos")
    assert len(events) == 2
    assert events[0]["kind"] == "import"  # newest first
    assert events[1]["provider"] == "cocos"
    assert "ts" in events[0]


def test_sync_history_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(sync_history, "get_config", lambda: fake_cfg)
    monkeypatch.setattr(connection_manager, "get_history", lambda p, limit=50: [{"kind": "sync"}])
    resp = client.get("/api/connection-manager/accounts/cocos/sync/history")
    assert resp.status_code == 200
    assert resp.json()["events"] == [{"kind": "sync"}]


# ── Financial normalizer (P8) ─────────────────────────────────────────────


def _norm_cfg(tmp_path, monkeypatch):
    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(financial_normalizer, "get_config", lambda: fake_cfg)


def test_normalize_iol_snapshot(tmp_path, monkeypatch) -> None:
    _norm_cfg(tmp_path, monkeypatch)
    # Real IOL API shapes (developers.iolinversiones.com)
    snap = {
        "positions": {
            "account": "AR",
            "currency": "USD",
            "positions": [
                {
                    "instrument": {"symbol": "GGAL", "name": "Grupo Galicia", "asset_class": "STOCK", "currency": "ARS"},
                    "availability": {"quantity_available": 10, "quantity_held": 0, "quantity_pending": 0},
                    "cost_basis": {"average_entry_price": 1400, "total_cost": 14000},
                    "market_value": {"current_price": 1500, "price_change_percent": 7.1, "value": 15000},
                }
            ],
        },
        "balances": {
            "ars": {"available": {"t0": 30000, "t1": 20000}, "available_for_withdrawal": 50000},
            "usd": {"available": {"t0": 100}, "available_for_withdrawal": 100},
        },
        "movements": [{"ticker": "GGAL", "type": "buy", "amount": -15000, "currency": "ARS", "date": "2026-01-01"}],
    }
    out = financial_normalizer.normalize_provider("iol", snap)
    assert out["position_count"] == 1
    assert out["positions"][0]["symbol"] == "GGAL"
    assert out["positions"][0]["quantity"] == 10
    assert out["positions"][0]["avg_price"] == 1400
    assert out["cash_by_currency"] == {"ARS": 50000, "USD": 100}
    assert out["transaction_count"] == 1
    assert financial_normalizer.load_normalized("iol")["provider"] == "iol"


def test_iol_authenticate_sends_oauth2_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    """IOL /auth/token requires grant_type=password per official docs."""
    captured: dict = {}

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"access_token": "jwt", "refresh_token": "rt", "expires_in": 3600, "expires_at": "2026-01-01T01:00:00Z", "token_type": "bearer"}}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return FakeResp()

    monkeypatch.setattr(iol_client.httpx, "post", fake_post)
    client = iol_client.IOLClient()
    auth = client.authenticate("u@x.com", "pw")
    assert captured["json"]["grant_type"] == "password"
    assert captured["json"]["username"] == "u@x.com"
    assert auth["access_token"] == "jwt"
    assert auth["refresh_token"] == "rt"


def test_iol_refresh_grant(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"access_token": "new-jwt", "refresh_token": "rt2"}}

    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return FakeResp()

    monkeypatch.setattr(iol_client.httpx, "post", fake_post)
    out = iol_client.IOLClient().refresh("rt-old")
    assert captured["json"] == {"grant_type": "refresh_token", "refresh_token": "rt-old"}
    assert out["access_token"] == "new-jwt"


def test_normalize_ppi_snapshot(tmp_path, monkeypatch) -> None:
    _norm_cfg(tmp_path, monkeypatch)
    snap = {
        "account_details": [
            {
                "account_number": "1",
                "balances_and_positions": {
                    "groupedAvailability": [{"availability": [{"name": "ARS", "amount": 2000, "settlement": "INMEDIATA"}]}],
                    "groupedInstruments": [{"name": "Acciones", "instruments": [{"ticker": "YPF", "amount": 5, "price": 30000, "currency": "ARS"}]}],
                },
                "available_balance": [{"name": "USD", "amount": 50}],
                "movements": [{"ticker": "YPF", "amount": -150000, "currency": "ARS", "settlementDate": "2026-01-05"}],
            }
        ]
    }
    out = financial_normalizer.normalize_provider("ppi", snap)
    assert out["position_count"] == 1
    assert out["positions"][0]["symbol"] == "YPF"
    assert out["cash_by_currency"]["ARS"] == 2000
    assert out["cash_by_currency"]["USD"] == 50
    assert out["transaction_count"] == 1


def test_normalize_binance_snapshot(tmp_path, monkeypatch) -> None:
    _norm_cfg(tmp_path, monkeypatch)
    snap = {"balances": {"total": {"BTC": 0.1, "USDT": 500, "XRP": 0}, "free": {"BTC": 0.1}, "used": {}}}
    out = financial_normalizer.normalize_provider("binance", snap)
    assert out["position_count"] == 2  # BTC + USDT, XRP dropped (zero)
    symbols = {p["symbol"] for p in out["positions"]}
    assert symbols == {"BTC", "USDT"}


def test_consolidated_portfolio_no_fx_mixing(tmp_path, monkeypatch) -> None:
    _norm_cfg(tmp_path, monkeypatch)
    financial_normalizer.save_normalized(
        "iol",
        {"provider": "iol", "positions": [], "transactions": [], "cash_by_currency": {"ARS": 100, "USD": 10}, "position_count": 0, "transaction_count": 0},
    )
    financial_normalizer.save_normalized(
        "binance", {"provider": "binance", "positions": [], "transactions": [], "cash_by_currency": {"USDT": 5}, "position_count": 0, "transaction_count": 0}
    )
    cons = financial_normalizer.consolidated_portfolio()
    assert cons["provider_count"] == 2
    assert cons["cash_by_currency"]["ARS"] == 100
    assert cons["cash_by_currency"]["USD"] == 10
    assert cons["cash_by_currency"]["USDT"] == 5
    # never a single blended total
    assert "total" not in cons


def test_normalized_endpoints(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _norm_cfg(tmp_path, monkeypatch)
    # 404 before any sync
    assert client.get("/api/connection-manager/accounts/cocos/normalized").status_code == 404
    # manual sync triggers normalization
    saved = {}
    monkeypatch.setattr(
        connection_manager,
        "save_snapshot",
        lambda p, payload, source="manual": saved.setdefault(p, {"provider": p, "source": source, "synced_at": "t", "data": payload}),
    )
    client.post("/api/connection-manager/accounts/cocos/connect", json={"email": "u@x.com"})
    resp = client.post(
        "/api/connection-manager/accounts/cocos/sync",
        json={"snapshot": {"positions": [{"ticker": "AL30", "quantity": 100, "price": 80, "currency": "USD"}]}},
    )
    assert resp.status_code == 200
    norm = client.get("/api/connection-manager/accounts/cocos/normalized")
    assert norm.status_code == 200
    assert norm.json()["position_count"] == 1
    cons = client.get("/api/connection-manager/portfolio")
    assert cons.status_code == 200
    assert cons.json()["provider_count"] >= 1


def test_iol_sync_strips_auth_blob_and_stores_refresh(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """_auth secrets must never reach the persisted snapshot."""
    saved: dict[str, dict] = {}
    monkeypatch.setattr(
        connection_manager,
        "save_snapshot",
        lambda p, payload, source="api": saved.setdefault(p, {"provider": p, "source": source, "synced_at": "t", "data": payload}),
    )

    def fake_sync(email, password, refresh_token=None):
        assert refresh_token is None  # first sync: no stored refresh token
        return {
            "authenticated": True,
            "balances": {"ars": {"available": {"t0": 1}, "available_for_withdrawal": 1}},
            "positions": {"positions": []},
            "movements": [],
            "_auth": {"refresh_token": "rt-rotated"},
        }

    monkeypatch.setattr(connection_manager, "sync_iol_account", fake_sync)
    # normalize_provider would write to real data dir — stub it
    monkeypatch.setattr(connection_manager.financial_normalizer, "normalize_provider", lambda *a, **k: {})

    client.post("/api/connection-manager/accounts/iol/connect", json={"email": "io@x.com", "password": "pw"})
    resp = client.post("/api/connection-manager/accounts/iol/sync", json={})
    assert resp.status_code == 200
    stored = saved["iol"]["data"]
    assert "_auth" not in stored
    assert "rt-rotated" not in json.dumps(stored)


def test_iol_sync_uses_stored_refresh_token(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}
    saved: dict[str, dict] = {}
    monkeypatch.setattr(
        connection_manager,
        "save_snapshot",
        lambda p, payload, source="api": saved.setdefault(p, {"provider": p, "source": source, "synced_at": "t", "data": payload}),
    )
    monkeypatch.setattr(connection_manager.financial_normalizer, "normalize_provider", lambda *a, **k: {})

    vault_holder: dict = {}

    class VaultWithSecret(FakeVault):
        def get_secret(self, provider, name):
            return "rt-stored" if name == "refresh_token" else ""

        def set_secret(self, provider, name, value):
            vault_holder[(provider, name)] = value

    vault_instance = VaultWithSecret()
    monkeypatch.setattr(connection_manager, "get_identity_vault", lambda: vault_instance)

    def fake_sync(email, password, refresh_token=None):
        captured["refresh_token"] = refresh_token
        return {"authenticated": True, "_auth": {"refresh_token": "rt-new"}}

    monkeypatch.setattr(connection_manager, "sync_iol_account", fake_sync)
    client.post("/api/connection-manager/accounts/iol/connect", json={"email": "io@x.com", "password": "pw"})
    resp = client.post("/api/connection-manager/accounts/iol/sync", json={})
    assert resp.status_code == 200
    assert captured["refresh_token"] == "rt-stored"
    assert vault_holder[("iol", "refresh_token")] == "rt-new"


def test_binance_valuation_with_quotes(tmp_path, monkeypatch) -> None:
    _norm_cfg(tmp_path, monkeypatch)
    snap = {
        "balances": {"total": {"BTC": 0.5, "USDT": 100}, "free": {"BTC": 0.5}, "used": {}},
        "quotes": {"BTC": {"last": 100000.0, "timestamp": 1700000000000}},
    }
    out = financial_normalizer.normalize_provider("binance", snap)
    btc = next(p for p in out["positions"] if p["symbol"] == "BTC")
    usdt = next(p for p in out["positions"] if p["symbol"] == "USDT")
    assert btc["current_price"] == 100000.0
    assert btc["value"] == 50000.0
    assert btc["currency"] == "USDT"
    assert usdt["value"] == 100.0  # fiat 1:1
    assert btc["extra"]["quote_ts"] == 1700000000000


def test_iol_quote_fallback_valuation(tmp_path, monkeypatch) -> None:
    _norm_cfg(tmp_path, monkeypatch)
    snap = {
        "positions": {"positions": [{"instrument": {"symbol": "GGAL", "currency": "ARS"}, "availability": {"quantity_available": 10}}]},
        "balances": {},
        "quotes": {"GGAL": {"price": 1550.0, "timestamp": "2026-01-01T00:00:00Z"}},
    }
    out = financial_normalizer.normalize_provider("iol", snap)
    pos = out["positions"][0]
    assert pos["current_price"] == 1550.0
    assert pos["value"] == 15500.0
    assert pos["extra"]["quote_ts"] == "2026-01-01T00:00:00Z"


# ── OWNEX MCP server (P12) ──────────────────────────────────────────────


def test_mcp_tool_catalog_is_read_only() -> None:
    from core import mcp_ownex_server

    names = {t.name for t in mcp_ownex_server.TOOLS}
    assert names == {
        "get_ownex_status",
        "list_connected_providers",
        "get_connection_status",
        "get_portfolio_snapshot",
        "get_portfolio_positions",
        "get_cash_balances",
        "get_transaction_history",
        "get_last_sync_results",
        "get_data_quality_report",
    }
    # no write/trade/withdraw tools exist at all
    assert not any(w in n for n in names for w in ("order", "trade", "withdraw", "transfer", "buy", "sell"))


def test_mcp_call_tool_handlers(tmp_path, monkeypatch) -> None:
    from core import mcp_ownex_server

    _norm_cfg(tmp_path, monkeypatch)
    financial_normalizer.save_normalized(
        "iol",
        {
            "provider": "iol",
            "positions": [{"symbol": "GGAL", "quantity": 10, "value": 15000, "currency": "ARS"}],
            "transactions": [{"symbol": "GGAL", "tx_type": "buy", "total": -15000}],
            "cash_by_currency": {"ARS": 50000},
            "position_count": 1,
            "transaction_count": 1,
            "normalized_at": "t",
        },
    )

    status = mcp_ownex_server.call_tool("get_ownex_status", {})
    assert "iol" in status["providers_with_normalized_data"]

    positions = mcp_ownex_server.call_tool("get_portfolio_positions", {"provider": "iol"})
    assert positions["positions"][0]["symbol"] == "GGAL"

    cash = mcp_ownex_server.call_tool("get_cash_balances", {"provider": "iol"})
    assert cash["cash_by_currency"]["ARS"] == 50000

    txs = mcp_ownex_server.call_tool("get_transaction_history", {"provider": "iol"})
    assert txs["count"] == 1

    unknown = mcp_ownex_server.call_tool("get_portfolio_positions", {"provider": "nope"})
    assert "error" in unknown

    bad_tool = mcp_ownex_server.call_tool("place_order", {})
    assert "error" in bad_tool


# ── P13: external portfolio view / revenue separation ───────────────────


def _pv_cfg(tmp_path, monkeypatch):
    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(portfolio_view, "get_config", lambda: fake_cfg)
    monkeypatch.setattr(financial_normalizer, "get_config", lambda: fake_cfg)


def test_transaction_classification_separates_income(tmp_path, monkeypatch) -> None:
    _pv_cfg(tmp_path, monkeypatch)
    financial_normalizer.save_normalized(
        "cocos",
        {
            "provider": "cocos",
            "positions": [],
            "transactions": [
                {"symbol": "GGAL", "tx_type": "buy", "total": -1000, "currency": "ARS", "executed_at": "2026-01-01"},
                {"symbol": "", "tx_type": "deposit", "total": 50000, "currency": "ARS", "executed_at": "2026-01-02"},
                {"symbol": "", "tx_type": "dividend", "total": 120, "currency": "USD", "executed_at": "2026-01-03"},
                {"symbol": "", "tx_type": "", "total": 50, "currency": "ARS", "executed_at": "2026-01-04", "extra": {"description": "Comision por operación"}},
                {"symbol": "", "tx_type": "mystery", "total": 10, "currency": "ARS", "executed_at": "2026-01-05"},
            ],
            "cash_by_currency": {},
            "position_count": 0,
            "transaction_count": 5,
        },
    )
    income = portfolio_view.income_candidates()
    assert len(income) == 1
    assert income[0]["tx_type"] == "dividend"
    # internal moves never become income
    kinds = {t["kind"] for t in portfolio_view.external_transactions()}
    assert "trade" in kinds and "transfer" in kinds and "fee" in kinds and "unknown" in kinds


def test_portfolio_detail_and_endpoints(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _pv_cfg(tmp_path, monkeypatch)
    financial_normalizer.save_normalized(
        "binance",
        {
            "provider": "binance",
            "positions": [{"symbol": "BTC", "quantity": 0.1, "value": 5000, "currency": "USDT"}],
            "transactions": [],
            "cash_by_currency": {"USDT": 100},
            "position_count": 1,
            "transaction_count": 0,
            "normalized_at": "t",
        },
    )
    detail = client.get("/api/connection-manager/portfolio/detail")
    assert detail.status_code == 200
    body = detail.json()
    assert body["provider_count"] == 1
    assert body["positions"][0]["provider"] == "binance"

    txs = client.get("/api/connection-manager/portfolio/transactions")
    assert txs.status_code == 200

    income = client.get("/api/connection-manager/portfolio/income-candidates")
    assert income.status_code == 200
    assert income.json()["count"] == 0


# ── MCP consent + audit (P12 hardening) ─────────────────────────────────


def _consent_cfg(tmp_path, monkeypatch):
    fake_cfg = type("Cfg", (), {"data_dir": tmp_path})()
    monkeypatch.setattr(mcp_consent, "get_config", lambda: fake_cfg)


def test_mcp_consent_default_denies_financial(tmp_path, monkeypatch) -> None:
    _consent_cfg(tmp_path, monkeypatch)
    assert mcp_consent.get_consents() == {"metadata": False, "financial": False}
    ok, _ = mcp_consent.check_tool_allowed("get_ownex_status")
    assert ok  # metadata class always allowed
    ok, reason = mcp_consent.check_tool_allowed("get_portfolio_positions")
    assert not ok and "consentimiento" in reason
    ok, _ = mcp_consent.check_tool_allowed("place_order")
    assert not ok


def test_mcp_consent_grant_and_revoke(tmp_path, monkeypatch) -> None:
    _consent_cfg(tmp_path, monkeypatch)
    mcp_consent.set_consent("financial", True)
    ok, _ = mcp_consent.check_tool_allowed("get_cash_balances")
    assert ok
    mcp_consent.set_consent("financial", False)
    ok, _ = mcp_consent.check_tool_allowed("get_cash_balances")
    assert not ok
    with pytest.raises(ValueError):
        mcp_consent.set_consent("everything", True)


def test_mcp_audit_log(tmp_path, monkeypatch) -> None:
    _consent_cfg(tmp_path, monkeypatch)
    mcp_consent.record_call("get_portfolio_positions", "iol", "ok")
    mcp_consent.record_call("get_cash_balances", "binance", "denied")
    entries = mcp_consent.get_audit()
    assert len(entries) == 2
    assert entries[0]["outcome"] == "denied"  # newest first
    assert entries[1]["data_class"] == "financial"
    assert "arguments" not in entries[0]  # no payloads logged


def test_mcp_consent_endpoints(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _consent_cfg(tmp_path, monkeypatch)
    status = client.get("/api/connection-manager/mcp/consent")
    assert status.status_code == 200
    assert status.json()["consents"]["financial"] is False

    grant = client.post("/api/connection-manager/mcp/consent", json={"data_class": "financial", "granted": True})
    assert grant.status_code == 200
    assert grant.json()["consents"]["financial"] is True

    bad = client.post("/api/connection-manager/mcp/consent", json={"data_class": "root", "granted": True})
    assert bad.status_code == 400

    audit = client.get("/api/connection-manager/mcp/audit")
    assert audit.status_code == 200
