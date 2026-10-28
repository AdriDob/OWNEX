"""Copy trading: la cadena discovery → master, y que|leaderboard no mienta.

Por qué existe (auditoría 2026-10-05). La cadena estaba rota en **3 puntos**:

1. `TraderDiscovery._polymarket_candidates` era **sync** pero
   `SmartMoneyCopier.scan_top_traders` es **async** → `for item in raw`
   recibía un coroutine → `TypeError: 'coroutine' object is not iterable` →
   discovery devolvía 0 candidatos siempre. El log decía "continuing".

2. El leaderboard migró de `gamma-api.polymarket.com/leaderboard` a
   `data-api.polymarket.com/v1/leaderboard` (docs oficiales). La URL vieja
   devuelve **404** verificado.

3. Aunque ambos bugs se arreglaran, **nada conectaba discovery con
   `add_master`**: los masters se cargaban a mano. Este archivo fija el
   endpoint `/intelligence/promote`, que es ese puente.

Y una regla que estos tests protegen: **descubrir ≠ autorizar**. El leaderboard
NO expone win_rate ni número de trades, así que ningún trader pasa el
BacktestValidator (exige 5/6 checks). El sistema debe devolver 0 agregados y
decir por qué, no inventar métricas para que pasen.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routers.trading as tr

# Forma REAL devuelta por data-api.polymarket.com/v1/leaderboard (verificado)
LEADERBOARD_ROW = {
    "rank": "1",
    "proxyWallet": "0x51698a47f840a242abc2ca0351371c7ffacf4142",
    "userName": "00gringo00",
    "xUsername": "",
    "verifiedBadge": False,
    "vol": 28_166_736.98,
    "pnl": 3_654_334.78,
    "profileImage": "",
}


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(tr.router)
    return TestClient(app)


class TestLeaderboardApiMigration:
    def test_usa_data_api_no_gamma(self) -> None:
        """Guard: la URL vieja da 404, no devolvería datos.

        Chequea el CÓDIGO, no el docstring (que menciona la URL vieja a
        propósito, para documentar la migración).
        """
        import inspect

        from cores.polymarket.strategies import SmartMoneyCopier

        src = inspect.getsource(SmartMoneyCopier.scan_top_traders)
        code = "\n".join(
            ln
            for ln in src.splitlines()
            if not ln.strip().startswith("#") and "http" not in ln.lower() or "await" in ln
        )
        # La llamada real debe ir a data-api
        assert '"https://data-api.polymarket.com/v1/leaderboard"' in src
        # Y no debe haber una petición GET a la ruta gamma leaderboard
        assert 'f"https://gamma-api.polymarket.com/leaderboard' not in src
        assert 'get("https://gamma-api.polymarket.com/leaderboard' not in src
        assert code is not None

    def test_parsea_camelcase_y_proxy_wallet(self) -> None:
        """La API devuelve camelCase y keyea por proxyWallet, no address."""
        import asyncio

        from cores.polymarket.strategies import SmartMoneyCopier

        trader = SmartMoneyCopier()

        class _Resp:
            status_code = 200

            def json(self):
                return [LEADERBOARD_ROW]

        client_mock = MagicMock()
        client_mock.__aenter__ = AsyncMock(return_value=client_mock)
        client_mock.__aexit__ = AsyncMock(return_value=False)
        client_mock.get = AsyncMock(return_value=_Resp())

        with patch("httpx.AsyncClient", return_value=client_mock):
            out = asyncio.run(trader.scan_top_traders(limit=1))

        assert len(out) == 1
        assert out[0]["address"] == LEADERBOARD_ROW["proxyWallet"], "key por proxyWallet"
        assert out[0]["volume"] == LEADERBOARD_ROW["vol"], "vol, no volume"
        assert out[0]["pnl"] == LEADERBOARD_ROW["pnl"]
        assert out[0]["user_name"] == LEADERBOARD_ROW["userName"]

    def test_win_rate_queda_en_cero_porque_no_existe(self) -> None:
        """El leaderboard NO expone win_rate. Dejarlo 0 (UNKNOWN), no inventar."""
        import asyncio

        from cores.polymarket.strategies import SmartMoneyCopier

        trader = SmartMoneyCopier()

        class _Resp:
            status_code = 200

            def json(self):
                return [LEADERBOARD_ROW]

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=cm)
        cm.__aexit__ = AsyncMock(return_value=False)
        cm.get = AsyncMock(return_value=_Resp())

        with patch("httpx.AsyncClient", return_value=cm):
            out = asyncio.run(trader.scan_top_traders(limit=1))

        assert out[0]["win_rate"] == 0, "no hay win_rate en el leaderboard: 0 = desconocido"
        assert out[0]["trades"] == 0, "no hay tradesCount en el leaderboard"


class TestDiscoveryIsAsync:
    def test_polymarket_candidates_es_async(self) -> None:
        """Guard: si vuelve a ser sync, el await de scan_top_traders explota."""
        import inspect

        from cores.trading.trader_intelligence import TraderDiscovery

        assert inspect.iscoroutinefunction(TraderDiscovery._polymarket_candidates), (
            "debe ser async: SmartMoneyCopier.scan_top_traders es una coroutine"
        )

    def test_trader_from_dict_mapea_user_name(self) -> None:
        """La API devuelve user_name; si no se mapea, el nombre queda vacío."""
        from cores.trading.trader_intelligence import TraderDiscovery

        m = TraderDiscovery._trader_from_dict(
            {"address": "0xabc", "user_name": "alguien", "pnl": 100.0, "volume": 500.0},
            source="polymarket",
        )
        assert m.name == "alguien"
        assert m.trader_id == "0xabc"
        assert m.pnl_usd == 100.0


class TestPromoteRequiresEvidence:
    """Descubrir ≠ autorizar. Sin evidencia suficiente, NO se agrega."""

    def _scored(self, passed: int) -> list[dict]:
        return [
            {
                "trader": {
                    "trader_id": "0xdead",
                    "name": "trader",
                    "source": "polymarket",
                },
                "score": 20.0,
                "tier": "A",
                "validation": {"passed": passed, "total": 6, "approved": passed >= 5},
            }
        ]

    def test_sin_evidencia_no_agrega(self, client: TestClient) -> None:
        with (
            patch.object(tr.TraderDiscovery, "discover_scored", AsyncMock(return_value=self._scored(1))),
            patch("cores.trading.copy_trading.CopyTradingEngine") as engine_cls,
        ):
            engine_cls.return_value.get_master.return_value = None
            r = client.post("/api/trading/intelligence/promote")

        assert r.status_code == 200
        body = r.json()
        assert body["added_count"] == 0
        assert body["skipped_count"] == 1
        assert "evidencia insuficiente" in body["skipped"][0]["reason"]

    def test_con_evidencia_agrega_desarmado(self, client: TestClient) -> None:
        with (
            patch.object(tr.TraderDiscovery, "discover_scored", AsyncMock(return_value=self._scored(6))),
            patch("cores.trading.copy_trading.CopyTradingEngine") as engine_cls,
        ):
            engine_cls.return_value.get_master.return_value = None
            engine_cls.return_value.add_master = MagicMock()
            r = client.post("/api/trading/intelligence/promote")

        body = r.json()
        assert body["added_count"] == 1
        added = body["added"][0]
        assert added["master_id"] == "0xdead"
        # DESCUBRIR NO ES ARMAR: el Human Gate es armar explícitamente.
        assert added["enabled"] is False, "un trader descubierto entra DESARMADO"

        trader_arg = engine_cls.return_value.add_master.call_args.args[0]
        assert trader_arg.enabled is False, "add_master debe recibir enabled=False"

    def test_ya_seguido_no_duplica(self, client: TestClient) -> None:
        with (
            patch.object(tr.TraderDiscovery, "discover_scored", AsyncMock(return_value=self._scored(6))),
            patch("cores.trading.copy_trading.CopyTradingEngine") as engine_cls,
        ):
            engine_cls.return_value.get_master.return_value = {"master_id": "0xdead"}
            r = client.post("/api/trading/intelligence/promote")

        body = r.json()
        assert body["added_count"] == 0
        assert "ya lo seguís" in body["skipped"][0]["reason"]
        engine_cls.return_value.add_master.assert_not_called()

    def test_la_respuesta_explica_como_armar(self, client: TestClient) -> None:
        with (
            patch.object(tr.TraderDiscovery, "discover_scored", AsyncMock(return_value=[])),
            patch("cores.trading.copy_trading.CopyTradingEngine"),
        ):
            r = client.post("/api/trading/intelligence/promote")
        assert "toggle" in r.json()["note"], "la respuesta debe decir cómo armar el master"
