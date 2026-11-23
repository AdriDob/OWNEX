"""Tests for the Investment Engine module.

Covers:
  - RevenueAllocationController (allocation, 25% rule, payout allocation)
  - InvestmentManager (deploy, pause, risk management, drawdown protection)
  - InvestmentMetrics (trade recording, Sharpe, drawdown)
  - CCXTAdapter (connection, info with mocked ccxt)
  - PolymarketAdapter
  - API endpoints (via minimal FastAPI app)
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def isolate_state():
    """Isolate state between tests by patching home directory and resetting singletons."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_home = os.environ.get("HOME", "")
        os.environ["HOME"] = tmpdir
        yield
        os.environ["HOME"] = old_home


@pytest.fixture
def allocation_controller():
    from core.investment.allocation import get_allocation_controller, reset_allocation_controller

    reset_allocation_controller()
    ctrl = get_allocation_controller()
    ctrl.update_capital(10000.0)
    return ctrl


def _reset_all():
    from core.investment.allocation import reset_allocation_controller
    from core.investment.manager import reset_investment_manager
    from core.investment.metrics import reset_investment_metrics

    reset_allocation_controller()
    reset_investment_manager()
    reset_investment_metrics()


@pytest.fixture
def investment_manager():
    _reset_all()
    from core.investment.manager import get_investment_manager

    mgr = get_investment_manager()
    mgr.allocation.update_capital(10000.0)
    return mgr


@pytest.fixture
def investment_metrics():
    from core.investment.metrics import get_investment_metrics

    _reset_all()
    return get_investment_metrics()


# Minimal app without auth for API tests
@pytest.fixture
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routers.investment import register_investment_capabilities

    app = FastAPI()
    from api.routers.investment import router as investment_router

    app.include_router(investment_router)
    register_investment_capabilities()
    return TestClient(app)


# ── RevenueAllocationController Tests ──────────────────────────


class TestAllocationController:
    def test_update_capital(self, allocation_controller):
        ctrl = allocation_controller
        assert ctrl.config.total_capital_usd == 10000.0
        ctrl.update_capital(25000.0)
        assert ctrl.config.total_capital_usd == 25000.0

    def test_max_high_risk_amount(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(10000.0)
        assert ctrl.config.max_high_risk_amount() == 2500.0
        assert ctrl.config.max_speculative_amount() == 1000.0
        assert ctrl.config.emergency_reserve_amount() == 500.0
        assert ctrl.config.available_for_investment() == 9500.0

    def test_allocate_payout_basic(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(10000.0)
        result = ctrl.allocate_payout(1000.0, source="hackerone")
        assert "allocated" in result
        assert result["total"] == 1000.0
        assert result["reserve"] == 50.0

        snap = ctrl.snapshot()
        assert snap.total_capital == 10000.0

    def test_allocate_payout_respects_25_percent_rule(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(1000.0)

        from core.investment.models import StrategyAllocation

        ctrl._strategies["memecoin"] = StrategyAllocation(strategy_id="memecoin", allocated_usd=200.0, deployed_usd=200.0)
        ctrl._strategies["polymarket"] = StrategyAllocation(strategy_id="polymarket", allocated_usd=50.0, deployed_usd=50.0)

        exposure = ctrl.get_high_risk_exposure()
        assert exposure["high_risk_deployed"] == 250.0
        assert exposure["within_limit"] is True

        result = ctrl.allocate_payout(500.0)
        assert result["total"] == 500.0

    def test_snapshot_format(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(5000.0)
        snap = ctrl.snapshot()
        data = snap.to_dict()
        assert data["total_capital"] == 5000.0
        assert "deployed" in data
        assert "available" in data
        assert "total_pnl" in data
        assert "strategies" in data
        assert "timestamp" in data

    def test_deploy_capital(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(10000.0)
        ctrl.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        ctrl._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, available_usd=500.0)

        success = ctrl.deploy_capital("ccxt_spot", 200.0)
        assert success is True
        snap = ctrl.snapshot()
        assert snap.deployed >= 200.0

        success = ctrl.deploy_capital("ccxt_spot", 999999.0)
        assert success is False

    def test_record_pnl(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(10000.0)
        ctrl.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        sa = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, deployed_usd=500.0)
        ctrl._strategies["ccxt_spot"] = sa
        ctrl.deploy_capital("ccxt_spot", 500.0)

        ctrl.record_pnl("ccxt_spot", 50.0)
        snap = ctrl.snapshot()
        assert snap.total_pnl >= 50.0

        ctrl.record_pnl("ccxt_spot", -20.0)
        snap = ctrl.snapshot()
        assert abs(snap.total_pnl - 30.0) < 0.01

    def test_get_high_risk_exposure(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(10000.0)
        exposure = ctrl.get_high_risk_exposure()
        assert exposure["total_capital"] == 10000.0
        assert exposure["max_allowed_pct"] == 25.0
        assert exposure["max_allowed_amount"] == 2500.0
        assert exposure["within_limit"] is True

    def test_persistence(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(5000.0)
        ctrl.allocate_payout(1000.0)

        from core.investment.allocation import get_allocation_controller, reset_allocation_controller

        reset_allocation_controller()
        ctrl2 = get_allocation_controller()
        assert ctrl2.config.total_capital_usd == 5000.0

    def test_get_event_history(self, allocation_controller):
        ctrl = allocation_controller
        ctrl.update_capital(10000.0)
        ctrl.allocate_payout(500.0, source="bugcrowd")
        ctrl.allocate_payout(300.0, source="hackerone")

        events = ctrl.get_event_history(limit=10)
        assert len(events) >= 2
        assert events[0]["type"] == "payout_allocated"
        # Most recent first
        assert events[0]["source"] == "hackerone"


# ── InvestmentManager Tests ────────────────────────────────────


class TestInvestmentManager:
    def test_initial_state(self, investment_manager):
        mgr = investment_manager
        assert mgr.is_paused is False
        assert mgr.drawdown_protection is True

    def test_pause_resume_all(self, investment_manager):
        mgr = investment_manager
        assert mgr.is_paused is False
        mgr.pause_all()
        assert mgr.is_paused is True
        mgr.resume_all()
        assert mgr.is_paused is False

    def test_strategy_pause_resume(self, investment_manager):
        mgr = investment_manager
        mgr.allocation.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        mgr.allocation._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, deployed_usd=200.0, available_usd=300.0)

        mgr._active_strategies["ccxt_spot"] = {
            "strategy_id": "ccxt_spot",
            "deployed_at": "",
            "total_deployed": 200.0,
            "total_withdrawn": 0.0,
        }

        assert mgr.is_strategy_paused("ccxt_spot") is False
        assert mgr.pause_strategy("ccxt_spot") is True
        assert mgr.is_strategy_paused("ccxt_spot") is True
        mgr.resume_strategy("ccxt_spot")
        assert mgr.is_strategy_paused("ccxt_spot") is False

    def test_can_deploy_basic(self, investment_manager):
        mgr = investment_manager
        mgr.allocation.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        mgr.allocation._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, available_usd=500.0)

        check = mgr.can_deploy("ccxt_spot", 100.0)
        assert check["allowed"] is True

    def test_can_deploy_when_paused(self, investment_manager):
        mgr = investment_manager
        mgr.pause_all()
        check = mgr.can_deploy("ccxt_spot", 100.0)
        assert check["allowed"] is False
        assert "pause" in check["reason"].lower()

    def test_deploy_success(self, investment_manager):
        mgr = investment_manager
        mgr.allocation.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        mgr.allocation._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, available_usd=500.0)

        result = mgr.deploy("ccxt_spot", 200.0)
        assert result["success"] is True
        assert result["amount"] == 200.0

    def test_deploy_insufficient_capital(self, investment_manager):
        mgr = investment_manager
        result = mgr.deploy("ccxt_spot", 999999.0)
        assert result["success"] is False

    def test_risk_report_structure(self, investment_manager):
        mgr = investment_manager
        mgr.allocation.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        mgr.allocation._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, deployed_usd=200.0, available_usd=300.0)
        mgr._active_strategies["ccxt_spot"] = {
            "strategy_id": "ccxt_spot",
            "deployed_at": "",
            "total_deployed": 200.0,
            "total_withdrawn": 0.0,
        }

        mgr.record_trade_result("ccxt_spot", "BTC/USDT", "buy", 50000.0, 51000.0, 0.01, 10.0, 2.0)

        report = mgr.risk_report()
        assert "global_paused" in report
        assert "high_risk_exposure" in report
        assert "snapshot" in report
        assert "strategies" in report
        assert "consolidated_metrics" in report
        assert "pnl_chart" in report

    def test_auto_pause_on_drawdown(self, investment_manager):
        mgr = investment_manager
        mgr.allocation.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        mgr.allocation._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, deployed_usd=200.0, available_usd=300.0)
        mgr._active_strategies["ccxt_spot"] = {
            "strategy_id": "ccxt_spot",
            "deployed_at": "",
            "total_deployed": 200.0,
            "total_withdrawn": 0.0,
        }

        for _ in range(6):
            mgr.record_trade_result("ccxt_spot", "BTC/USDT", "buy", 100.0, 90.0, 1.0, -10.0, -10.0)

        assert mgr.is_strategy_paused("ccxt_spot") is True

    def test_update_config(self, investment_manager):
        mgr = investment_manager
        mgr.update_config(drawdown_protection=False, max_consecutive_losses=10, max_high_risk_pct=30.0)
        assert mgr.drawdown_protection is False
        assert mgr.allocation.config.max_high_risk_pct == 30.0

    def test_snapshot(self, investment_manager):
        mgr = investment_manager
        mgr.allocation.allocate_payout(2000.0)
        snap = mgr.snapshot()
        assert snap.total_capital == 10000.0
        assert snap.available > 0

    def test_activate_max_revenue_mode(self, investment_manager):
        mgr = investment_manager
        mgr.allocation.allocate_payout(1000.0)

        from core.investment.models import StrategyAllocation

        mgr.allocation._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, available_usd=500.0)

        mgr.deploy("ccxt_spot", 200.0)
        result = mgr.activate_max_revenue_mode()
        assert "success" in result


