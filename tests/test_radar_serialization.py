"""Los radares tienen que serializar; dataclasses con slots no tienen __dict__.

Por qué existe (2026-10-05): al construir el panel de radares encontré que
`/api/trading/pump/radar` era **un 500 garantizado**:

    "config": cfg.__dict__                  # PumpRadarConfig  → slots=True
    "candidates": [c.__dict__ for c in ...] # PumpCandidate     → slots=True

Un `@dataclass(slots=True)` no tiene `__dict__`. Nunca se notó porque el
endpoint **no tenía un solo consumidor en el frontend** — nadie lo había
llamado nunca. `/dip/radar` tenía el mismo bug.

`dataclasses.asdict()` es el serializador correcto y además es recursivo
(anida dicts/listas), que `__dict__` no garantiza.

Estos tests no pegan red: verifique la SERIALIZACIÓN contra la forma real del
endpoint, que es lo que estaba roto.
"""

from __future__ import annotations

import dataclasses

import pytest

from cores.trading.extra_radars import DipCandidate
from cores.trading.pump_radar import PumpCandidate, PumpRadarConfig


class TestSlotsDataclassesHaveNoDict:
    def test_pump_candidate_no_tiene_dict(self) -> None:
        """Guard del bug: si solders/attrs vuelven a permitirlo, esto avisa."""
        c = PumpCandidate(
            mint="So11111111111111111111111111111111111111112",
            symbol="TEST",
            name="Test Token",
            price_usd=0.001,
            price_change_h24=45.0,
            volume_h24=50_000,
            liquidity_usd=20_000,
            dex="raydium",
            url="https://dexscreener.com/solana/abc",
            pump_score=72.0,
            reasons=("liquidez bajo el umbral",),
            warnings=(),
            passed_filters=True,
            rug={},
        )
        assert not hasattr(c, "__dict__"), "si aparece __dict__, revisá el uso de asdict"
        assert dataclasses.asdict(c)["symbol"] == "TEST"

    def test_pump_radar_config_no_tiene_dict(self) -> None:
        cfg = PumpRadarConfig()
        assert not hasattr(cfg, "__dict__")
        assert "min_liquidity_usd" in dataclasses.asdict(cfg)

    def test_dip_candidate_no_tiene_dict(self) -> None:
        c = DipCandidate(
            mint="So11111111111111111111111111111111111111112",
            symbol="DIP",
            price_usd=0.002,
            price_change_h24=-30.0,
            price_change_m5=-5.0,
            price_change_h1=-18.0,
            volume_h24=40_000,
            liquidity_usd=15_000,
            dip_score=55.0,
            reasons=(),
            warnings=(),
            passed_filters=True,
        )
        assert not hasattr(c, "__dict__")
        assert dataclasses.asdict(c)["symbol"] == "DIP"


class TestRadarSerialization:
    def test_asdict_produce_la_forma_que_el_panel_consume(self) -> None:
        """El panel lee estos campos: si faltan, la tabla sale vacía."""
        c = PumpCandidate(
            mint="MINT123",
            symbol="PUMP",
            name="Pump Token",
            price_usd=0.00123,
            price_change_h24=88.5,
            volume_h24=120_000,
            liquidity_usd=30_000,
            dex="pumpswap",
            url="https://dexscreener.com/solana/xyz",
            pump_score=91.0,
            reasons=("ok",),
            warnings=("rug score medio",),
            passed_filters=False,
            rug={"score": 55},
        )
        d = dataclasses.asdict(c)

        for field in (
            "mint",
            "symbol",
            "name",
            "price_usd",
            "price_change_h24",
            "volume_h24",
            "liquidity_usd",
            "dex",
            "url",
            "pump_score",
            "reasons",
            "warnings",
            "passed_filters",
        ):
            assert field in d, f"el panel necesita '{field}'"

        # Las tuplas de reasons/warnings deben ser serializables a JSON.
        assert isinstance(d["reasons"], (list, tuple))
        assert d["passed_filters"] is False, "el flag de filtros debe viajar tal cual"

    def test_asdict_recursivo_en_rug(self) -> None:
        """`rug` es un dict; asdict lo copia, __dict__ lo habríasharedeado."""
        c = PumpCandidate(
            mint="M",
            symbol="S",
            name="N",
            price_usd=1.0,
            price_change_h24=1.0,
            volume_h24=1,
            liquidity_usd=1,
            dex="d",
            url="u",
            pump_score=1.0,
            reasons=(),
            warnings=(),
            passed_filters=True,
            rug={"score": 12, "risks": ["a"]},
        )
        d = dataclasses.asdict(c)
        assert d["rug"] == {"score": 12, "risks": ["a"]}
        d["rug"]["score"] = 99
        assert c.rug["score"] == 12, "asdict debe COPIAR, no aliasar el dict original"


class TestRouterUsesAsdict:
    def test_el_router_no_usa_dict_para_radares(self) -> None:
        """Guard de regresión sobre el archivo real del router."""
        import inspect

        import api.routers.trading as mod

        src = inspect.getsource(mod)
        radar_lines = [ln.strip() for ln in src.splitlines() if "__dict__" in ln]
        # Quedan permitidos sólo en dna/proposals (dataclasses sin slots).
        offenders = [ln for ln in radar_lines if "candidates" in ln or "config" in ln]
        assert not offenders, f"los radares no deben usar __dict__: {offenders}"


@pytest.mark.parametrize("path", ["/api/trading/pump/radar", "/api/trading/dip/radar"])
def test_radar_no_es_500_por_serializacion(path: str) -> None:
    """El bug era un 500. Con __dict__ sobre slots=True es 500 garantizado.

    NO pegamos red: interceptamos el scan con un candidato real, así el
    endpoint ejecuta su serialización de verdad y el test es determinista.
    """
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import api.routers.trading as mod

    app = FastAPI()
    app.include_router(mod.router)
    client = TestClient(app)

    if "pump" in path:
        from cores.trading.pump_radar import PumpCandidate

        cands = [
            PumpCandidate(
                mint="M",
                symbol="S",
                name="N",
                price_usd=1.0,
                price_change_h24=1.0,
                volume_h24=1,
                liquidity_usd=1,
                dex="d",
                url="u",
                pump_score=1.0,
                reasons=(),
                warnings=(),
                passed_filters=True,
                rug={},
            )
        ]

        async def _fake(cfg):  # noqa: ARG001
            return cands

        patcher = patch("cores.trading.pump_radar.scan_pump_candidates", side_effect=_fake)
    else:
        from cores.trading.extra_radars import DipCandidate

        cands = [
            DipCandidate(
                mint="M",
                symbol="S",
                price_usd=1.0,
                price_change_h24=-1.0,
                price_change_m5=-1.0,
                price_change_h1=-1.0,
                volume_h24=1,
                liquidity_usd=1,
                dip_score=1.0,
                reasons=(),
                warnings=(),
                passed_filters=True,
            )
        ]

        async def _fake(cfg):  # noqa: ARG001
            return cands

        patcher = patch("cores.trading.extra_radars.scan_dip_candidates", side_effect=_fake)

    with patcher:
        r = client.get(path)

    assert r.status_code == 200, f"{path} devolvió {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body.get("success") is True
    assert len(body.get("candidates") or []) == 1, "el candidato serializado debe volver"
