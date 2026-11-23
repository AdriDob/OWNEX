"""Investment integrity: incomplete P&L and duplicates must not inflate metrics."""

from __future__ import annotations

import pytest


def _metrics():
    from core.investment.metrics import InvestmentMetrics

    m = InvestmentMetrics()
    m._trade_history = []  # ignore real history file
    return m


def _evidence(trade_id: str, **kw):
    from core.investment.models import TradeEvidence

    base = dict(
        trade_id=trade_id,
        strategy_id="s1",
        symbol="BTC/USDT",
        side="buy",
        currency="USDT",
        gross_pnl=10.0,
        fees=1.0,
        slippage=0.5,
        net_pnl=8.5,
        net_pnl_calc=8.5,
        net_pnl_completeness="COMPLETE",
        exchange="binance",
        account_id="acc-1",
        asset="BTC",
        created_at="2026-03-15T10:00:00+00:00",
    )
    base.update(kw)
    return TradeEvidence(**base)


class TestDuplicateExclusion:
    def test_duplicate_payload_excluded_from_aggregates(self):
        from core.investment.attribution import attribute

        trades = [
            _evidence("A"),
            _evidence("B"),  # identical payload → duplicate of A
            _evidence("C", symbol="ETH/USDT"),
        ]
        group = attribute(trades).by_strategy()[0]

        assert group.total_trades == 3
        assert group.eligible_trades == 2
        assert group.excluded_reasons.get("duplicate") == 1
        # net = 8.5 + 8.5, not 8.5 * 3
        assert group.net_pnl_complete == pytest.approx(17.0)

    def test_distinct_trades_all_eligible(self):
        from core.investment.attribution import attribute

        trades = [_evidence("A"), _evidence("B", created_at="2026-03-15T11:00:00+00:00")]
        group = attribute(trades).by_strategy()[0]
        assert group.eligible_trades == 2
        assert "duplicate" not in group.excluded_reasons


class TestProvisionalNetExclusion:
    def test_incomplete_trade_not_counted_as_result(self):
        metrics = _metrics()
        metrics.record_trade(
            "s1",
            "BTC/USDT",
            "buy",
            100.0,
            110.0,
            1.0,
            10.0,
            10.0,
            currency="USDT",
            net_pnl_completeness="COMPLETE",
        )
        metrics.record_trade(
            "s1",
            "ETH/USDT",
            "buy",
            100.0,
            90.0,
            1.0,
            -10.0,
            -10.0,
            currency="USDT",
            net_pnl_completeness="INCOMPLETE",
        )

        risk = metrics.get_strategy_metrics("s1")

        assert risk.total_trades == 1
        assert risk.winning_trades == 1
        assert risk.incomplete_trades == 1
        assert risk.win_rate == pytest.approx(1.0)
        cons = metrics.consolidated_metrics()
        assert cons["incomplete_trades"] == 1
        assert cons["total_pnl"] == pytest.approx(10.0)  # provisional -10 excluded

    def test_undeclared_legacy_trade_keeps_historical_behavior(self):
        metrics = _metrics()
        metrics.record_trade("s1", "BTC/USDT", "buy", 100.0, 110.0, 1.0, 10.0, 10.0)

        risk = metrics.get_strategy_metrics("s1")
        assert risk.total_trades == 1
        assert risk.incomplete_trades == 0
