"""Memecoin paper loop — full cycle with fakes (no network, no funds)."""

from __future__ import annotations

import pytest

from cores.trading.paper.memecoin_paper import MemecoinPaperLoop, PaperConfig, paper_metrics
from cores.trading.risk import KillSwitchLevel, KillSwitchManager

MINT = "MintAAA1111111111111111111111111111111111111"


class FakeAdapter:
    def __init__(self, tokens, rugs):
        self._tokens = tokens
        self._rugs = rugs

    async def scan_new_tokens(self, min_liq=None):
        return self._tokens

    async def get_token_metrics(self, mint):
        return self._rugs.get(mint)


def token(price="0.001"):
    return {
        "mint": MINT,
        "symbol": "AAA",
        "liquidity_usd": 50_000,
        "volume_h24": 80_000,
        "price_usd": price,
        "pair_created_at": 1_757_000_000_000 - 3_600_000,
        "boosts_active": 0,
    }


def rug():
    return {
        "holder_count": 300,
        "top_10_pct": 12.0,
        "liquidity_locked": True,
        "mint_disabled": True,
        "freeze_disabled": True,
        "score": 5,
        "risks": [],
    }


def make_loop(**overrides):
    cfg_kwargs = {"position_sol": 1.0, "max_open_positions": 3, "daily_loss_limit_sol": 5.0}
    cfg_kwargs.update(overrides)
    return MemecoinPaperLoop(FakeAdapter([token()], {MINT: rug()}), config=PaperConfig(**cfg_kwargs))


class TestScanEnter:
    async def test_scan_returns_filtered_candidate(self):
        loop = make_loop()
        cands = await loop.scan()
        assert len(cands) == 1 and cands[0]["mint"] == MINT

    async def test_scan_blocked_by_kill(self):
        from cores.trading.risk import KillSwitchLevel as L

        kill = KillSwitchManager()
        kill.activate(L.STRATEGY, "test", affected=["memecoin_v1"])
        loop = MemecoinPaperLoop(FakeAdapter([token()], {MINT: rug()}), kill=kill)
        assert await loop.scan() == []

    async def test_enter_records_position(self):
        loop = make_loop()
        pos = await loop.enter(token(), now=1000.0)
        assert pos is not None and pos.entry_sol == 1.0
        assert len(loop.open_positions()) == 1

    async def test_enter_respects_cap_and_duplicates(self):
        loop = MemecoinPaperLoop(
            FakeAdapter([token()], {MINT: rug()}),
            config=PaperConfig(position_sol=1.0, max_open_positions=1),
        )
        assert await loop.enter(token(), now=1000.0) is not None
        assert await loop.enter(token(), now=1001.0) is None  # duplicate + cap


class TestTrackExit:
    async def test_take_profit_closes_staged_then_rest(self):
        loop = make_loop()
        await loop.enter(token("0.001"), now=1000.0)

        async def price(mint):
            return 0.0016  # +60% -> first tier +50%

        closed = await loop.track(price, now=1060.0)
        assert len(closed) == 1
        assert closed[0].exit_reason.startswith("take_profit")
        assert closed[0].pnl_sol > 0
        assert len(loop.open_positions()) == 1  # half remains

    async def test_stop_loss_closes_fully_with_loss(self):
        loop = make_loop()
        await loop.enter(token("0.001"), now=1000.0)

        async def price(mint):
            return 0.0007  # -30%

        closed = await loop.track(price, now=1060.0)
        assert len(closed) == 1
        assert closed[0].exit_reason.startswith("stop_loss")
        assert closed[0].pnl_sol < 0
        assert loop.open_positions() == []

    async def test_price_failure_skips(self):
        loop = make_loop()
        await loop.enter(token("0.001"), now=1000.0)

        async def price(mint):
            raise RuntimeError("feed down")

        assert await loop.track(price, now=1060.0) == []
        assert len(loop.open_positions()) == 1


class TestKillAndMetrics:
    async def test_daily_loss_trips_kill(self):
        kill = KillSwitchManager()
        loop = MemecoinPaperLoop(
            FakeAdapter([token()], {MINT: rug()}),
            kill=kill,
            config=PaperConfig(position_sol=1.0, daily_loss_limit_sol=0.01),
        )
        await loop.enter(token("0.001"), now=1000.0)

        async def price(mint):
            return 0.0005

        await loop.track(price, now=1060.0)
        assert kill.is_active(KillSwitchLevel.STRATEGY, "memecoin_v1") is True
        assert loop.kill_active() is True

    def test_metrics_empty(self):
        m = paper_metrics([])
        assert m["trades"] == 0 and m["verdict"] == "NO_DATA"

    def test_metrics_mixed(self):
        from cores.trading.paper.memecoin_paper import PaperTrade

        trades = [
            PaperTrade(MINT, "AAA", 1.0, 1.5, 0.5, "take_profit", 1.0, 2.0),
            PaperTrade(MINT, "AAA", 1.0, 0.7, -0.3, "stop_loss", 3.0, 4.0),
            PaperTrade(MINT, "AAA", 1.0, 1.2, 0.2, "take_profit", 5.0, 6.0),
        ]
        m = paper_metrics(trades)
        assert m["trades"] == 3 and m["wins"] == 2
        assert m["win_rate"] == pytest.approx(0.667, abs=0.001)
        assert m["profit_factor"] == pytest.approx(0.7 / 0.3, abs=0.01)
        assert m["verdict"] == "NO_EDGE"  # n < 20
