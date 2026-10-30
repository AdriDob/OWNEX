"""Extra radars — dip + spread, puro + jobs + router (sin red)."""

from __future__ import annotations


def test_dip_score_puro():
    from cores.trading.extra_radars import DipRadarConfig, dip_score

    cfg = DipRadarConfig()
    good = {"priceChange": {"h24": 80, "m5": -20, "h1": -10}, "volume": {"h24": 80_000}, "liquidity": {"usd": 15_000}}
    bad = {"priceChange": {"h24": 10, "m5": 2, "h1": 3}, "volume": {"h24": 5_000}, "liquidity": {"usd": 15_000}}
    assert dip_score(good, cfg) > dip_score(bad, cfg)
    assert dip_score({}, cfg) == 0.0


def test_spread_scan_mockeado(monkeypatch):
    import cores.trading.extra_radars as m

    async def fake_bin():
        return 150.0

    async def fake_jup(amount_sol=0.5):
        return 151.5

    monkeypatch.setattr(m, "_binance_sol_price", fake_bin)
    monkeypatch.setattr(m, "_jupiter_sol_price", fake_jup)

    import asyncio

    snap = asyncio.run(m.scan_spread())
    assert snap["success"] is True
    assert snap["spread_pct"] == 1.0
    assert snap["opportunity"] is True


def test_scheduler_jobs_registrados():
    from cores.scheduler.jobs import get_trading_jobs

    ids = {j.job_id for j in get_trading_jobs()}
    assert "trading_dip_radar" in ids
    assert "trading_spread_radar" in ids
    assert "trading_pump_radar" in ids


def test_router_montado():
    from api.main import app

    paths = {getattr(r, "path", "") for r in app.routes}
    assert any("/dip/radar" in p for p in paths)
    assert any("/spread/radar" in p for p in paths)
