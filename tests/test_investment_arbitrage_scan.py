"""Tests for the investment arbitrage scan runner (read-only, paper)."""

import asyncio
import json

from cores.investment.tasks import run_arbitrage_scan_once, run_investment_arbitrage_scan


class _FakeAdapter:
    """Fake adapter: returns canned gaps, records any trade attempt."""

    def __init__(self, gaps=None, raise_on_scan=False):
        self._gaps = (
            gaps
            if gaps is not None
            else [
                {
                    "symbol": "BTC/USDT",
                    "buy_on": "kraken",
                    "buy_price": 65432,
                    "sell_on": "coinbase",
                    "sell_price": 65890,
                    "spread_pct": 0.7,
                    "estimated_profit_usd": 70.0,
                }
            ]
        )
        self._raise = raise_on_scan
        self.trade_attempts: list = []

    async def scan_opportunities(self):
        if self._raise:
            raise ConnectionError("offline")
        return self._gaps

    async def execute_trade(self, opportunity):
        self.trade_attempts.append(opportunity)
        raise AssertionError("runner must never call execute_trade")


def test_scan_returns_gaps_and_snapshot(tmp_path):
    snap = tmp_path / "arb.json"
    out = asyncio.run(run_arbitrage_scan_once(adapter=_FakeAdapter(), snapshot_path=snap))
    assert out["status"] == "ok"
    assert out["count"] == 1
    assert out["opportunities"][0]["symbol"] == "BTC/USDT"
    assert out["note"] == "read-only scan; no orders placed"
    persisted = json.loads(snap.read_text(encoding="utf-8"))
    assert persisted["count"] == 1


def test_runner_never_trades(tmp_path):
    fake = _FakeAdapter()
    snap = tmp_path / "arb.json"
    asyncio.run(run_arbitrage_scan_once(adapter=fake, snapshot_path=snap))
    assert fake.trade_attempts == []


def test_scan_offline_degrades_to_empty(tmp_path):
    snap = tmp_path / "arb.json"
    out = asyncio.run(run_arbitrage_scan_once(adapter=_FakeAdapter(raise_on_scan=True), snapshot_path=snap))
    assert out["status"] == "ok"
    assert out["count"] == 0
    assert out["opportunities"] == []


def test_scheduler_entrypoint_resolves_and_runs():
    from cores.scheduler.jobs import get_investment_jobs

    ids = [j.job_id for j in get_investment_jobs()]
    assert "investment_arbitrage_scan" in ids
    job = next(j for j in get_investment_jobs() if j.job_id == "investment_arbitrage_scan")
    assert job.app_id == "investment"
    handler_path: str = job.handler  # type: ignore[assignment]
    assert handler_path == "cores.investment.tasks:run_investment_arbitrage_scan"

    import importlib

    mod_name, attr = handler_path.rsplit(":", 1)
    fn = getattr(importlib.import_module(mod_name), attr)
    assert fn is run_investment_arbitrage_scan


def test_entrypoint_never_raises_without_ccxt(monkeypatch, tmp_path):
    """Without ccxt installed, the default adapter degrades honestly."""
    import cores.investment.tasks as tasks

    monkeypatch.setattr(tasks, "_default_snapshot_path", lambda: tmp_path / "arb.json")
    try:
        import ccxt  # noqa: F401

        ccxt_present = True
    except ImportError:
        ccxt_present = False
    out = run_investment_arbitrage_scan()
    assert out["status"] in ("ok", "error", "timeout")
    assert "count" in out
    if not ccxt_present:
        # dry-run fallback returns the documented mock gap, still read-only
        assert out["status"] == "ok"
