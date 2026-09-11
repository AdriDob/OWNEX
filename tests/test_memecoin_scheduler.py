"""Memecoin paper scheduler wiring — resolution + cycle with fakes (no network)."""

from __future__ import annotations

import importlib

from cores.scheduler.jobs import get_all_jobs, get_trading_jobs
from cores.trading.paper.memecoin_paper import PaperConfig, run_paper_cycle_once

MINT = "MintAAA1111111111111111111111111111111111111"


class FakeAdapter:
    def __init__(self, tokens, rugs):
        self._tokens = tokens
        self._rugs = rugs

    async def scan_new_tokens(self, min_liq=None):
        return self._tokens

    async def get_token_metrics(self, mint):
        return self._rugs.get(mint)


class FakeStore:
    def __init__(self):
        self.state: dict = {}

    def get(self, key):
        return self.state.get(key)

    def set(self, key, value):
        self.state[key] = value


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


class TestJobWiring:
    def test_paper_job_registered(self):
        ids = [j.job_id for j in get_trading_jobs()]
        assert "trading_memecoin_paper" in ids

    def test_handler_resolves_to_callable(self):
        job = next(j for j in get_trading_jobs() if j.job_id == "trading_memecoin_paper")
        assert job.app_id == "trading"
        handler_path: str = job.handler  # type: ignore[assignment]
        module_path, name = handler_path.rsplit(":", 1)
        fn = getattr(importlib.import_module(module_path), name)
        assert callable(fn)

    def test_job_visible_in_all_jobs(self):
        all_ids = [j.job_id for jobs in get_all_jobs().values() for j in jobs]
        assert "trading_memecoin_paper" in all_ids


class TestPaperCycle:
    async def test_full_cycle_enter_and_exit(self):
        from cores.trading.risk import KillSwitchManager

        loop_store = FakeStore()
        summary = await run_paper_cycle_once(
            adapter=FakeAdapter([token()], {MINT: rug()}),
            store=loop_store,
            kill=KillSwitchManager(),
            config=PaperConfig(position_sol=1.0, max_open_positions=3, daily_loss_limit_sol=5.0),
            max_new=3,
        )
        assert summary["entered"] == [MINT]
        assert summary["open_positions"] == 1
        assert summary["kill_active"] is False
        assert loop_store.get("memecoin_paper_positions") is not None

    async def test_cycle_never_raises_without_network(self):
        class DeadAdapter:
            async def scan_new_tokens(self, min_liq=None):
                raise RuntimeError("offline")

            async def get_token_metrics(self, mint):
                raise RuntimeError("offline")

        summary = await run_paper_cycle_once(adapter=DeadAdapter(), store=FakeStore(), kill=None, max_new=1)
        assert summary["entered"] == []
        assert summary["kill_active"] is False

    def test_sync_entrypoint_never_raises(self):
        from cores.trading.paper.memecoin_paper import run_memecoin_paper_cycle

        out = run_memecoin_paper_cycle()
        assert isinstance(out, dict) and "status" in out
