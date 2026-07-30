"""Tests for ORION Core — platform-level infrastructure."""

from __future__ import annotations

import pytest

from core.app_registry import AppRegistry, get_app_registry
from core.database.manager import DatabaseManager, get_db_manager
from core.events import CoreEventBus, get_core_event_bus
from core.interfaces.scheduler import JobDefinition
from core.normalizer.base import (
    NormalizedBet,
    NormalizedMarket,
    NormalizedPortfolio,
    NormalizedPosition,
    NormalizedPrice,
    NormalizedTransaction,
)
from core.scheduler.scheduler import CoreScheduler, get_core_scheduler
from core.simulation.engine import SimulationEngine


class TestNormalizedTypes:
    """All normalized data types should construct without errors."""

    def test_normalized_position(self):
        p = NormalizedPosition(
            symbol="BTC",
            asset_type="crypto",
            quantity=1.0,
            avg_price=50000,
            current_price=55000,
            value=55000,
            pnl_percent=10.0,
        )
        assert p.symbol == "BTC"
        assert p.value == 55000

    def test_normalized_portfolio(self):
        pos = NormalizedPosition(
            symbol="ETH", asset_type="crypto", quantity=10, avg_price=2000, current_price=2500, value=25000
        )
        port = NormalizedPortfolio(total_value=25000, positions=[pos], cash=5000, provider="test")
        assert port.total_value == 25000
        assert port.cash == 5000

    def test_normalized_price(self):
        p = NormalizedPrice(
            symbol="AAPL", price=150.0, currency="USD", change_24h=2.5, volume_24h=1000000, source="yahoo"
        )
        assert p.price == 150.0

    def test_normalized_transaction(self):
        t = NormalizedTransaction(
            symbol="AAPL",
            tx_type="buy",
            quantity=10,
            price=150.0,
            total=1500.0,
            executed_at="2024-01-01",
            platform="test",
        )
        assert t.quantity == 10

    def test_normalized_market(self):
        m = NormalizedMarket(
            market_id="m1",
            title="Test Market",
            platform="polymarket",
            outcomes=[{"name": "Yes", "price": 0.5}],
            volume_24h=10000.0,
        )
        assert m.title == "Test Market"
        assert m.platform == "polymarket"

    def test_normalized_bet(self):
        b = NormalizedBet(
            bet_id="b1",
            event="Game",
            market="Winner",
            platform="test",
            odds=2.0,
            stake=100,
            payout=200,
            outcome="win",
            placed_at="2024-01-01",
        )
        assert b.stake == 100


class TestAppRegistry:
    def test_registry_singleton(self):
        r1 = get_app_registry()
        r2 = get_app_registry()
        assert r1 is r2

    def test_registry_empty_initial(self):
        r = AppRegistry()
        apps = r.list_apps()
        assert isinstance(apps, list)


class TestDatabaseManager:
    def test_db_manager_singleton(self):
        m1 = get_db_manager()
        m2 = get_db_manager()
        assert m1 is m2

    def test_register_and_access(self):
        m = DatabaseManager()
        m.register("test_mem", ":memory:")
        engine = m.get_engine("test_mem")
        assert engine is not None
        session = m.get_session("test_mem")
        assert session is not None
        session.close()
        m.dispose("test_mem")

    def test_unknown_app_raises(self):
        m = DatabaseManager()
        with pytest.raises(KeyError):
            m.get_engine("nonexistent")


class TestCoreScheduler:
    def test_scheduler_singleton(self):
        s1 = get_core_scheduler()
        s2 = get_core_scheduler()
        assert s1 is s2

    def test_add_and_remove_job(self):
        s = CoreScheduler()
        job = JobDefinition(job_id="test_job", app_id="test", handler=lambda: None, seconds=60)
        job_id = s.add_job(job)
        assert s.get_jobs("test")[0].job_id == job_id
        s.remove_job(job_id)
        assert len(s.get_jobs("test")) == 0


class TestCoreEventBus:
    def test_event_bus_singleton(self):
        b1 = get_core_event_bus()
        b2 = get_core_event_bus()
        assert b1 is b2

    def test_publish_subscribe(self):
        bus = CoreEventBus()
        received = []

        def handler(**data):
            received.append(data)

        bus.subscribe("test:event", handler)
        bus.publish("test:event", key="value")
        assert len(received) == 1
        assert received[0]["key"] == "value"
        assert received[0]["event"] == "test:event"


@pytest.mark.asyncio
class TestSimulationEngine:
    async def test_monte_carlo(self):
        engine = SimulationEngine()
        result = await engine.run_monte_carlo(
            app_id="test",
            initial_value=10000,
            scenarios=[
                {"probability": 0.5, "return_pct": 0.001, "label": "up"},
                {"probability": 0.5, "return_pct": -0.001, "label": "down"},
            ],
            n_simulations=100,
            horizon_days=30,
        )
        assert result.initial_value == 10000
        assert result.metrics["simulations"] == 100
        assert "median" in result.metrics
        assert "ruin_probability" in result.metrics

    async def test_what_if(self):
        engine = SimulationEngine()
        result = await engine.run_what_if(
            app_id="test",
            title="Rebalance test",
            current_value=10000,
            proposed_changes=[
                {"field": "cash", "old_value": 5000, "new_value": 2000},
            ],
        )
        assert result.final_value == 7000
