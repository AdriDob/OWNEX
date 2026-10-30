"""Pump radar — puro + integración con filtros hard (sin red real)."""

from __future__ import annotations

import pytest


def _pair(ch24=50, vol=50_000, liq=15_000, boosts=1):
    return {
        "priceChange": {"h24": ch24},
        "volume": {"h24": vol},
        "liquidity": {"usd": liq},
        "boosts": {"active": boosts},
    }


def test_pump_score_basico():
    from cores.trading.pump_radar import PumpRadarConfig, pump_score

    cfg = PumpRadarConfig()
    assert pump_score(_pair(50, 50_000, 10_000, 2), cfg) > pump_score(_pair(20, 10_000, 10_000, 0), cfg)
    assert 0 <= pump_score(_pair(-10, 50_000, 10_000, 0), cfg) <= 40


def test_pump_score_puro_no_raise():
    from cores.trading.pump_radar import pump_score

    assert pump_score({}, __import__("cores.trading.pump_radar", fromlist=["PumpRadarConfig"]).PumpRadarConfig()) == 0.0


def test_config_defaults_honestos():
    from cores.trading.pump_radar import PumpRadarConfig

    cfg = PumpRadarConfig()
    assert cfg.min_price_change_h24_pct == 20.0
    assert cfg.w_change_h24 + cfg.w_volume_ratio + cfg.w_boost == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_scan_prefiltra_sin_rug(monkeypatch):
    from cores.trading.pump_radar import PumpRadarConfig, scan_pump_candidates

    async def fake_search():
        return [
            {
                "chainId": "solana",
                "pairAddress": "p1",
                "baseToken": {"address": "M1", "symbol": "A"},
                "priceUsd": "1",
                "priceChange": {"h24": 80},
                "volume": {"h24": 100_000},
                "liquidity": {"usd": 20_000},
                "dexId": "raydium",
                "url": "https://dexscreener.com/solana/p1",
                "boosts": {"active": 1},
            },
            {
                "chainId": "solana",
                "pairAddress": "p2",
                "baseToken": {"address": "M2", "symbol": "B"},
                "priceUsd": "1",
                "priceChange": {"h24": 5},
                "volume": {"h24": 100_000},
                "liquidity": {"usd": 20_000},
                "dexId": "raydium",
                "url": "",
                "boosts": {"active": 0},
            },
        ]

    monkeypatch.setattr("cores.trading.pump_radar._fetch_dexsearch_candidates", fake_search)
    # Sin RugCheck para no tocar red
    cands = await scan_pump_candidates(PumpRadarConfig(max_candidates=5), enrich_rug=False)
    assert len(cands) == 1 and cands[0].mint == "M1"


def test_scheduler_job_registrado():
    from cores.scheduler.jobs import get_trading_jobs

    ids = {j.job_id for j in get_trading_jobs()}
    assert "trading_pump_radar" in ids


def test_router_montado():
    from api.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert any("/pump/radar" in p for p in paths)
    assert any("/pump/last" in p for p in paths)
    assert any("/pump/simulate" in p for p in paths)
    assert any("/pump/approve" in p for p in paths)
    assert any("/pump/execute" in p for p in paths)
