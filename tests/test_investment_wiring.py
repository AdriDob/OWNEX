"""Tests: wiring de sub-adapters de inversión (rutas finas sobre adapters existentes).

Cada grupo verifica las shapes exactas que consume el frontend
({success, connected} / {success, data} / {success, result}) usando adapters
fake inyectados por monkeypatch — sin red ni creds reales.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


class FakeAdapter:
    name = "fake"
    is_connected = True

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    async def connect(self) -> bool:
        return True

    async def get_balance(self) -> dict[str, Any]:
        return {"total": {"USDT": 100.0}}

    async def get_account(self) -> dict[str, Any]:
        return {"equity": 1000}

    async def get_positions(self) -> list[dict[str, Any]]:
        return [{"symbol": "AAPL", "qty": 1}]

    async def place_order(self, **kwargs: Any) -> dict[str, Any]:
        self.last_order = kwargs
        return {"status": "filled", **kwargs}

    async def get_market_data(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "price": 100}

    async def get_option_chain(self, underlying: str) -> list[dict[str, Any]]:
        return [{"underlying": underlying}]

    async def get_supply_apy(self, asset: str = "USDC") -> dict[str, Any]:
        return {"asset": asset, "apy": 5.0}

    async def get_top_assets(self) -> list[dict[str, Any]]:
        return [{"asset": "USDC"}]

    async def get_market_apy(self, market_id: str) -> dict[str, Any]:
        return {"market": market_id, "apy": 8.0}

    async def get_top_markets(self) -> list[dict[str, Any]]:
        return [{"id": "m1"}]

    async def get_yield_opportunities(self) -> list[dict[str, Any]]:
        return [{"market": "pt-usdc"}]

    async def get_pt_yield(self, market_id: str) -> dict[str, Any]:
        return {"market": market_id, "yield": 12.0}

    async def get_staking_apy(self) -> dict[str, Any]:
        return {"apy": 3.4}

    async def get_protocol_metrics(self) -> dict[str, Any]:
        return {"tvl": 1e9}


_TOKEN_CACHE: dict[str, str] = {}


def _device_token(c: TestClient) -> str:
    """Login una sola vez por proceso (rate-limiter rechaza logins repetidos)."""
    if "token" not in _TOKEN_CACHE:
        import os

        prev = os.environ.get("CATEYE_CSRF_DISABLED")
        login = c.post("/api/auth/login", json={"device_id": "inv-wiring-test"})
        _TOKEN_CACHE["token"] = ((login.json().get("data") or {}).get("token")) or ""
        if prev is None:
            os.environ.pop("CATEYE_CSRF_DISABLED", None)
    return _TOKEN_CACHE["token"]


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient autenticado con adapters reemplazados por FakeAdapter."""
    import api.routers.investment as inv

    fake = FakeAdapter()

    async def _fresh(name: str, config: dict[str, Any] | None = None) -> FakeAdapter:
        fake.config = config or {}
        return fake

    monkeypatch.setattr(inv, "_fresh_adapter", _fresh)
    from api.main import app  # noqa: PLC0415

    c = TestClient(app)
    # Device-login real (mismo flujo del frontend); token cacheado por proceso
    # para no chocar con el rate limiter de /auth/login entre tests.
    token = _device_token(c)
    assert token, "device login falló en fixture"
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


