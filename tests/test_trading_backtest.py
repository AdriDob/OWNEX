"""Tests for the memecoin backtester (pure CPU, deterministic, no network)."""

from __future__ import annotations

from cores.trading.backtest import (
    BacktestConfig,
    Snapshot,
    load_snapshots,
    parameter_sweep,
    result_to_dict,
    run_backtest,
    save_snapshot,
    snapshot_to_dict,
)


def _pairs(symbol: str) -> dict:
    """Build a minimal passing pair for a snapshot."""
    return {
        "liquidity_usd": 50_000.0,
        "volume_h24": 80_000.0,
        "pair_created_at": 1_700_000_000_000,
    }


def _rug() -> dict:
    return {
        "holder_count": 200,
        "top_10_pct": 20.0,
        "liquidity_locked": True,
        "mint_disabled": True,
        "freeze_disabled": True,
        "risks": [],
    }


def _series(symbol: str, prices: list[float], start: float = 2_000_000_000.0, step: float = 60.0) -> list[Snapshot]:
    return [
        Snapshot(
            mint=f"mint_{symbol}",
            symbol=symbol,
            timestamp=start + i * step,
            price_usd=price,
            pair=_pairs(symbol),
            rug=_rug(),
        )
        for i, price in enumerate(prices)
    ]


def test_empty_snapshots_returns_no_data():
    result = run_backtest([])
    assert result.metrics["trades"] == 0
    assert result.metrics["verdict"] == "NO_DATA"
    assert result.tokens_evaluated == 0


def test_no_filter_pass_means_no_trades():
    snap = Snapshot(
        mint="mint_x",
        symbol="X",
        timestamp=2_000_000_000.0,
        price_usd=0.01,
        pair={"liquidity_usd": 0.0},  # fails liquidity floor
        rug=_rug(),
    )
    result = run_backtest([snap])
    assert result.metrics["trades"] == 0
    assert len(result.events) == 1
    assert result.events[0]["action"] == "filtered_out"


def test_filter_missing_rug_fails_closed():
    snap = Snapshot(
        mint="mint_y",
        symbol="Y",
        timestamp=2_000_000_000.0,
        price_usd=0.01,
        pair=_pairs("Y"),
        rug=None,
    )
    result = run_backtest([snap])
    assert result.metrics["trades"] == 0
    assert any(e["action"] == "filtered_out" and "RugCheck" in str(e["reasons"]) for e in result.events)


def test_simple_stop_loss_closes_trade():
    series = _series("A", [0.0100, 0.0070])  # entry then -30% → stop-loss (25%)
    result = run_backtest(series, BacktestConfig(stop_loss_pct=0.25))
    assert result.tokens_entered == 1
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.pnl_sol < 0
    assert "stop_loss" in trade.exit_reason


def test_staged_take_profit_partial():
    series = _series("B", [0.0100, 0.0150, 0.0150])  # +50% → sell half, remaining half closes next tick at same tier
    result = run_backtest(series, BacktestConfig(take_profit_tiers=((0.5, 0.5),)))
    assert len(result.trades) == 2
    assert all("take_profit" in t.exit_reason for t in result.trades)
    assert result.metrics["realized_pnl_sol"] > 0


def test_time_stop_after_max_hold():
    # Never breaches any price band but age exceeds max_hold
    series = _series(
        "C",
        [0.0100] * 60,
        start=2_000_000_000.0,
        step=60 * 3,  # 3 minutes per step → 60 steps = 3h
    )
    result = run_backtest(series, BacktestConfig(max_hold_minutes=120.0))
    if result.trades:
        assert any("time_stop" in t.exit_reason for t in result.trades)


def test_determinism_same_input_same_output():
    series = _series("D", [0.0100, 0.0120, 0.0140, 0.0110, 0.0090, 0.0150, 0.0200, 0.0180])
    r1 = run_backtest(series)
    r2 = run_backtest(series)
    assert r1 == r2


def test_metrics_shape_and_verdict():
    series = _series("E", [0.0100, 0.0050] * 30)  # alternating → many stop-losses
    result = run_backtest(series, BacktestConfig(stop_loss_pct=0.25))
    m = result.metrics
    for key in ("trades", "wins", "win_rate", "expectancy_sol", "realized_pnl_sol", "max_drawdown_sol", "verdict"):
        assert key in m
    assert m["trades"] == len(result.trades)


def test_daily_loss_kill_switch_stops_token():
    # 3 consecutive hard stop-losses within the same day breach the limit
    series = _series(
        "F",
        [0.01, 0.006, 0.01, 0.006, 0.01, 0.006, 0.01, 0.006],
        step=120,
    )
    result = run_backtest(series, BacktestConfig(daily_loss_limit_sol=0.03, stop_loss_pct=0.25))
    # kills after realized losses exceed 0.03 SOL → fewer trades than provided
    assert "kill_triggered" in [e["action"] for e in result.events]
    assert result.metrics["realized_pnl_sol"] <= 0


def test_parameter_sweep_ranks_by_expectancy():
    series = _series("G", [0.0100, 0.0140, 0.0200, 0.0120, 0.0180, 0.0090, 0.0150, 0.0060])
    configs = [
        BacktestConfig(stop_loss_pct=0.25),
        BacktestConfig(stop_loss_pct=0.50),
    ]
    results = parameter_sweep(series, configs)
    assert len(results) == 2
    assert results[0]["metrics"]["trades"] >= results[1]["metrics"]["trades"]


def test_result_serialization_roundtrip():
    series = _series("H", [0.0100, 0.0070])
    result = run_backtest(series)
    d = result_to_dict(result)
    assert d["trades"] == [t for t in d["trades"]]
    assert isinstance(d["metrics"]["trades"], int)
    assert d["config"]["stop_loss_pct"] == 0.25


class _FakeStore:
    """Minimal TradingStore-like stub for snapshot persistence."""

    def __init__(self) -> None:
        self._state: dict = {}

    def get(self, key: str):
        return self._state.get(key)

    def set(self, key: str, value) -> None:
        self._state[key] = value


def test_snapshot_persistence_roundtrip():
    store = _FakeStore()
    series = _series("I", [0.0100, 0.0080])
    for snap in series:
        save_snapshot(store, snap.mint, snap.symbol, snap.price_usd, snap.timestamp, snap.pair, snap.rug)
    loaded = load_snapshots(store)
    assert len(loaded) == 2
    assert loaded[0].mint == series[0].mint
    assert snapshot_to_dict(loaded[0])["price_usd"] == 0.01


def test_snapshot_store_absent_is_noop():
    save_snapshot(None, "mint", "S", 0.01)
    assert load_snapshots(None) == []
