"""Tests for financial connections milestone: PPI, Binance, importer, history."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers import connection_manager
from cores.brokers import binance_client, ppi_client
from cores.connections import financial_normalizer, importer, sync_history


class FakeVault:
    SUPPORTED_PROVIDERS = []

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
    snap = {
        "positions": [{"ticker": "GGAL", "quantity": 10, "price": 1500, "currency": "ARS", "value": 15000}],
        "balances": {"ARS": 50000, "USD": 100},
        "movements": [{"ticker": "GGAL", "type": "buy", "amount": -15000, "currency": "ARS", "date": "2026-01-01"}],
    }
    out = financial_normalizer.normalize_provider("iol", snap)
    assert out["position_count"] == 1
    assert out["positions"][0]["symbol"] == "GGAL"
    assert out["cash_by_currency"] == {"ARS": 50000, "USD": 100}
    assert out["transaction_count"] == 1
    assert financial_normalizer.load_normalized("iol")["provider"] == "iol"


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