class TestCCXT:
    def test_connect(self, client: TestClient) -> None:
        res = client.post(
            "/api/investment/ccxt/connect",
            json={"exchange": "binance", "api_key": "k", "api_secret": "s"},
        )
        assert res.status_code == 200
        assert res.json() == {"success": True, "connected": True}

    def test_balance_registry_path(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        class Reg:
            async def initialize_all(self) -> None:
                pass

            def get_adapter(self, name: str) -> FakeAdapter | None:
                return FakeAdapter() if name == "ccxt" else None

        monkeypatch.setattr(inv_mod().investment, "get_registry", lambda: Reg())
        res = client.get("/api/investment/ccxt/balance?exchange=binance")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True and "balance" in body


def inv_mod():  # helper para acceder al módulo en tests de registry
    import api.routers.investment as inv

    class Wrap:
        investment = inv

    return Wrap()


class TestStocks:
    def test_alpaca_info_shape(self, client: TestClient) -> None:
        body = client.get("/api/investment/stocks/algopaca").json()
        assert set(body) == {"success", "adapter", "connected"}

    def test_alpaca_order_gated_when_paused(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        import api.routers.investment as inv

        class PausedManager:
            def is_paused(self) -> bool:
                return True

        monkeypatch.setattr(inv, "get_investment_manager", lambda: PausedManager())
        res = client.post(
            "/api/investment/stocks/algopaca/order",
            json={"symbol": "AAPL", "side": "buy", "qty": 1},
        )
        assert res.status_code == 409

    def test_alpaca_order_ok(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        import api.routers.investment as inv

        class OpenManager:
            def is_paused(self) -> bool:
                return False

        monkeypatch.setattr(inv, "get_investment_manager", lambda: OpenManager())
        res = client.post(
            "/api/investment/stocks/algopaca/order",
            json={"symbol": "AAPL", "side": "buy", "qty": 2},
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_ibkr_info_and_account(self, client: TestClient) -> None:
        info = client.get("/api/investment/stocks/ibkr").json()
        acc = client.get("/api/investment/stocks/ibkr/account").json()
        assert info["success"] and info["adapter"] == "fake"
        assert acc["success"] and acc["account"] == {"equity": 1000}


class TestDefi:
    @pytest.mark.parametrize(
        ("provider", "path", "key"),
        [
            ("aave", "/api/investment/defi/aave/supply-apy?asset=USDC", "data"),
            ("aave", "/api/investment/defi/aave/top-assets", "assets"),
            ("morpho", "/api/investment/defi/morpho/top-markets", "markets"),
            ("pendle", "/api/investment/defi/pendle/yield-opportunities", "opportunities"),
            ("lido", "/api/investment/defi/lido/staking-apy", "data"),
            ("lido", "/api/investment/defi/lido/protocol-metrics", "metrics"),
        ],
    )
    def test_yield_routes(self, client: TestClient, provider: str, path: str, key: str) -> None:
        body = client.get(path).json()
        assert body["success"] is True
        assert key in body

    def test_morpho_market_apy_requires_param(self, client: TestClient) -> None:
        assert client.get("/api/investment/defi/morpho/market-apy").status_code == 422

    def test_connect_routes(self, client: TestClient) -> None:
        for p in (
            "/api/investment/defi/aave/connect",
            "/api/investment/defi/morpho/connect",
            "/api/investment/defi/pendle/connect",
            "/api/investment/defi/lido/connect",
        ):
            assert client.post(p, json={}).json()["connected"] is True


class TestPolymarket:
    def test_strategies_list(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        import core.polymarket.manager as pm

        monkeypatch.setattr(pm, "list_strategies", lambda: {"whale": "Follow whales"})
        body = client.get("/api/investment/polymarket/strategies").json()
        assert body["success"] and body["strategies"]["whale"].startswith("Follow")

    def test_run_unknown_strategy_404(self, client: TestClient) -> None:
        assert client.post("/api/investment/polymarket/strategies/nope/run").status_code == 404


class TestBacktest:
    def test_validation_short_ge_long(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        import api.routers.investment as inv

        class Reg:
            def get_adapter(self, name: str) -> FakeAdapter | None:
                return None

            async def initialize_all(self) -> None:
                pass

        monkeypatch.setattr(inv, "get_registry", lambda: Reg())
        res = client.post(
            "/api/investment/backtest",
            json={"symbol": "BTC/USD", "short_ma": 50, "long_ma": 20},
        )
        assert res.status_code == 400

    def test_ma_crossover_math(self, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        import api.routers.investment as inv

        class CcxtFake(FakeAdapter):
            # ohlcv sintético: tendencia alcista lineal → crossover temprano
            async def get_ohlcv(self, symbol: str, timeframe: str = "1d", limit: int = 200) -> list[list]:
                base = [100 + i for i in range(120)]
                return [[0, 0, 0, 0, c] for c in base]

        class Reg:
            def get_adapter(self, name: str) -> CcxtFake | None:
                return CcxtFake()

            async def initialize_all(self) -> None:
                pass

        monkeypatch.setattr(inv, "get_registry", lambda: Reg())
        res = client.post(
            "/api/investment/backtest",
            json={"symbol": "BTC/USD", "short_ma": 5, "long_ma": 20, "initial_capital": 10000},
        )
        assert res.status_code == 200
        result = res.json()["result"]
        assert result["trades"] >= 1
        assert result["final_equity"] > 0
        assert "total_return_pct" in result and "buy_and_hold_return_pct" in result
