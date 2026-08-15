"""Tests for the trading layer — copy trading, trader intelligence, reasoning.

Engine tests use dry-run execution and in-memory stores (no network, no DB
writes). Decision journal logging is monkeypatched to keep tests hermetic.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from core.trading.config import TradingConfig
from core.trading.copy_trading import CopyTradingEngine, FollowedTrader, MasterTrade, RiskControls
from core.trading.executor import DryRunExecutor
from core.trading.models import OrderSide
from core.trading.reasoning import AutoParamOptimizer, DecisionCorrelator, StrategyDNA
from core.trading.store import TradingStore
from core.trading.trader_intelligence import (
    BacktestValidator,
    LiveTraderMonitor,
    TraderDiscovery,
    TraderMetrics,
    TraderScorer,
)


@pytest.fixture()
def store(tmp_path) -> TradingStore:
    return TradingStore(data_dir=tmp_path / "trading")


@pytest.fixture()
def engine(store: TradingStore) -> CopyTradingEngine:
    return CopyTradingEngine(
        store=store, config=TradingConfig(), executor=DryRunExecutor(TradingConfig()), log_decisions=False
    )


def _good_trader() -> TraderMetrics:
    return TraderMetrics(
        trader_id="t1",
        name="Alpha Whale",
        source="polymarket",
        total_trades=250,
        win_rate=62.0,
        profit_factor=1.8,
        sharpe=2.4,
        max_dd_pct=12.0,
        consistency=0.75,
        pnl_usd=45000,
        volume_usd=500000,
        age_days=300,
        period_days=180,
    )


# ---------------------------------------------------------------- copy engine


class TestCopyTradingEngine:
    def test_add_and_list_master(self, engine: CopyTradingEngine) -> None:
        trader = FollowedTrader(master_id="m1", name="Master One")
        engine.add_master(trader)
        masters = engine.list_masters()
        assert len(masters) == 1
        assert masters[0].master_id == "m1"

    def test_add_master_duplicate_rejected(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1"))
        with pytest.raises(ValueError):
            engine.add_master(FollowedTrader(master_id="m1", name="M1 again"))

    def test_add_master_invalid_ratio(self, engine: CopyTradingEngine) -> None:
        with pytest.raises(ValueError):
            engine.add_master(FollowedTrader(master_id="m2", name="M2", copy_ratio=2.0))

    def test_remove_master(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1"))
        assert engine.remove_master("m1") is True
        assert engine.remove_master("m1") is False

    def test_toggle_master_enabled(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1"))
        master = engine.get_master("m1")
        assert master is not None
        assert master.enabled is True
        assert engine.set_master_enabled("m1", False) is True
        updated = engine.get_master("m1")
        assert updated is not None
        assert updated.enabled is False
        assert engine.set_master_enabled("ghost", False) is False

    def test_replicate_unknown_master_rejected(self, engine: CopyTradingEngine) -> None:
        trade = MasterTrade(
            master_id="ghost", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=Decimal("60000")
        )
        result = engine.replicate("ghost", trade)
        assert result.success is False
        assert result.reason == "master not followed"

    def test_replicate_executes_in_dry_run(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1", copy_ratio=0.1, max_position_pct=100.0))
        trade = MasterTrade(
            master_id="m1", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=Decimal("60000")
        )
        result = engine.replicate("m1", trade)
        assert result.success is True
        assert result.simulated is True
        assert result.size_usd == Decimal("1000")  # capped at 100% of $1000 dry-run equity
        assert result.order is not None
        assert engine.open_positions()["m1"]

    def test_replicate_requires_price(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1"))
        trade = MasterTrade(master_id="m1", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=None)
        result = engine.replicate("m1", trade)
        assert result.success is False

    def test_replicate_respects_position_cap(self, engine: CopyTradingEngine) -> None:
        trader = FollowedTrader(master_id="m1", name="M1", copy_ratio=1.0, max_position_pct=1.0)
        engine.add_master(trader)
        trade = MasterTrade(
            master_id="m1", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=Decimal("60000")
        )
        result = engine.replicate("m1", trade)
        assert result.success is True
        assert result.size_usd <= Decimal("10")  # 1% of $1000 dry-run equity

    def test_replicate_blocks_symbol_not_allowed(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1", allowed_symbols=["ETH-USD"]))
        trade = MasterTrade(
            master_id="m1", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=Decimal("60000")
        )
        result = engine.replicate("m1", trade)
        assert result.success is False
        assert "not allowed" in result.reason

    def test_replicate_blocks_when_master_dd_beyond_stop(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1", risk=RiskControls(stop_on_master_dd_pct=15.0)))
        trade = MasterTrade(
            master_id="m1",
            pair="BTC-USD",
            side=OrderSide.BUY,
            quantity=Decimal("1"),
            price=Decimal("60000"),
            master_dd_pct=40.0,
        )
        result = engine.replicate("m1", trade)
        assert result.success is False
        assert "drawdown" in result.reason

    def test_daily_dd_blocks_replication(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1", risk=RiskControls(max_daily_dd_pct=3.0)))
        engine.record_daily_pnl("m1", -80.0)  # 8% dd on $1000 equity
        trade = MasterTrade(
            master_id="m1", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=Decimal("60000")
        )
        result = engine.replicate("m1", trade)
        assert result.success is False
        assert "risk" in result.reason

    def test_emergency_stop_blocks_and_cancels(self, engine: CopyTradingEngine) -> None:
        engine.add_master(FollowedTrader(master_id="m1", name="M1"))
        trade = MasterTrade(
            master_id="m1", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=Decimal("60000")
        )
        engine.replicate("m1", trade)
        stop = engine.emergency_stop("test")
        assert stop["reason"] == "test"
        assert engine.status()["emergency_stop"] is True
        trade2 = MasterTrade(
            master_id="m1", pair="BTC-USD", side=OrderSide.BUY, quantity=Decimal("1"), price=Decimal("60000")
        )
        assert engine.replicate("m1", trade2).success is False

    def test_release_emergency_stop(self, engine: CopyTradingEngine) -> None:
        engine.emergency_stop("test")
        engine.release_emergency_stop()
        assert engine.status()["emergency_stop"] is False

    def test_status_shape(self, engine: CopyTradingEngine) -> None:
        status = engine.status()
        assert "mode" in status and "masters" in status and "daily_dd_pct" in status
        assert status["mode"] == "DRY_RUN"

    def test_risk_check_handler_no_breach(self, engine: CopyTradingEngine, monkeypatch) -> None:
        monkeypatch.setattr("core.trading.copy_trading.CopyTradingEngine", lambda: engine)
        from core.trading.copy_trading import run_trading_risk_check

        result = run_trading_risk_check()
        assert result["status"] == "ok"


# ------------------------------------------------------------ trader scoring


class TestTraderScorer:
    def test_elite_trader(self) -> None:
        elite = TraderMetrics(
            trader_id="e1",
            total_trades=400,
            win_rate=68.0,
            profit_factor=2.2,
            sharpe=3.5,
            max_dd_pct=8.0,
            consistency=0.85,
            pnl_usd=90000,
            volume_usd=1000000,
            age_days=400,
        )
        score = TraderScorer().score(elite)
        assert score.tier == "ELITE"
        assert score.score >= 85

    def test_bad_trader_avoid(self) -> None:
        bad = TraderMetrics(
            trader_id="b1",
            total_trades=20,
            win_rate=40.0,
            profit_factor=0.9,
            sharpe=0.2,
            max_dd_pct=45.0,
            consistency=0.2,
            pnl_usd=-500,
            volume_usd=5000,
        )
        score = TraderScorer().score(bad)
        assert score.tier == "AVOID"
        assert score.score < 55

    def test_weights_sum_to_one(self) -> None:
        assert abs(sum(TraderScorer.WEIGHTS.values()) - 1.0) < 1e-9

    def test_reasoning_present(self) -> None:
        score = TraderScorer().score(_good_trader())
        assert len(score.reasoning) >= 2
        assert any("trades" in r for r in score.reasoning)


class TestBacktestValidator:
    def test_good_trader_approved(self) -> None:
        validation = BacktestValidator().validate(_good_trader())
        assert validation["approved"] is True
        assert validation["passed"] >= 5

    def test_martingale_rejected(self) -> None:
        martingale = TraderMetrics(
            trader_id="m1",
            total_trades=300,
            win_rate=98.0,
            profit_factor=1.05,
            sharpe=1.0,
            max_dd_pct=35.0,
            consistency=0.5,
            pnl_usd=1000,
            volume_usd=30000,
            age_days=400,
        )
        validation = BacktestValidator().validate(martingale)
        assert validation["checks"]["no_martingale"] is False

    def test_small_sample_rejected(self) -> None:
        small = TraderMetrics(
            trader_id="s1",
            total_trades=12,
            win_rate=60.0,
            profit_factor=1.9,
            sharpe=2.0,
            max_dd_pct=8.0,
            consistency=1.0,
            pnl_usd=100,
            volume_usd=10000,
            age_days=30,
        )
        validation = BacktestValidator().validate(small)
        assert validation["checks"]["sample_size"] is False
        assert validation["approved"] is False


class TestLiveTraderMonitor:
    def test_dd_breach_alerts(self) -> None:
        alerts = LiveTraderMonitor().check(_good_trader(), current_dd_pct=30.0)
        assert len(alerts) == 1
        assert "drawdown" in alerts[0]

    def test_rolling_win_rate_drop_alerts(self) -> None:
        alerts = LiveTraderMonitor().check(_good_trader(), rolling_win_rate=35.0)
        assert any("win rate" in a for a in alerts)

    def test_healthy_no_alerts(self) -> None:
        assert LiveTraderMonitor().check(_good_trader(), current_dd_pct=5.0, rolling_win_rate=60.0) == []

    def test_suspicious_high_win_rate(self) -> None:
        suspicious = TraderMetrics(
            trader_id="x1",
            total_trades=80,
            win_rate=97.0,
            profit_factor=1.1,
            sharpe=1.0,
            max_dd_pct=30.0,
            consistency=0.5,
            pnl_usd=100,
            volume_usd=10000,
        )
        alerts = LiveTraderMonitor().check(suspicious)
        assert any("sospechosamente" in a for a in alerts)


# ----------------------------------------------------------------- reasoning


class TestDecisionCorrelator:
    def _entries(self) -> list[dict]:
        return [
            {
                "app_id": "trading",
                "action": "trading:copy_executed",
                "outcome": "success",
                "reward": 150.0,
                "data_snapshot": {"strategy_id": "strat_a", "params": {"tp_pct": 3.0, "size_pct": 5.0}},
            },
            {
                "app_id": "trading",
                "action": "trading:copy_executed",
                "outcome": "success",
                "reward": 90.0,
                "data_snapshot": {"strategy_id": "strat_a", "params": {"tp_pct": 3.0, "size_pct": 5.0}},
            },
            {
                "app_id": "trading",
                "action": "trading:copy_executed",
                "outcome": "failure",
                "reward": 0.0,
                "data_snapshot": {"strategy_id": "strat_a", "params": {"tp_pct": 3.0, "size_pct": 5.0}},
            },
            {
                "app_id": "trading",
                "action": "trading:copy_executed",
                "outcome": "failure",
                "reward": 0.0,
                "data_snapshot": {"strategy_id": "strat_a", "params": {"tp_pct": 3.0, "size_pct": 5.0}},
            },
            {
                "app_id": "trading",
                "action": "trading:copy_executed",
                "outcome": "success",
                "reward": 200.0,
                "data_snapshot": {"strategy_id": "strat_a", "params": {"tp_pct": 3.0, "size_pct": 5.0}},
            },
        ]

    def test_dna_built_from_journal(self, store: TradingStore) -> None:
        correlator = DecisionCorrelator(store)
        dna_list = correlator.correlate(entries=self._entries())
        assert len(dna_list) == 1
        dna = dna_list[0]
        assert dna.strategy_id == "strat_a"
        assert dna.sample_size == 5
        assert dna.win_rate == 60.0
        assert dna.profit_factor >= 1.4
        assert dna.confidence >= 0.2

    def test_skips_small_samples(self, store: TradingStore) -> None:
        entries = self._entries()[:2]
        assert DecisionCorrelator(store).correlate(entries=entries) == []

    def test_skips_non_trading_entries(self, store: TradingStore) -> None:
        entries = [{"app_id": "atlas", "action": "rebalance", "outcome": "success", "data_snapshot": {}}]
        assert DecisionCorrelator(store).correlate(entries=entries) == []

    def test_parse_string_snapshot(self, store: TradingStore) -> None:
        entries = [
            {
                "app_id": "trading",
                "action": "trading:copy_executed",
                "outcome": "success",
                "reward": 10.0,
                "data_snapshot": '{"strategy_id": "strat_b", "params": {"size_pct": 5.0}}',
            }
        ] * 6
        dna_list = DecisionCorrelator(store).correlate(entries=entries)
        assert dna_list and dna_list[0].strategy_id == "strat_b"


class TestAutoParamOptimizer:
    def _dna(self, store: TradingStore, win_rate: float = 40.0, pf: float = 1.2) -> StrategyDNA:
        return StrategyDNA(
            strategy_id="strat_a",
            regime="unknown",
            winning_params={"tp_pct": 3.0, "size_pct": 5.0},
            losing_params={},
            confidence=0.8,
            sample_size=40,
            win_rate=win_rate,
            profit_factor=pf,
            max_dd_pct=15.0,
            sharpe=1.5,
            last_updated=store.now_iso(),
        )

    def test_low_win_rate_proposes_tp_tighten(self, store: TradingStore) -> None:
        proposals = AutoParamOptimizer(store).propose(self._dna(store, win_rate=40.0))
        assert any(p.param == "tp_pct" and p.proposed_value < p.current_value for p in proposals)

    def test_winning_dna_proposes_scale_up(self, store: TradingStore) -> None:
        proposals = AutoParamOptimizer(store).propose(self._dna(store, win_rate=65.0, pf=1.9))
        assert any(p.param == "size_pct" and p.proposed_value > p.current_value for p in proposals)

    def test_no_proposals_without_sample(self, store: TradingStore) -> None:
        dna = self._dna(store)
        dna.sample_size = 5
        assert AutoParamOptimizer(store).propose(dna) == []

    def test_approve_proposal(self, store: TradingStore) -> None:
        optimizer = AutoParamOptimizer(store)
        proposal = optimizer.propose(self._dna(store))[0]
        store.upsert_item("proposals", proposal.__dict__, id_key="proposal_id")
        result = optimizer.approve(proposal.proposal_id)
        assert result["success"] is True
        assert result["proposal"]["status"] == "approved"

    def test_approve_unknown_proposal(self, store: TradingStore) -> None:
        assert AutoParamOptimizer(store).approve("nope")["success"] is False

    def test_reject_proposal(self, store: TradingStore) -> None:
        optimizer = AutoParamOptimizer(store)
        proposal = optimizer.propose(self._dna(store))[0]
        store.upsert_item("proposals", proposal.__dict__, id_key="proposal_id")
        assert optimizer.reject(proposal.proposal_id)["success"] is True
        assert optimizer.reject(proposal.proposal_id)["success"] is False


# -------------------------------------------------------------- discovery


class TestTraderDiscovery:
    def test_degrades_to_empty_on_network_error(self, monkeypatch) -> None:
        class FailingCopier:
            def scan_top_traders(self):
                raise RuntimeError("network down")

        discovery = TraderDiscovery(copier=FailingCopier())
        import asyncio

        assert asyncio.run(discovery.discover(limit=5)) == []

    def test_maps_polymarket_candidates(self, monkeypatch) -> None:
        class FakeCopier:
            def scan_top_traders(self):
                return [
                    {
                        "trader_id": "0xabc",
                        "trader": "Whale",
                        "total_trades": 120,
                        "win_rate": 65.0,
                        "profit_factor": 1.7,
                        "pnl": 1000.0,
                        "volume": 20000.0,
                        "age_days": 200,
                    },
                ]

        discovery = TraderDiscovery(copier=FakeCopier())
        import asyncio

        scored = asyncio.run(discovery.discover_scored(limit=5))
        assert len(scored) == 1
        assert scored[0]["trader"]["trader_id"] == "0xabc"
        assert scored[0]["tier"] in ("ELITE", "STRONG", "GOOD", "AVOID")


# ------------------------------------------------------------------ router


def test_dashboard_summary_route(tmp_path, monkeypatch) -> None:
    import fastapi
    from fastapi.testclient import TestClient

    from api.routers import trading as trading_router

    store = TradingStore(data_dir=tmp_path / "trading")
    engine = CopyTradingEngine(
        store=store, config=TradingConfig(), executor=DryRunExecutor(TradingConfig()), log_decisions=False
    )
    trading_router._engine = engine  # noqa: SLF001

    app = fastapi.FastAPI()
    app.include_router(trading_router.router)
    client = TestClient(app)

    response = client.get("/api/trading/dashboard/summary")
    assert response.status_code == 200
    body = response.json()
    assert "copy" in body and "reasoning" in body
    assert body["copy"]["mode"] == "DRY_RUN"

    response = client.post(
        "/api/trading/copy/masters", json={"master_id": "api-m1", "name": "API Master", "copy_ratio": 0.05}
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.get("/api/trading/copy/masters")
    assert response.json()["count"] == 1

    response = client.post(
        "/api/trading/copy/ingest",
        json={"master_id": "api-m1", "pair": "ETH-USD", "side": "BUY", "quantity": 2.0, "price": 3000.0},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    response = client.delete("/api/trading/copy/masters/api-m1")
    assert response.status_code == 200

    response = client.post("/api/trading/copy/emergency-stop", json={"reason": "api test"})
    assert response.status_code == 200
    assert response.json()["result"]["reason"] == "api test"

    response = client.post(
        "/api/trading/intelligence/score",
        json={
            "trader_id": "t-api",
            "total_trades": 150,
            "win_rate": 60.0,
            "profit_factor": 1.6,
            "sharpe": 2.0,
            "max_dd_pct": 10.0,
            "consistency": 0.7,
            "pnl_usd": 1000.0,
            "volume_usd": 10000.0,
            "age_days": 200,
        },
    )
    assert response.status_code == 200
    assert response.json()["tier"] in ("ELITE", "STRONG", "GOOD", "AVOID")

    response = client.get("/api/trading/reasoning/dna")
    assert response.status_code == 200

    response = client.get("/api/trading/copy/status")
    assert response.status_code == 200