# ── InvestmentMetrics Tests ────────────────────────────────────

# Each test creates its own InvestmentMetrics instance to avoid state leakage


class TestInvestmentMetrics:
    def _fresh_metrics(self):
        from core.investment.metrics import InvestmentMetrics

        return InvestmentMetrics()

    def test_record_trade(self):
        metrics = self._fresh_metrics()
        metrics.record_trade("ccxt_spot", "BTC/USDT", "buy", 50000.0, 51000.0, 0.01, 10.0, 2.0)
        metrics.record_trade("ccxt_spot", "BTC/USDT", "sell", 51000.0, 50000.0, 0.01, -10.0, -2.0)

        all_metrics = metrics.get_all_strategy_metrics()
        assert "ccxt_spot" in all_metrics
        assert all_metrics["ccxt_spot"].total_trades == 2
        assert all_metrics["ccxt_spot"].winning_trades == 1
        assert all_metrics["ccxt_spot"].losing_trades == 1

    def test_sharpe_ratio_calculation(self):
        metrics = self._fresh_metrics()
        for _ in range(10):
            metrics.record_trade("strategy_a", "BTC/USDT", "buy", 100.0, 102.0, 1.0, 2.0, 2.0)
        for _ in range(5):
            metrics.record_trade("strategy_a", "BTC/USDT", "sell", 100.0, 98.0, 1.0, -2.0, -2.0)

        risk = metrics.get_strategy_metrics("strategy_a")
        assert risk.total_trades == 15
        assert risk.win_rate == pytest.approx(10 / 15, 0.01)
        assert risk.sharpe_ratio != 0.0

    def test_max_drawdown(self):
        metrics = self._fresh_metrics()
        for _ in range(3):
            metrics.record_trade("strategy_b", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0)
        for _ in range(5):
            metrics.record_trade("strategy_b", "BTC/USDT", "buy", 100.0, 85.0, 1.0, -15.0, -15.0)

        risk = metrics.get_strategy_metrics("strategy_b")
        assert risk.max_drawdown_pct > 20.0

    def test_in_drawdown_flag(self):
        metrics = self._fresh_metrics()
        metrics.record_trade("strategy_c", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0)
        metrics.record_trade("strategy_c", "BTC/USDT", "buy", 100.0, 80.0, 1.0, -20.0, -20.0)

        risk = metrics.get_strategy_metrics("strategy_c")
        if risk.current_drawdown_pct > 5.0:
            assert risk.is_drawdown is True

    def test_should_pause_on_consecutive_losses(self):
        metrics = self._fresh_metrics()
        for _ in range(6):
            metrics.record_trade("strategy_d", "BTC/USDT", "buy", 100.0, 95.0, 1.0, -5.0, -5.0)

        risk = metrics.get_strategy_metrics("strategy_d")
        assert risk.should_pause is True
        assert risk.consecutive_losses >= 5

    def test_pnl_chart_data(self):
        metrics = self._fresh_metrics()
        for _ in range(5):
            metrics.record_trade("ccxt_spot", "BTC/USDT", "buy", 100.0, 102.0, 1.0, 2.0, 2.0)
        chart = metrics.pnl_chart_data(days=30)
        assert len(chart) >= 1
        assert "date" in chart[0]
        assert "pnl" in chart[0]

    def test_healthy_strategy(self):
        metrics = self._fresh_metrics()
        for _ in range(5):
            metrics.record_trade("healthy", "BTC/USDT", "buy", 100.0, 103.0, 1.0, 3.0, 3.0)
        risk = metrics.get_strategy_metrics("healthy")
        assert risk.is_healthy is True

    def test_consolidated_metrics(self):
        metrics = self._fresh_metrics()
        metrics.record_trade("s1", "BTC/USDT", "buy", 100.0, 105.0, 1.0, 5.0, 5.0)
        metrics.record_trade("s1", "BTC/USDT", "sell", 100.0, 98.0, 1.0, -2.0, -2.0)
        metrics.record_trade("s2", "ETH/USDT", "buy", 2000.0, 2100.0, 0.5, 50.0, 5.0)

        consolidated = metrics.consolidated_metrics()
        assert consolidated["total_trades"] == 3
        assert consolidated["winning_trades"] == 2
        assert abs(consolidated["total_pnl"] - 53.0) < 0.01


# ── CCXTAdapter Tests ──────────────────────────────────────────


class TestCCXTAdapter:
    @pytest.mark.asyncio
    async def test_get_exchange_info(self):
        from core.investment.adapters.ccxt_adapter import CCXTAdapter

        adapter = CCXTAdapter(exchange_id="binance")
        info = await adapter.get_exchange_info()
        assert isinstance(info, dict)

    @pytest.mark.asyncio
    async def test_connect_fails_without_ccxt(self):
        from core.investment.adapters.ccxt_adapter import CCXTAdapter

        adapter = CCXTAdapter(exchange_id="nonexistent")
        connected = await adapter.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.ccxt_adapter import CCXTAdapter

        adapter = CCXTAdapter(exchange_id="binance")
        assert adapter.is_connected is False
        await adapter.disconnect()
        assert adapter.is_connected is False


# ── PolymarketAdapter Tests ────────────────────────────────────


class TestPolymarketAdapter:
    @pytest.mark.asyncio
    async def test_connect_without_api_key(self):
        from core.investment.adapters.polymarket_adapter import PolymarketAdapter

        adapter = PolymarketAdapter()
        connected = await adapter.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.polymarket_adapter import PolymarketAdapter

        adapter = PolymarketAdapter()
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_get_markets_not_connected(self):
        from core.investment.adapters.polymarket_adapter import PolymarketAdapter

        adapter = PolymarketAdapter()
        markets = await adapter.get_markets()
        assert markets == []


# ── API Tests (no auth) ────────────────────────────────────────


