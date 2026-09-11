"""L5b: strategy runner — paper default, explicit arm, envelope, audit."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from cores.trading.contracts import Signal, SignalSide
from cores.trading.risk import RiskEngine
from cores.trading.runner import StrategyEnvelope, StrategyRunner


def _runner(tmp_path, **kw) -> StrategyRunner:
    return StrategyRunner(audit_path=tmp_path / "audit.jsonl", **kw)


def _env(**overrides) -> StrategyEnvelope:
    base = {"strategy_id": "s-1", "allocated_capital_usd": 1000.0}
    base.update(overrides)
    return StrategyEnvelope(**base)


def _signal(**overrides) -> Signal:
    base = {"strategy_id": "s-1", "symbol": "BTC/USDT", "side": SignalSide.BUY}
    base.update(overrides)
    return Signal(**base)


def _audit_lines(tmp_path) -> list[dict]:
    p = tmp_path / "audit.jsonl"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


class TestArming:
    def test_paper_needs_no_arm(self, tmp_path):
        r = _runner(tmp_path)
        r.register(_env())
        assert r.is_armed("s-1") is False

    def test_arm_requires_purpose(self, tmp_path):
        r = _runner(tmp_path, capital_engine=object(), risk_engine=RiskEngine())
        r.register(_env())
        assert r.arm("s-1", "")["armed"] is False
        assert r.arm("s-1", "   ")["armed"] is False
        assert r.is_armed("s-1") is False

    def test_arm_requires_engines(self, tmp_path):
        r = _runner(tmp_path)
        r.register(_env())
        res = r.arm("s-1", "backtest validated 60d")
        assert res["armed"] is False
        assert "engines" in res["reason"]

    def test_arm_disarm_cycle_audited(self, tmp_path):
        r = _runner(tmp_path, capital_engine=object(), risk_engine=RiskEngine())
        r.register(_env())
        assert r.arm("s-1", "paper validated, going live capped")["armed"] is True
        assert r.is_armed("s-1") is True
        assert r.disarm("s-1", "eod")["armed"] is False
        actions = [a["action"] for a in _audit_lines(tmp_path)]
        assert "arm" in actions and "disarm" in actions

    def test_unknown_strategy(self, tmp_path):
        r = _runner(tmp_path)
        assert r.arm("nope", "x")["armed"] is False
        assert r.is_armed("nope") is False


class TestExecution:
    @pytest.mark.asyncio()
    async def test_live_refused_unarmed(self, tmp_path):
        r = _runner(tmp_path, capital_engine=object(), risk_engine=RiskEngine())
        r.register(_env())
        res = await r.run_signal("s-1", _signal(), live=True)
        assert res["success"] is False
        assert "not armed" in res["error"]

    @pytest.mark.asyncio()
    async def test_live_refused_venue(self, tmp_path):
        r = _runner(tmp_path, capital_engine=object(), risk_engine=RiskEngine())
        r.register(_env(venues_allowlist=("kraken",)))
        r.arm("s-1", "testing venue gate")
        sig = _signal()
        sig.metadata = {"exchange": "binance"}
        res = await r.run_signal("s-1", sig, live=True)
        assert res["success"] is False
        assert "allowlist" in res["error"]

    @pytest.mark.asyncio()
    async def test_live_refused_leverage(self, tmp_path):
        r = _runner(tmp_path, capital_engine=object(), risk_engine=RiskEngine())
        r.register(_env())
        r.arm("s-1", "testing leverage gate")
        sig = _signal()
        sig.metadata = {"leverage": 5}
        res = await r.run_signal("s-1", sig, live=True)
        assert res["success"] is False
        assert "leverage" in res["error"]

    @pytest.mark.asyncio()
    async def test_paper_runs_unarmed(self, tmp_path):
        from decimal import Decimal

        from cores.trading.capital import CapitalEngine
        from cores.trading.risk import RiskEngine

        capital = CapitalEngine(initial_capital=Decimal("10000"))
        r = _runner(tmp_path, capital_engine=capital, risk_engine=RiskEngine())
        r.register(_env())
        res = await r.run_signal("s-1", _signal(), live=False)
        assert res["mode"] == "paper"
        assert any(a["action"] == "paper_result" for a in _audit_lines(tmp_path))

    @pytest.mark.asyncio()
    async def test_paper_without_capital_refuses_honestly(self, tmp_path):
        r = _runner(tmp_path)
        r.register(_env())
        res = await r.run_signal("s-1", _signal(), live=False)
        assert res["success"] is False
        assert res["mode"] == "refused"

    @pytest.mark.asyncio()
    async def test_unknown_strategy_refused(self, tmp_path):
        r = _runner(tmp_path)
        res = await r.run_signal("nope", _signal(), live=True)
        assert res["success"] is False


class TestKillSwitch:
    @pytest.mark.asyncio()
    async def test_max_loss_auto_disarms(self, tmp_path):
        risk = RiskEngine()
        risk.metrics.daily_pnl = Decimal("-500")  # way past 2% of $1000
        r = _runner(tmp_path, capital_engine=object(), risk_engine=risk)
        r.register(_env(allocated_capital_usd=1000.0, max_daily_loss_pct=2.0))
        r.arm("s-1", "testing max-loss gate")
        res = await r.run_signal("s-1", _signal(), live=True)
        assert res["success"] is False
        assert "max daily loss" in res["error"]
        assert r.is_armed("s-1") is False
        actions = [a["action"] for a in _audit_lines(tmp_path)]
        assert "auto_disarm_max_loss" in actions

    def test_global_kill_blocks(self, tmp_path):
        import asyncio

        from cores.trading.contracts import KillSwitchLevel

        risk = RiskEngine()
        risk.kill_switch.activate(KillSwitchLevel.GLOBAL, reason="test", trigger="test")
        r = _runner(tmp_path, capital_engine=object(), risk_engine=risk)
        r.register(_env())
        r.arm("s-1", "testing kill gate")
        res = asyncio.run(r.run_signal("s-1", _signal(), live=True))
        assert res["success"] is False
        assert "kill switch" in res["error"]
