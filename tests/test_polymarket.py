from __future__ import annotations

import pytest

from core.polymarket.manager import PolymarketManager, list_strategies
from core.polymarket.strategies import (
    BTCArbitrageStrategy,
    CompleteSetArbitrage,
    PolymarketLPMarketMaker,
    SmartMoneyCopier,
    WeatherMarketStrategy,
)


def test_list_strategies():
    s = list_strategies()
    assert isinstance(s, dict)
    assert "btc_arb" in s
    assert "smart_money" in s
    assert "complete_arb" in s
    assert "weather" in s
    assert "lp_mm" in s
    assert len(s) == 5


def test_manager_list():
    mgr = PolymarketManager()
    assert mgr is not None


class TestBTCArbitrage:
    def test_init(self):
        s = BTCArbitrageStrategy()
        assert s.name == "polymarket_btc_arb"

    def test_check_setup_no_binance(self):
        s = BTCArbitrageStrategy()
        assert s.name == "polymarket_btc_arb"

    @pytest.mark.asyncio
    async def test_check_setup(self):
        s = BTCArbitrageStrategy({"btc_move_threshold": 50})
        result = await s.check_setup()
        assert isinstance(result, dict)
        # binance might not be reachable in CI
        assert "binance" in result
        assert "ready" in result

    @pytest.mark.asyncio
    async def test_scan_opportunity(self):
        s = BTCArbitrageStrategy()
        result = await s.scan_opportunity()
        assert isinstance(result, dict)
        assert "signal" in result
        assert "btc_move" in result

    def test_make_plan_no_signal(self):
        s = BTCArbitrageStrategy()
        plan = s.make_plan({"signal": False, "reason": "test"})
        assert plan.get("execute") is False

    def test_make_plan_with_signal(self):
        s = BTCArbitrageStrategy()
        plan = s.make_plan({"signal": True, "direction": "up", "btc_move": 100, "btc_price": 65000})
        assert plan.get("execute") is True
        assert plan.get("side") == "BUY"
        assert plan.get("outcome") == "YES"
        assert plan.get("size_usd") == 1.0


class TestSmartMoneyCopier:
    def test_init(self):
        s = SmartMoneyCopier()
        assert s.name == "polymarket_smart_money"

    @pytest.mark.asyncio
    async def test_scan_top_traders(self):
        s = SmartMoneyCopier()
        traders = await s.scan_top_traders(limit=3)
        assert isinstance(traders, list)

    @pytest.mark.asyncio
    async def test_generate_copy_signals(self):
        s = SmartMoneyCopier()
        signals = await s.generate_copy_signals()
        assert isinstance(signals, list)

    def test_empty_target_user(self):
        s = SmartMoneyCopier()
        assert s._target_user == ""


class TestCompleteSetArbitrage:
    def test_init(self):
        s = CompleteSetArbitrage()
        assert s.name == "polymarket_complete_arb"

    @pytest.mark.asyncio
    async def test_scan_opportunities(self):
        s = CompleteSetArbitrage({"min_spread": 0.5})
        opps = await s.scan_opportunities(limit=5)
        assert isinstance(opps, list)

    def test_config_min_spread(self):
        s = CompleteSetArbitrage({"min_spread": 0.1})
        assert s._min_spread == 0.1


class TestWeatherMarketStrategy:
    def test_init(self):
        s = WeatherMarketStrategy()
        assert s.name == "polymarket_weather"

    @pytest.mark.asyncio
    async def test_fetch_temperature(self):
        s = WeatherMarketStrategy()
        data = await s.fetch_temperature()
        assert isinstance(data, dict)

    def test_predict_settlement(self):
        s = WeatherMarketStrategy()
        result = s.predict_settlement({"current_temp": 35, "today_max": 38}, threshold=30)
        assert result.get("predictable") is True
        assert result.get("prediction") == "above"
        assert isinstance(result.get("confidence"), float)

    def test_predict_below(self):
        s = WeatherMarketStrategy()
        result = s.predict_settlement({"current_temp": 15, "today_max": 20}, threshold=30)
        assert result.get("predictable") is True
        assert result.get("prediction") == "below"

    def test_predict_no_data(self):
        s = WeatherMarketStrategy()
        result = s.predict_settlement({}, threshold=30)
        assert result.get("predictable") is False


class TestPolymarketLPMarketMaker:
    def test_init(self):
        s = PolymarketLPMarketMaker()
        assert s.name == "polymarket_lp"

    @pytest.mark.asyncio
    async def test_get_open_orders(self):
        s = PolymarketLPMarketMaker()
        orders = await s.get_open_orders()
        assert isinstance(orders, list)

    @pytest.mark.asyncio
    async def test_price_orders(self):
        s = PolymarketLPMarketMaker()
        orders = await s.price_orders("market-123", {"YES": 0.65, "NO": 0.35})
        assert isinstance(orders, list)
        assert len(orders) == 2

    @pytest.mark.asyncio
    async def test_summary(self):
        s = PolymarketLPMarketMaker()
        summary = await s.summary()
        assert isinstance(summary, dict)
        assert "active_orders" in summary