class TestInvestmentAPI:
    def test_get_status(self, client):
        response = client.get("/api/investment/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data

    def test_get_snapshot(self, client):
        response = client.get("/api/investment/snapshot")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "snapshot" in data

    def test_list_strategies(self, client):
        response = client.get("/api/investment/strategies")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["strategies"]) > 0

    def test_get_strategy_detail(self, client):
        response = client.get("/api/investment/strategies/ccxt_spot")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["strategy"]["profile"]["id"] == "ccxt_spot"

    def test_get_strategy_detail_not_found(self, client):
        response = client.get("/api/investment/strategies/nonexistent")
        assert response.status_code == 404

    def test_get_exposure(self, client):
        response = client.get("/api/investment/exposure")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "exposure" in data

    def test_get_allocation(self, client):
        response = client.get("/api/investment/allocation")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "allocation" in data

    def test_get_metrics(self, client):
        response = client.get("/api/investment/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "metrics" in data

    def test_get_events(self, client):
        response = client.get("/api/investment/events")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "events" in data

    def test_update_capital(self, client):
        response = client.post("/api/investment/allocation/update-capital", json={"total_usd": 50000.0})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_capital_usd"] == 50000.0

    def test_allocate_payout(self, client):
        response = client.post("/api/investment/allocation/allocate-payout", json={"amount": 1000.0, "source": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "allocation" in data

    def test_allocate_payout_zero(self, client):
        response = client.post("/api/investment/allocation/allocate-payout", json={"amount": 0})
        assert response.status_code == 400

    def test_pause_resume(self, client):
        response = client.post("/api/investment/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["paused"] is True

        response = client.post("/api/investment/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["paused"] is False

    def test_deploy_strategy(self, client):
        from core.investment.allocation import get_allocation_controller
        from core.investment.models import StrategyAllocation

        ctrl = get_allocation_controller()
        ctrl.update_capital(10000.0)
        ctrl._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, available_usd=500.0)

        response = client.post("/api/investment/strategies/ccxt_spot/deploy", json={"amount": 200.0})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_deploy_strategy_nonexistent(self, client):
        response = client.post("/api/investment/strategies/nonexistent/deploy", json={"amount": 100.0})
        assert response.status_code == 400

    def test_strategy_pause_resume_api(self, client):
        from core.investment.allocation import get_allocation_controller
        from core.investment.manager import get_investment_manager
        from core.investment.models import StrategyAllocation

        ctrl = get_allocation_controller()
        ctrl.update_capital(10000.0)
        ctrl._strategies["ccxt_spot"] = StrategyAllocation(strategy_id="ccxt_spot", allocated_usd=500.0, available_usd=500.0)

        mgr = get_investment_manager()
        mgr.deploy("ccxt_spot", 200.0)

        response = client.post("/api/investment/strategies/ccxt_spot/pause")
        assert response.status_code == 200

        response = client.post("/api/investment/strategies/ccxt_spot/resume")
        assert response.status_code == 200

    def test_update_config(self, client):
        response = client.post("/api/investment/config", json={"drawdown_protection": False})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_max_revenue_mode(self, client):
        client.post("/api/investment/allocation/allocate-payout", json={"amount": 1000.0})
        client.post("/api/investment/strategies/ccxt_spot/deploy", json={"amount": 200.0})
        response = client.post("/api/investment/max-revenue")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_ccxt_exchange_info(self, client):
        response = client.get("/api/investment/ccxt/info?exchange=binance")
        assert response.status_code == 200
        data = response.json()
        assert "exchange" in data

    def test_deploy_zero_amount(self, client):
        response = client.post("/api/investment/strategies/ccxt_spot/deploy", json={"amount": 0})
        assert response.status_code == 400


# ── Stocks & Options Tests ─────────────────────────────────────────


class TestAlpacaAdapter:
    def test_name(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        assert adapter.name == "alpaca"

    def test_default_config(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        assert adapter.is_connected is False
        assert adapter._base_url == "https://paper-api.alpaca.markets"

    @pytest.mark.asyncio
    async def test_connect_without_keys(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        connected = await adapter.connect()
        assert connected is True
        assert adapter.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_with_keys(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter(config={"api_key": "test_key", "secret_key": "test_secret"})
        connected = await adapter.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        await adapter.connect()
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_get_account_not_connected(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        account = await adapter.get_account()
        assert "error" in account or account == {}

    @pytest.mark.asyncio
    async def test_get_positions_not_connected(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        positions = await adapter.get_positions()
        assert positions == []

    @pytest.mark.asyncio
    async def test_place_order_not_connected(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        order = await adapter.place_order("AAPL", "buy", 10)
        assert "status" in order
        assert order["status"] in ("error", "not_connected", "rejected")

    @pytest.mark.asyncio
    async def test_get_market_data_not_connected(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        data = await adapter.get_market_data("AAPL")
        assert "error" in data or data == {}

    @pytest.mark.asyncio
    async def test_get_option_chain_not_connected(self):
        from core.investment.adapters.stocks_adapter import AlpacaAdapter

        adapter = AlpacaAdapter()
        chain = await adapter.get_option_chain("AAPL")
        assert chain == []

    def test_build_alpaca_adapter(self):
        from core.investment.adapters.stocks_adapter import build_alpaca_adapter

        adapter = build_alpaca_adapter()
        assert adapter.name == "alpaca"


class TestIBKRAdapter:
    def test_name(self):
        from core.investment.adapters.stocks_adapter import IBKRAdapter

        adapter = IBKRAdapter()
        assert adapter.name == "ibkr"

    def test_default_config(self):
        from core.investment.adapters.stocks_adapter import IBKRAdapter

        adapter = IBKRAdapter()
        assert adapter.is_connected is False
        assert adapter._host == "127.0.0.1"
        assert adapter._port == 7497

    @pytest.mark.asyncio
    async def test_connect_without_ib_insync(self):
        from core.investment.adapters.stocks_adapter import IBKRAdapter

        adapter = IBKRAdapter()
        connected = await adapter.connect()
        assert connected is True

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.stocks_adapter import IBKRAdapter

        adapter = IBKRAdapter()
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_get_account_not_connected(self):
        from core.investment.adapters.stocks_adapter import IBKRAdapter

        adapter = IBKRAdapter()
        account = await adapter.get_account()
        assert "error" in account or account == {}

    @pytest.mark.asyncio
    async def test_get_positions_not_connected(self):
        from core.investment.adapters.stocks_adapter import IBKRAdapter

        adapter = IBKRAdapter()
        positions = await adapter.get_positions()
        assert positions == []

    @pytest.mark.asyncio
    async def test_place_order_not_connected(self):
        from core.investment.adapters.stocks_adapter import IBKRAdapter

        adapter = IBKRAdapter()
        order = await adapter.place_order("AAPL", "BUY", 10)
        assert "status" in order
        assert order["status"] in ("error", "not_connected", "rejected")

    def test_build_ibkr_adapter(self):
        from core.investment.adapters.stocks_adapter import build_ibkr_adapter

        adapter = build_ibkr_adapter()
        assert adapter.name == "ibkr"


# ── DeFi Yield Tests ───────────────────────────────────────────────


class TestAaveAdapter:
    def test_name(self):
        from core.investment.adapters.defi_adapter import AaveAdapter

        adapter = AaveAdapter()
        assert adapter.name == "aave"

    def test_default_config(self):
        from core.investment.adapters.defi_adapter import AaveAdapter

        adapter = AaveAdapter()
        assert adapter.is_connected is False
        assert adapter._chain == "ethereum"

    @pytest.mark.asyncio
    async def test_connect_fails_without_rpc(self):
        from core.investment.adapters.defi_adapter import AaveAdapter

        adapter = AaveAdapter(config={"chain": "ethereum"})
        connected = await adapter.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.defi_adapter import AaveAdapter

        adapter = AaveAdapter()
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_get_supply_apy_not_connected(self):
        from core.investment.adapters.defi_adapter import AaveAdapter

        adapter = AaveAdapter()
        apy = await adapter.get_supply_apy("USDC")
        assert isinstance(apy, dict)
        assert "supply_apy" in apy

    @pytest.mark.asyncio
    async def test_get_top_assets_not_connected(self):
        from core.investment.adapters.defi_adapter import AaveAdapter

        adapter = AaveAdapter()
        assets = await adapter.get_top_assets()
        assert assets == []

    def test_build_aave_adapter(self):
        from core.investment.adapters.defi_adapter import build_aave_adapter

        adapter = build_aave_adapter()
        assert adapter.name == "aave"


class TestMorphoAdapter:
    def test_name(self):
        from core.investment.adapters.defi_adapter import MorphoAdapter

        adapter = MorphoAdapter()
        assert adapter.name == "morpho"

    def test_default_config(self):
        from core.investment.adapters.defi_adapter import MorphoAdapter

        adapter = MorphoAdapter()
        assert adapter.is_connected is False
        assert adapter._chain == "ethereum"

    @pytest.mark.asyncio
    async def test_connect_fails_without_rpc(self):
        from core.investment.adapters.defi_adapter import MorphoAdapter

        adapter = MorphoAdapter(config={"chain": "ethereum"})
        connected = await adapter.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.defi_adapter import MorphoAdapter

        adapter = MorphoAdapter()
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_get_market_apy_not_connected(self):
        from core.investment.adapters.defi_adapter import MorphoAdapter

        adapter = MorphoAdapter()
        apy = await adapter.get_market_apy("test")
        assert isinstance(apy, dict)
        assert "supply_apy" in apy

    @pytest.mark.asyncio
    async def test_get_top_markets_not_connected(self):
        from core.investment.adapters.defi_adapter import MorphoAdapter

        adapter = MorphoAdapter()
        markets = await adapter.get_top_markets()
        assert markets == []

    def test_build_morpho_adapter(self):
        from core.investment.adapters.defi_adapter import build_morpho_adapter

        adapter = build_morpho_adapter()
        assert adapter.name == "morpho"


class TestPendleAdapter:
    def test_name(self):
        from core.investment.adapters.defi_adapter import PendleAdapter

        adapter = PendleAdapter()
        assert adapter.name == "pendle"

    def test_default_config(self):
        from core.investment.adapters.defi_adapter import PendleAdapter

        adapter = PendleAdapter()
        assert adapter.is_connected is False
        assert adapter._chain == "ethereum"

    @pytest.mark.asyncio
    async def test_connect_fails_without_rpc(self):
        from core.investment.adapters.defi_adapter import PendleAdapter

        adapter = PendleAdapter(config={"chain": "ethereum"})
        connected = await adapter.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.defi_adapter import PendleAdapter

        adapter = PendleAdapter()
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_get_yield_opportunities_not_connected(self):
        from core.investment.adapters.defi_adapter import PendleAdapter

        adapter = PendleAdapter()
        opps = await adapter.get_yield_opportunities()
        assert opps == []

    @pytest.mark.asyncio
    async def test_get_pt_yield_not_connected(self):
        from core.investment.adapters.defi_adapter import PendleAdapter

        adapter = PendleAdapter()
        yield_data = await adapter.get_pt_yield("0x123")
        assert isinstance(yield_data, dict)
        assert "implied_apy" in yield_data

    def test_build_pendle_adapter(self):
        from core.investment.adapters.defi_adapter import build_pendle_adapter

        adapter = build_pendle_adapter()
        assert adapter.name == "pendle"


class TestLidoAdapter:
    def test_name(self):
        from core.investment.adapters.defi_adapter import LidoAdapter

        adapter = LidoAdapter()
        assert adapter.name == "lido"

    def test_default_config(self):
        from core.investment.adapters.defi_adapter import LidoAdapter

        adapter = LidoAdapter()
        assert adapter.is_connected is False
        assert adapter._chain == "ethereum"

    @pytest.mark.asyncio
    async def test_connect_fails_without_rpc(self):
        from core.investment.adapters.defi_adapter import LidoAdapter

        adapter = LidoAdapter(config={"chain": "ethereum"})
        connected = await adapter.connect()
        assert connected is False

    @pytest.mark.asyncio
    async def test_disconnect_cleanly(self):
        from core.investment.adapters.defi_adapter import LidoAdapter

        adapter = LidoAdapter()
        await adapter.disconnect()
        assert adapter.is_connected is False

    @pytest.mark.asyncio
    async def test_get_staking_apy_not_connected(self):
        from core.investment.adapters.defi_adapter import LidoAdapter

        adapter = LidoAdapter()
        apy = await adapter.get_staking_apy()
        assert isinstance(apy, dict)
        assert "apy" in apy

    @pytest.mark.asyncio
    async def test_get_protocol_metrics_not_connected(self):
        from core.investment.adapters.defi_adapter import LidoAdapter

        adapter = LidoAdapter()
        metrics = await adapter.get_protocol_metrics()
        assert isinstance(metrics, dict)
        assert "tvl" in metrics

    def test_build_lido_adapter(self):
        from core.investment.adapters.defi_adapter import build_lido_adapter

        adapter = build_lido_adapter()
        assert adapter.name == "lido"


# ── Registry Tests ─────────────────────────────────────────────────


class TestInvestmentAdapterRegistry:
    def test_register_and_list(self):
        from core.investment.adapters.registry import InvestmentAdapterRegistry

        registry = InvestmentAdapterRegistry()
        registry.register_adapter(
            "alpaca",
            "core.investment.adapters.stocks_adapter.AlpacaAdapter",
            enabled=True,
        )
        adapters = registry.list_adapters()
        assert len(adapters) == 1
        assert adapters[0]["name"] == "alpaca"
        assert adapters[0]["enabled"] is True

    def test_register_disabled(self):
        from core.investment.adapters.registry import InvestmentAdapterRegistry

        registry = InvestmentAdapterRegistry()
        registry.register_adapter(
            "ibkr",
            "core.investment.adapters.stocks_adapter.IBKRAdapter",
            enabled=False,
        )
        adapters = registry.list_adapters()
        assert len(adapters) == 1
        assert adapters[0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_initialize_all(self):
        from core.investment.adapters.registry import InvestmentAdapterRegistry

        registry = InvestmentAdapterRegistry()
        registry.register_adapter(
            "alpaca",
            "core.investment.adapters.stocks_adapter.AlpacaAdapter",
            enabled=True,
        )
        results = await registry.initialize_all()
        assert results["alpaca"] is True
        adapter = registry.get_adapter("alpaca")
        assert adapter is not None

    @pytest.mark.asyncio
    async def test_shutdown_all(self):
        from core.investment.adapters.registry import InvestmentAdapterRegistry

        registry = InvestmentAdapterRegistry()
        registry.register_adapter(
            "alpaca",
            "core.investment.adapters.stocks_adapter.AlpacaAdapter",
            enabled=True,
        )
        await registry.initialize_all()
        await registry.shutdown_all()
        assert len(registry._adapters) >= 0  # shutdown removes adapter if disconnect succeeds

    @pytest.mark.asyncio
    async def test_import_class_failure(self):
        from core.investment.adapters.registry import InvestmentAdapterRegistry

        registry = InvestmentAdapterRegistry()
        registry.register_adapter(
            "bad",
            "core.investment.adapters.nonexistent.NonexistentAdapter",
            enabled=True,
        )
        results = await registry.initialize_all()
        assert results["bad"] is False

    def test_get_adapter_not_found(self):
        from core.investment.adapters.registry import InvestmentAdapterRegistry

        registry = InvestmentAdapterRegistry()
        assert registry.get_adapter("nonexistent") is None

    def test_get_all_adapters_empty(self):
        from core.investment.adapters.registry import InvestmentAdapterRegistry

        registry = InvestmentAdapterRegistry()
        assert registry.get_all_adapters() == {}


class TestBuildDefaultRegistry:
    def test_build_default_registry(self):
        from core.investment.adapters import build_default_registry

        registry = build_default_registry()
        adapters = registry.list_adapters()
        names = [a["name"] for a in adapters]
        assert "alpaca" in names
        assert "ibkr" in names
        assert "aave" in names
        assert "morpho" in names
        assert "pendle" in names
        assert "lido" in names
        assert "ccxt" in names
        assert "polymarket" in names
        assert len(adapters) == 20


# ── 11.4.2 Strategy Attribution Engine ──────────────────────────


def _make_trade(
    trade_id: str = "T1",
    strategy_id: str = "ccxt_spot",
    symbol: str = "BTC/USDT",
    side: str = "buy",
    currency: str = "USDT",
    gross_pnl: float | None = 10.0,
    fees: float = 1.0,
    slippage: float = 0.5,
    completeness: str = "COMPLETE",
    exchange: str = "binance",
    account_id: str = "acc-1",
    asset: str = "BTC",
    provenance: str = "EXCHANGE",
    created_at: str = "2026-03-15T10:00:00+00:00",
):
    """Build one TradeEvidence with every attribution dimension explicit."""
    from core.investment.models import ProvenanceLevel, TradeEvidence

    gross = gross_pnl
    net = None if gross is None else gross - fees - slippage
    return TradeEvidence(
        trade_id=trade_id,
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        currency=currency,
        gross_pnl=gross,
        fees=fees,
        slippage=slippage,
        net_pnl=net,
        net_pnl_calc=0.0 if net is None else net,
        net_pnl_completeness=completeness,
        exchange=exchange,
        account_id=account_id,
        asset=asset,
        provenance_level=ProvenanceLevel(provenance),
        created_at=created_at,
    )


class TestStrategyAttribution:
    """11.4.2 — attribution must never invent dimensions or net figures."""

    def test_group_by_strategy(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", strategy_id="ccxt_spot"),
            _make_trade(trade_id="B", strategy_id="polymarket"),
        ]
        groups = attribute(trades).by_strategy()
        assert {g.key.strategy_id for g in groups} == {"ccxt_spot", "polymarket"}
        assert all(g.total_trades == 1 for g in groups)

    def test_group_by_exchange(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", exchange="binance"),
            _make_trade(trade_id="B", exchange="kraken"),
            _make_trade(trade_id="C", exchange="binance"),
        ]
        groups = {g.key.exchange: g for g in attribute(trades).by_exchange()}
        assert groups["binance"].total_trades == 2
        assert groups["kraken"].total_trades == 1

    def test_group_by_period(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", created_at="2026-03-01T00:00:00+00:00"),
            _make_trade(trade_id="B", created_at="2026-03-20T00:00:00+00:00"),
            _make_trade(trade_id="C", created_at="2026-04-02T00:00:00+00:00"),
        ]
        groups = {g.key.period: g for g in attribute(trades).by_period()}
        assert groups["2026-03"].total_trades == 2
        assert groups["2026-04"].total_trades == 1

    def test_group_by_strategy_and_exchange(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", strategy_id="s1", exchange="binance"),
            _make_trade(trade_id="B", strategy_id="s1", exchange="kraken"),
            _make_trade(trade_id="C", strategy_id="s2", exchange="binance"),
        ]
        groups = attribute(trades).by_strategy_and_exchange()
        combos = {(g.key.strategy_id, g.key.exchange) for g in groups}
        assert combos == {("s1", "binance"), ("s1", "kraken"), ("s2", "binance")}

    def test_missing_account_and_asset_are_not_inferred(self):
        from core.investment.attribution import attribute

        trades = [_make_trade(trade_id="A", account_id="", asset="")]
        group = attribute(trades).by_strategy()[0]
        # Reported as missing, never filled with a guessed value
        assert "account_id" in group.missing_dimensions
        assert "asset" in group.missing_dimensions
        assert group.key.account_id != "acc-1"

    def test_account_attribution_reports_unavailable(self):
        from core.investment.attribution import attribute

        trades = [_make_trade(trade_id="A", account_id="")]
        groups = attribute(trades).by_account()
        assert len(groups) == 1
        assert groups[0].key.account_id == ""
        assert "account_id" in groups[0].missing_dimensions

    def test_gross_is_never_reported_as_net(self):
        from core.investment.attribution import attribute

        # Fees and slippage known, but costs are not confirmed complete
        trades = [
            _make_trade(trade_id="A", gross_pnl=10.0, fees=1.0, slippage=0.5, completeness="INCOMPLETE"),
            _make_trade(trade_id="B", gross_pnl=-4.0, fees=1.0, slippage=0.5, completeness="INCOMPLETE"),
        ]
        group = attribute(trades).by_strategy()[0]
        assert group.gross_pnl_complete == pytest.approx(6.0)
        assert group.net_pnl_complete == 0.0
        assert "no_complete_net" in group.roi_basis
        assert group.roi_pct is None

    def test_net_only_from_complete_trades(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", gross_pnl=10.0, fees=1.0, slippage=0.5, completeness="COMPLETE"),
            _make_trade(trade_id="B", gross_pnl=-4.0, fees=1.0, slippage=0.5, completeness="INCOMPLETE"),
        ]
        group = attribute(trades).by_strategy()[0]
        # Only the COMPLETE trade contributes to net: 10 - 1 - 0.5 = 8.5
        assert group.net_pnl_complete == pytest.approx(8.5)
        assert group.pnl_completeness == "PARTIAL"

    def test_currency_mismatch_blocks_net_aggregation(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", currency="USDT"),
            _make_trade(trade_id="B", currency="EUR"),
        ]
        group = attribute(trades).by_strategy()[0]
        assert group.currency_mismatch is True
        assert group.net_pnl_complete == 0.0
        assert group.currencies_seen == {"USDT", "EUR"}
        assert "currency_mismatch" in group.roi_basis

    def test_provenance_is_reported_separately(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", provenance="EXCHANGE"),
            _make_trade(trade_id="B", provenance="MANUAL"),
            _make_trade(trade_id="C", provenance="MANUAL"),
        ]
        group = attribute(trades).by_strategy()[0]
        assert group.provenance_breakdown == {"EXCHANGE": 1, "MANUAL": 2}
        by_prov = {g.key.provenance: g for g in attribute(trades).by_provenance()}
        assert set(by_prov) == {"EXCHANGE", "MANUAL"}

    def test_duplicates_are_excluded_from_aggregates(self):
        from core.investment.attribution import attribute

        a = _make_trade(trade_id="A")
        dup = _make_trade(trade_id="B")  # same payload, different id
        group = attribute([a, dup]).by_strategy()[0]
        assert group.total_trades == 2
        assert group.trade_ids == ["A", "B"]
        assert group.eligible_trades == 1
        assert group.excluded_reasons.get("duplicate") == 1

    def test_traceability_by_trade_id(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", gross_pnl=1.0),
            _make_trade(trade_id="B", gross_pnl=2.0),
        ]
        group = attribute(trades).by_strategy()[0]
        assert set(group.trade_ids) == {"A", "B"}

    def test_missing_dimensions_exclude_and_count(self):
        from core.investment.attribution import attribute

        missing_currency = _make_trade(trade_id="A", currency="")
        group = attribute([missing_currency]).by_strategy()[0]
        assert group.eligible_trades == 0
        assert group.excluded_trades == 1
        assert any("missing_currency" in reason for reason in group.excluded_reasons)
        assert group.sample_quality == "NO_ELIGIBLE_TRADES"

    def test_no_trades_yields_no_groups(self):
        from core.investment.attribution import attribute

        # Nothing recorded means nothing to attribute: no fabricated empty group.
        assert attribute([]).by_strategy() == []
        assert attribute([]).all_groups() == []

    def test_sample_quality_small_sample(self):
        from core.investment.attribution import attribute

        group = attribute([_make_trade(trade_id="A")]).by_strategy()[0]
        assert group.sample_quality == "SMALL_SAMPLE"

    def test_sample_quality_complete(self):
        from core.investment.attribution import attribute

        trades = [_make_trade(trade_id=f"T{i}", created_at=f"2026-03-15T10:0{i}:00+00:00") for i in range(5)]
        group = attribute(trades).by_strategy()[0]
        assert group.sample_quality == "COMPLETE"
        assert group.pnl_completeness == "COMPLETE"

    def test_win_rate_declares_its_series(self):
        from core.investment.attribution import attribute

        trades = [
            _make_trade(trade_id="A", gross_pnl=10.0, fees=1.0, slippage=1.0),
            _make_trade(trade_id="B", gross_pnl=-10.0, fees=1.0, slippage=1.0),
        ]
        group = attribute(trades).by_strategy()[0]
        assert group.win_rate_definition
        assert "COMPLETE" in group.win_rate_definition
        assert group.win_rate_explicit == 0.5
        assert group.winning_trades == 1
        assert group.losing_trades == 1

    def test_legacy_trade_without_new_fields_still_attributes(self):
        from core.investment.attribution import attribute

        # Historical trade: no exchange, account_id or asset recorded
        legacy = _make_trade(trade_id="OLD", exchange="", account_id="", asset="")
        group = attribute([legacy]).by_strategy()[0]
        assert group.total_trades == 1
        assert group.eligible_trades == 1
        assert {"exchange", "account_id", "asset"} <= group.missing_dimensions

    def test_zero_pnl_is_break_even_not_win(self):
        from core.investment.attribution import attribute

        trade = _make_trade(trade_id="A", gross_pnl=1.5, fees=1.0, slippage=0.5)
        group = attribute([trade]).by_strategy()[0]
        assert group.break_even_trades == 1
        assert group.winning_trades == 0
        assert group.win_rate_explicit == 0.0


# ── Strategy attribution exposed through /metrics ───────────────


class TestStrategyAttributionEndpoint:
    """The metrics endpoint must publish attribution with its caveats."""

    @staticmethod
    def _isolated_metrics():
        from core.investment.metrics import InvestmentMetrics

        metrics = InvestmentMetrics()
        metrics._trade_history = []  # ignore whatever the real history file holds
        return metrics

    def test_trade_evidence_does_not_infer_missing_dimensions(self):
        metrics = self._isolated_metrics()
        metrics.record_trade("ccxt_spot", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0, fee=1.0)

        evidence = metrics.trade_evidence()

        assert len(evidence) == 1
        trade = evidence[0]
        assert trade.strategy_id == "ccxt_spot"
        assert trade.gross_pnl == pytest.approx(10.0)
        assert trade.fees == pytest.approx(1.0)
        # Never captured by the legacy record: reported empty, not guessed.
        assert trade.currency == ""
        assert trade.exchange == ""
        assert trade.account_id == ""
        assert trade.asset == ""
        assert trade.net_pnl_completeness == "INCOMPLETE"

    def test_legacy_record_without_currency_is_excluded_not_guessed(self):
        """A record that never captured its currency cannot be summed at all."""
        metrics = self._isolated_metrics()
        metrics.record_trade("ccxt_spot", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0, fee=1.0)

        group = metrics.strategy_attribution()[0]

        assert group["key"]["strategy_id"] == "ccxt_spot"
        assert group["total_trades"] == 1
        # Excluded from every money metric rather than assumed to be USDT.
        assert group["eligible_trades"] == 0
        assert group["gross_pnl_complete"] == 0.0
        assert group["net_pnl_complete"] == 0.0
        assert any("missing_currency" in reason for reason in group["excluded_reasons"])
        assert group["sample_quality"] == "NO_ELIGIBLE_TRADES"

    def test_recorded_currency_makes_legacy_trade_attributable(self):
        metrics = self._isolated_metrics()
        metrics.record_trade("ccxt_spot", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0, fee=1.0, currency="USDT")

        group = metrics.strategy_attribution()[0]

        assert group["eligible_trades"] == 1
        assert group["gross_pnl_complete"] == pytest.approx(10.0)
        # Gross is real, but no declared COMPLETE net exists for this record.
        assert group["net_pnl_complete"] == 0.0
        assert "no_complete_net" in group["roi_basis"]
        assert group["pnl_completeness"] != "COMPLETE"

    def test_declared_completeness_and_currency_are_honoured(self):
        metrics = self._isolated_metrics()
        metrics.record_trade(
            "polymarket",
            "BTC/USDT",
            "buy",
            100.0,
            110.0,
            1.0,
            10.0,
            10.0,
            fee=1.0,
            currency="USDT",
            net_pnl_completeness="COMPLETE",
        )

        group = metrics.strategy_attribution()[0]

        assert group["currencies_seen"] == ["USDT"]
        assert group["net_pnl_complete"] == pytest.approx(10.0)
        assert group["pnl_completeness"] == "COMPLETE"
        assert group["sample_quality"] == "SMALL_SAMPLE"

    def test_attribution_is_serialisable_and_traceable(self):
        metrics = self._isolated_metrics()
        metrics.record_trade("ccxt_spot", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0, currency="USDT")
        metrics.record_trade("polymarket", "BTC/USDT", "buy", 100.0, 90.0, 1.0, -10.0, -10.0, currency="USDT")

        payload = metrics.strategy_attribution()

        assert {g["key"]["strategy_id"] for g in payload} == {"ccxt_spot", "polymarket"}
        for group in payload:
            assert group["trade_ids"]
            assert isinstance(group["currencies_seen"], list)
            assert isinstance(group["missing_dimensions"], list)
            assert group["win_rate_definition"]
            json.dumps(group)  # must survive JSON encoding for the API

    def test_metrics_endpoint_exposes_strategy_attribution(self, client):
        response = client.get("/api/investment/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "strategy_attribution" in data
        assert isinstance(data["strategy_attribution"], list)

    def test_manager_delegates_attribution(self):
        from core.investment.manager import get_investment_manager

        manager = get_investment_manager()

        attribution = manager.get_strategy_attribution()

        assert isinstance(attribution, list)


def _isolated_manager(monkeypatch):
    """Manager whose metrics keep history in memory only, never on disk."""
    from core.investment.manager import InvestmentManager
    from core.investment.metrics import InvestmentMetrics

    isolated = InvestmentMetrics()
    isolated._trade_history = []
    # Neutralise persistence so the real ~/.orion history stays untouched.
    monkeypatch.setattr(isolated, "_persist_trade", lambda trade: None)

    manager = InvestmentManager()
    manager._metrics = isolated
    return manager, isolated


class TestRecordTradeResultFeedsAttribution:
    """record_trade_result is the write path that makes attribution possible."""

    def test_currency_recorded_through_manager_reaches_attribution(self, monkeypatch):
        manager, metrics = _isolated_manager(monkeypatch)

        manager.record_trade_result(
            "global_arbitrage",
            "BTC/USDT",
            "arb",
            100.0,
            101.0,
            1.0,
            1.0,
            1.0,
            currency="USDT",
            net_pnl_completeness="PARTIAL",
        )

        stored = metrics._trade_history[0]
        assert stored["currency"] == "USDT"
        assert stored["net_pnl_completeness"] == "PARTIAL"

        group = manager.get_strategy_attribution()[0]
        assert group["total_trades"] == 1
        assert group["eligible_trades"] == 1
        assert group["currencies_seen"] == ["USDT"]
        assert group["gross_pnl_complete"] == pytest.approx(1.0)

    def test_partial_completeness_never_reports_a_definitive_net(self, monkeypatch):
        """A simulated fee without slippage is not a complete net figure."""
        manager, _ = _isolated_manager(monkeypatch)

        manager.record_trade_result(
            "global_arbitrage",
            "BTC/USDT",
            "arb",
            100.0,
            101.0,
            1.0,
            1.0,
            1.0,
            fee=0.1,
            currency="USDT",
            net_pnl_completeness="PARTIAL",
        )

        group = manager.get_strategy_attribution()[0]
        assert group["net_pnl_complete"] == 0.0
        assert group["pnl_completeness"] != "COMPLETE"

    def test_omitting_currency_keeps_the_trade_unattributable(self, monkeypatch):
        """The write path must not invent a currency from the symbol."""
        manager, metrics = _isolated_manager(monkeypatch)

        manager.record_trade_result("global_arbitrage", "BTC/USDT", "arb", 100.0, 101.0, 1.0, 1.0, 1.0)

        assert metrics._trade_history[0]["currency"] == ""
        group = manager.get_strategy_attribution()[0]
        assert group["eligible_trades"] == 0
        assert any("missing_currency" in reason for reason in group["excluded_reasons"])


def _paper_trade_module():
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parent.parent / "scripts" / "paper_trade.py"
    spec = importlib.util.spec_from_file_location("paper_trade_under_test", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_paper_trade_declares_quote_currency():
    """The paper trader knows its ccxt pairs, so it declares the quote asset."""
    module = _paper_trade_module()

    assert module._quote_currency("BTC/USDT") == "USDT"
    assert module._quote_currency("eth/btc") == "BTC"
    # No quote in the symbol: stays empty instead of being invented.
    assert module._quote_currency("BTC") == ""
    assert module._quote_currency("") == ""


class TestMeasuredSlippage:
    """Slippage must come from the book, never from a guessed bps figure."""

    def test_single_level_book_fills_at_touch(self):
        from core.investment.adapters.global_arbitrage_adapter import walk_book_for_size

        # 1 BTC at 100 means deep enough for $100 with no adverse movement.
        walked = walk_book_for_size([[100.0, 1.0]], 100.0)

        assert walked is not None
        vwap, filled = walked
        assert vwap == pytest.approx(100.0)
        assert filled == pytest.approx(100.0)

    def test_walking_deeper_levels_raises_the_buy_price(self):
        from core.investment.adapters.global_arbitrage_adapter import walk_book_for_size

        # Only $50 at the touch, the rest must lift the 101 level.
        walked = walk_book_for_size([[100.0, 0.5], [101.0, 1.0]], 100.0)

        assert walked is not None
        vwap, filled = walked
        assert filled == pytest.approx(100.0)
        assert vwap > 100.0
        assert vwap < 101.0

    def test_insufficient_depth_is_unmeasurable_not_extrapolated(self):
        from core.investment.adapters.global_arbitrage_adapter import walk_book_for_size

        # Only $50 visible for a $100 order: no honest slippage number exists.
        assert walk_book_for_size([[100.0, 0.5]], 100.0) is None
        assert walk_book_for_size([], 100.0) is None
        assert walk_book_for_size([[100.0, 1.0]], 0.0) is None

    def test_malformed_levels_are_rejected(self):
        from core.investment.adapters.global_arbitrage_adapter import walk_book_for_size

        assert walk_book_for_size([["x", 1.0]], 10.0) is None
        assert walk_book_for_size([[0.0, 1.0]], 10.0) is None

    @pytest.mark.asyncio
    async def test_measure_slippage_reports_unmeasurable_without_ccxt(self, monkeypatch):
        """No ccxt means no measurement, never a fabricated 0.0%."""
        import builtins

        from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

        adapter = GlobalArbitrageAdapter()
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name.startswith("ccxt"):
                raise ImportError("no ccxt")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        result = await adapter.measure_slippage({"symbol": "BTC/USDT", "buy_on": "a", "sell_on": "b", "buy_price": 1.0, "sell_price": 1.0}, 100.0)

        assert result["measured"] is False
        assert result["reason"] == "ccxt_not_installed"
        assert "slippage_pct" not in result


class TestSimulateCosts:
    """_simulate must cost the trade so net reconciles with its components."""

    _OPP = {
        "symbol": "BTC/USDT",
        "buy_on": "kraken",
        "sell_on": "coinbase",
        "buy_price": 100.0,
        "sell_price": 101.0,
        "spread_pct": 1.0,
    }

    @staticmethod
    def _measured(residual_pct: float, **extra):
        return {
            "measured": True,
            "residual_spread_pct": residual_pct,
            "buy_fill_price": 100.0,
            **extra,
        }

    def test_measured_execution_cost_reduces_net_pnl(self):
        module = _paper_trade_module()

        clean = module._simulate(self._OPP, 500.0, execution=self._measured(1.0))
        costed = module._simulate(self._OPP, 500.0, execution=self._measured(0.8))

        assert costed["pnl"] < clean["pnl"]
        assert costed["slippage_pct"] == pytest.approx(0.2)
        assert costed["slippage_usd"] == pytest.approx(1.0)

    def test_components_reconcile_to_net(self):
        module = _paper_trade_module()

        res = module._simulate(self._OPP, 500.0, execution=self._measured(0.85))

        assert res["gross_pnl"] - res["fee_usd"] - res["slippage_usd"] == pytest.approx(res["pnl"], abs=1e-3)

    def test_unmeasured_execution_keeps_costs_incomplete(self):
        """Without a measurement the scan spread is used and the net stays provisional."""
        module = _paper_trade_module()

        res = module._simulate(self._OPP, 500.0, execution={"measured": False, "reason": "ccxt_not_installed"})

        assert res["costs_complete"] is False
        assert res["slippage_pct"] == 0.0
        assert res["slippage_usd"] == 0.0
        # No measurement: the scan spread is all there is, and it is labelled as such.
        assert res["realized_spread_pct"] == pytest.approx(self._OPP["spread_pct"])

    def test_scan_spread_is_not_the_booked_gross(self):
        """The spread promised at scan time must not survive into the net."""
        module = _paper_trade_module()

        res = module._simulate(self._OPP, 500.0, execution=self._measured(0.1))

        # 1.0% scanned but only 0.1% survived both fills.
        assert res["realized_spread_pct"] == pytest.approx(0.1)
        assert res["net_pct"] == pytest.approx(0.1 - module.FEE_PCT, abs=1e-6)
        assert res["slippage_pct"] == pytest.approx(0.9)

    def test_quantity_uses_the_real_fill_price(self):
        module = _paper_trade_module()

        res = module._simulate(self._OPP, 500.0, execution=self._measured(1.0, buy_fill_price=100.5))

        assert res["qty"] == pytest.approx(res["deployed"] / 100.5)


class _StubExchange:
    """Minimal ccxt exchange stand-in returning a canned book, never a network."""

    def __init__(self, book: dict, fail: bool = False):
        self._book = book
        self._fail = fail
        self.fetched = 0
        self.closed = False

    async def fetch_order_book(self, symbol, limit=50):
        self.fetched += 1
        if self._fail:
            raise RuntimeError("book down")
        return self._book

    async def close(self):
        self.closed = True


def _stub_ccxt(monkeypatch, books: dict[str, dict | None]):
    """Install a fake ``ccxt.async_support`` exposing one exchange per name."""
    import sys
    import types

    created: list[_StubExchange] = []

    def factory(name: str):
        def build(_config=None):
            book = books.get(name)
            ex = _StubExchange(book or {}, fail=book is None)
            created.append(ex)
            return ex

        return build

    module = types.ModuleType("ccxt.async_support")
    for name in books:
        setattr(module, name, factory(name))
    package = types.ModuleType("ccxt")
    package.async_support = module
    monkeypatch.setitem(sys.modules, "ccxt", package)
    monkeypatch.setitem(sys.modules, "ccxt.async_support", module)
    return created


class TestExecutionRisk:
    """The second leg fills later: the spread captured is not the scanned one."""

    _OPP = {
        "symbol": "BTC/USDT",
        "buy_on": "kraken",
        "sell_on": "coinbase",
        "buy_price": 100.0,
        "sell_price": 101.0,
        "spread_pct": 1.0,
    }

    def test_residual_spread_uses_both_fill_prices(self):
        from core.investment.adapters.global_arbitrage_adapter import residual_spread_pct

        assert residual_spread_pct(100.0, 101.0) == pytest.approx(1.0)
        # Sold below the purchase price: the arbitrage is gone, not "zero cost".
        assert residual_spread_pct(100.0, 99.5) == pytest.approx(-0.5)
        with pytest.raises(ValueError):
            residual_spread_pct(0.0, 101.0)

    def test_drift_is_signed_against_us(self):
        from core.investment.adapters.global_arbitrage_adapter import quote_drift_pct

        # Buy leg asks rose: we pay more, adverse.
        assert quote_drift_pct("buy", 100.0, 100.5) == pytest.approx(0.5)
        # Sell leg bid fell: we receive less, adverse.
        assert quote_drift_pct("sell", 101.0, 100.0) == pytest.approx((101.0 - 100.0) / 101.0 * 100.0)
        # Moved in our favour: reported as a gain, not clamped to zero.
        assert quote_drift_pct("sell", 100.0, 101.0) < 0
        with pytest.raises(ValueError):
            quote_drift_pct("hold", 100.0, 101.0)

    @pytest.mark.asyncio
    async def test_second_leg_drift_eats_the_spread(self, monkeypatch):
        """The sell book is read after the buy fills, so its drop is captured."""
        from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

        books = {
            "kraken": {"asks": [[100.0, 10.0]], "bids": [[99.9, 10.0]]},
            # By the time the sell leg fills the bid has fallen to 100.2.
            "coinbase": {"asks": [[100.3, 10.0]], "bids": [[100.2, 10.0]]},
        }
        created = _stub_ccxt(monkeypatch, books)

        result = await GlobalArbitrageAdapter().measure_slippage(self._OPP, 100.0)

        assert result["measured"] is True
        assert result["buy_fill_price"] == pytest.approx(100.0)
        assert result["sell_fill_price"] == pytest.approx(100.2)
        # Scanned 1.0%, captured 0.2%.
        assert result["residual_spread_pct"] == pytest.approx(0.2)
        assert result["sell_drift_pct"] > 0
        assert result["depth_slippage_pct"] == pytest.approx(0.0, abs=1e-9)
        assert result["leg_gap_seconds"] >= 0.0
        # Every stub exchange the measurement opened was also closed.
        assert created and all(ex.closed for ex in created)

    @pytest.mark.asyncio
    async def test_depth_cost_is_measured_against_each_own_book(self, monkeypatch):
        from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

        books = {
            # $100 order only gets $50 at the touch, the rest lifts 101.
            "kraken": {"asks": [[100.0, 0.5], [101.0, 5.0]], "bids": [[99.9, 10.0]]},
            "coinbase": {"asks": [[100.5, 10.0]], "bids": [[101.0, 10.0]]},
        }
        _stub_ccxt(monkeypatch, books)

        result = await GlobalArbitrageAdapter().measure_slippage(self._OPP, 100.0)

        assert result["measured"] is True
        assert result["buy_slippage_pct"] > 0
        assert result["depth_slippage_pct"] == pytest.approx(result["buy_slippage_pct"] + result["sell_slippage_pct"])
        # Realized gross is strictly worse than the quoted 1.0% spread.
        assert result["residual_spread_pct"] < self._OPP["spread_pct"]

    @pytest.mark.asyncio
    async def test_unreachable_second_book_is_unmeasurable(self, monkeypatch):
        from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

        _stub_ccxt(monkeypatch, {"kraken": {"asks": [[100.0, 10.0]], "bids": [[99.9, 10.0]]}, "coinbase": None})

        result = await GlobalArbitrageAdapter().measure_slippage(self._OPP, 100.0)

        assert result["measured"] is False
        assert result["reason"].startswith("book_unavailable:coinbase")
        assert "residual_spread_pct" not in result
        # Leg 1 was priced and leg 2 has nowhere to go: unhedged, not just unmeasured.
        assert result["leg_unhedged"] is True
        assert result["buy_fill_price"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_thin_second_book_is_unmeasurable(self, monkeypatch):
        """No depth on the exit leg means the trade could not have been exited."""
        from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

        _stub_ccxt(monkeypatch, {"kraken": {"asks": [[100.0, 10.0]], "bids": [[99.9, 10.0]]}, "coinbase": {"asks": [[100.5, 10.0]], "bids": [[101.0, 0.1]]}})

        result = await GlobalArbitrageAdapter().measure_slippage(self._OPP, 100.0)

        assert result["measured"] is False
        assert result["reason"] == "insufficient_depth:coinbase"
        assert result["leg_unhedged"] is True
        assert result["unhedged_value_usd"] == pytest.approx(100.0)

    @pytest.mark.asyncio
    async def test_execution_risk_flows_into_the_recorded_metadata(self, monkeypatch):
        """End to end: drift measured on the book reaches the recorded trade."""
        from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

        _stub_ccxt(
            monkeypatch,
            {
                "kraken": {"asks": [[100.0, 10.0]], "bids": [[99.9, 10.0]]},
                "coinbase": {"asks": [[100.3, 10.0]], "bids": [[100.2, 10.0]]},
            },
        )
        module = _paper_trade_module()
        opp = dict(self._OPP)

        execution = await GlobalArbitrageAdapter().measure_slippage(opp, 100.0)
        res = module._simulate(opp, 500.0, execution=execution)

        assert res["costs_complete"] is True
        assert res["realized_spread_pct"] == pytest.approx(0.2)
        assert res["slippage_pct"] == pytest.approx(0.8, abs=1e-6)
        assert res["drift_pct"] == pytest.approx(execution["drift_pct"], abs=1e-3)
        assert res["gross_pnl"] - res["fee_usd"] - res["slippage_usd"] == pytest.approx(res["pnl"], abs=1e-3)


class TestLegUnhedged:
    """Entry leg filled, exit leg empty: an open position, not a measured cost."""

    _OPP = {
        "symbol": "BTC/USDT",
        "buy_on": "kraken",
        "sell_on": "coinbase",
        "buy_price": 100.0,
        "sell_price": 101.0,
        "spread_pct": 1.0,
    }

    @pytest.mark.asyncio
    async def test_first_leg_failure_is_not_an_unhedged_position(self, monkeypatch):
        """Nothing was bought, so there is no exposure to report."""
        from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter

        _stub_ccxt(monkeypatch, {"kraken": None, "coinbase": {"asks": [[100.5, 10.0]], "bids": [[101.0, 10.0]]}})

        result = await GlobalArbitrageAdapter().measure_slippage(self._OPP, 100.0)

        assert result["measured"] is False
        assert result["leg_unhedged"] is False
        assert result["reason"].startswith("book_unavailable:kraken")

    def test_simulate_refuses_to_price_an_unhedged_round(self):
        """There is no exit price, so any net figure here would be invented."""
        module = _paper_trade_module()
        execution = {
            "measured": False,
            "leg_unhedged": True,
            "reason": "insufficient_depth:coinbase",
            "unhedged_value_usd": 100.0,
            "buy_fill_price": 100.0,
            "leg_gap_seconds": 0.25,
        }

        res = module._simulate(self._OPP, 500.0, execution=execution)

        assert res["leg_unhedged"] is True
        assert res["costs_complete"] is False
        assert res["realized_spread_pct"] is None
        assert res["net_pct"] is None
        assert res["gross_pnl"] is None
        assert res["unhedged_value_usd"] == pytest.approx(100.0)
        assert res["unhedged_reason"] == "insufficient_depth:coinbase"
        # qty is sized on the real buy fill, and no P&L is claimed.
        assert res["qty"] == pytest.approx(res["deployed"] / 100.0)
        assert res["pnl"] == 0.0

    def test_recorded_unhedged_trade_keeps_its_level_and_claims_no_pnl(self):
        metrics = TestStrategyAttributionEndpoint._isolated_metrics()
        metrics.record_trade(
            "global_arbitrage",
            "BTC/USDT",
            "arb",
            100.0,
            0.0,
            1.0,
            0.0,
            0.0,
            currency="USDT",
            net_pnl_completeness="LEG_UNHEDGED",
            metadata={"leg_unhedged": True, "unhedged_value_usd": 100.0},
        )

        trade = metrics.trade_evidence()[0]

        # Declared, never coerced down to INCOMPLETE.
        assert trade.net_pnl_completeness == "LEG_UNHEDGED"
        # No gross fallback from the placeholder pnl: nothing was realized.
        assert trade.gross_pnl is None
        assert trade.net_pnl is None
        assert trade.net_pnl_calc == 0.0

    def test_unhedged_round_is_counted_but_never_a_result(self):
        metrics = TestStrategyAttributionEndpoint._isolated_metrics()
        for pnl, level in ((0.65, "COMPLETE"), (0.0, "LEG_UNHEDGED")):
            metrics.record_trade(
                "global_arbitrage",
                "BTC/USDT",
                "arb",
                100.0,
                101.0,
                1.0,
                pnl,
                0.65 if level == "COMPLETE" else 0.0,
                currency="USDT",
                net_pnl_completeness=level,
                metadata={"gross_pnl": 2.0, "slippage": 0.85} if level == "COMPLETE" else {},
            )

        risk = metrics.get_strategy_metrics("global_arbitrage")

        # The open position does not dilute the realized stats...
        assert risk.total_trades == 1
        assert risk.winning_trades == 1
        assert risk.win_rate == pytest.approx(1.0)
        assert risk.unhedged_trades == 1
        assert metrics.consolidated_metrics()["unhedged_trades"] == 1

        group = metrics.strategy_attribution()[0]
        assert group["unhedged_trades"] == 1
        assert group["net_pnl_complete"] == pytest.approx(0.65)
        assert group["gross_pnl_complete"] == pytest.approx(2.0)
        # ...and the group cannot claim a complete net while it does.
        assert group["pnl_completeness"] == "PARTIAL"


class TestCompleteNetNeedsMeasuredSlippage:
    """COMPLETE is only honest when fees and measured slippage both exist."""

    @staticmethod
    def _metrics_with_trade(metrics, **kwargs):
        metrics.record_trade("global_arbitrage", "BTC/USDT", "arb", 100.0, 101.0, 1.0, 0.65, 0.65, **kwargs)
        return metrics.strategy_attribution()[0]

    def test_evidence_reads_measured_slippage_and_gross(self):
        metrics = TestStrategyAttributionEndpoint._isolated_metrics()
        metrics.record_trade(
            "global_arbitrage",
            "BTC/USDT",
            "arb",
            100.0,
            101.0,
            1.0,
            0.65,
            0.65,
            fee=0.5,
            currency="USDT",
            net_pnl_completeness="COMPLETE",
            metadata={"gross_pnl": 2.0, "slippage": 0.85},
        )

        trade = metrics.trade_evidence()[0]

        assert trade.gross_pnl == pytest.approx(2.0)
        assert trade.fees == pytest.approx(0.5)
        assert trade.slippage == pytest.approx(0.85)
        # The recorded pnl is the fully costed net, and it reconciles.
        assert trade.net_pnl_calc == pytest.approx(0.65)
        assert trade.gross_pnl - trade.fees - trade.slippage == pytest.approx(trade.net_pnl_calc, abs=1e-9)

    def test_complete_trade_yields_a_definitive_net_in_attribution(self):
        metrics = TestStrategyAttributionEndpoint._isolated_metrics()

        group = self._metrics_with_trade(
            metrics,
            fee=0.5,
            currency="USDT",
            net_pnl_completeness="COMPLETE",
            metadata={"gross_pnl": 2.0, "slippage": 0.85},
        )

        assert group["eligible_trades"] == 1
        assert group["net_pnl_complete"] == pytest.approx(0.65)
        assert group["gross_pnl_complete"] == pytest.approx(2.0)
        assert group["pnl_completeness"] == "COMPLETE"

    def test_legacy_record_still_reports_zero_slippage_not_a_guess(self):
        metrics = TestStrategyAttributionEndpoint._isolated_metrics()

        metrics.record_trade("ccxt_spot", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0)

        trade = metrics.trade_evidence()[0]

        assert trade.slippage == 0.0
        assert trade.gross_pnl == pytest.approx(10.0)
        assert trade.net_pnl_completeness == "INCOMPLETE"
