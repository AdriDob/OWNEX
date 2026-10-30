"""Pump.fun launch discovery — verdicts puros + fetch mockeado (cero red real)."""

from __future__ import annotations

import pytest

from cores.trading.pumpfun_launch import (
    GRADUATION_MC_USD,
    evaluate_launch,
    graduation_proximity,
    launch_to_token,
)


def _launch(**over):
    base = {
        "mint": "M1" + "x" * 40,
        "symbol": "FRESH",
        "name": "Fresh Coin",
        "usd_market_cap": 12_000.0,
        "total_supply": 1_000_000_000_000_000,
        "base_decimals": 6,
        "real_sol_reserves": 30_000_000_000,
        "created_timestamp": 1_700_000_000_000,
        "complete": False,
        "nsfw": False,
        "is_banned": False,
        "twitter": "https://x.com/fresh",
        "reply_count": 15,
        "creator": "AbC123xyz",
    }
    base.update(over)
    return base


NOW = 1_700_000_000_000 + 5 * 60_000  # 5 min después


def test_fresh_passes_with_reasons():
    v = evaluate_launch(_launch(), now_ms=NOW)
    assert v.passed is True
    assert any(r.startswith("fresh-") for r in v.reasons)
    assert "has-socials" in v.reasons


def test_stale_graduated_nsfw_dust_rejected():
    assert evaluate_launch(_launch(created_timestamp=1), now_ms=NOW).passed is False
    assert evaluate_launch(_launch(complete=True), now_ms=NOW).passed is False
    assert evaluate_launch(_launch(nsfw=True), now_ms=NOW).passed is False
    assert evaluate_launch(_launch(usd_market_cap=100.0), now_ms=NOW).passed is False
    assert evaluate_launch(_launch(usd_market_cap=500_000.0), now_ms=NOW).passed is False
    assert evaluate_launch("basura", now_ms=NOW).passed is False  # type: ignore[arg-type]


def test_graduation_proximity_math():
    assert graduation_proximity(GRADUATION_MC_USD) == 1.0
    assert graduation_proximity(34_500.0) == 0.5
    assert graduation_proximity(None) is None
    assert graduation_proximity(-5) is None


def test_launch_to_token_math():
    tok = launch_to_token(_launch(), sol_price_usd=150.0)
    assert tok["mint"].startswith("M1")
    assert tok["price_usd"] == pytest.approx(12_000.0 / 1_000_000_000)
    assert tok["liquidity_usd"] == pytest.approx(30.0 * 150.0)  # curve, no LP
    assert tok["source"] == "pumpfun"
    assert tok["url"].startswith("https://pump.fun/coin/")


@pytest.mark.asyncio
async def test_scan_merges_only_passing(monkeypatch):
    import time

    import cores.trading.pumpfun_launch as pf

    fresh = _launch(created_timestamp=int(time.time() * 1000) - 5 * 60_000)
    stale = _launch(mint="M2" + "y" * 40, complete=True)

    async def fake_fetch(limit=50):
        return [fresh, stale]

    monkeypatch.setattr(pf, "fetch_new_launches", fake_fetch)
    out = await pf.scan_pumpfun_launches(sol_price_usd=150.0)
    assert [t["symbol"] for t in out] == ["FRESH"]


@pytest.mark.asyncio
async def test_scan_never_raises(monkeypatch):
    import cores.trading.pumpfun_launch as pf

    async def boom(limit=50):
        raise RuntimeError("red caída")

    monkeypatch.setattr(pf, "fetch_new_launches", boom)
    assert await pf.scan_pumpfun_launches() == []


@pytest.mark.asyncio
async def test_paper_scan_merges_pumpfun(monkeypatch):
    import cores.trading.pumpfun_launch as pf
    from cores.trading.paper.memecoin_paper import MemecoinPaperLoop, PaperConfig

    async def fake_launches(sol_price_usd=None):
        return [{"mint": "M9", "symbol": "P", "price_usd": 0.01}]

    monkeypatch.setattr(pf, "scan_pumpfun_launches", fake_launches)
    monkeypatch.setattr(pf, "get_sol_price_usd", lambda: 150.0)

    loop = MemecoinPaperLoop.__new__(MemecoinPaperLoop)
    loop.config = PaperConfig(use_pumpfun_launches=True)
    from cores.trading import risk as _risk  # noqa: F401  (kill sano = ausente)

    loop.kill = None

    class FakeAdapter:
        async def scan_new_tokens(self, *a):
            return []

        async def get_token_metrics(self, *a):
            return {}

    loop.adapter = FakeAdapter()
    out = await loop.scan()
    assert [t["mint"] for t in out] == ["M9"]


@pytest.mark.asyncio
async def test_radar_cycle_snapshot_serializes(monkeypatch):
    """Regresión: el snapshot del ciclo 5m persistía muerto (__dict__ en slots)."""
    import cores.trading.pump_radar as pr

    async def fake_scan(cfg=None, filter_cfg=None, enrich_rug=True):
        return []

    async def fake_launches(sol_price_usd=None):
        return [{"mint": "M1", "symbol": "FRESH"}]

    monkeypatch.setattr(pr, "scan_pump_candidates", fake_scan)
    monkeypatch.setattr("cores.trading.pumpfun_launch.scan_pumpfun_launches", fake_launches)
    monkeypatch.setattr("cores.trading.pumpfun_launch.get_sol_price_usd", lambda: 150.0)

    saved: dict = {}

    class FakeStore:
        def set(self, k, v):
            saved[k] = v

    out = await pr.run_pump_radar_cycle(store=FakeStore())
    assert out["success"] is True
    assert out["fresh_launches_count"] == 1
    assert saved["pump_radar_last"]["count"] == 0
    import json

    json.dumps(saved["pump_radar_last"])  # serializable para TradingStore


@pytest.mark.asyncio
async def test_paper_scan_off_when_disabled(monkeypatch):
    from cores.trading.paper.memecoin_paper import MemecoinPaperLoop, PaperConfig

    loop = MemecoinPaperLoop.__new__(MemecoinPaperLoop)
    loop.config = PaperConfig(use_pumpfun_launches=False)
    loop.kill = None

    class FakeAdapter:
        async def scan_new_tokens(self, *a):
            return []

        async def get_token_metrics(self, *a):
            return {}

    loop.adapter = FakeAdapter()
    assert await loop.scan() == []
