"""Tests for DeFi Yield Tracker and compound strategy."""

from __future__ import annotations

from core.defi import DefiPosition, DefiYieldTracker, YieldSnapshot
from core.defi.strategy import CompoundStrategy


def test_empty_tracker():
    t = DefiYieldTracker()
    assert t.list_positions() == []
    assert t.latest_snapshot() is None


def test_add_position():
    t = DefiYieldTracker()
    p = DefiPosition("AAVE V3", "ethereum", "USDC", 1000, 1000, 20.0, "lending")
    t.add_position(p)
    assert len(t.list_positions()) == 1
    assert t.list_positions()[0].protocol == "AAVE V3"


def test_add_multiple_positions():
    t = DefiYieldTracker()
    for _, (proto, apy) in enumerate([("A", 10), ("B", 20), ("C", 30)]):
        t.add_position(DefiPosition(proto, "eth", "USDC", 100, 100, apy, "lending"))
    assert len(t.list_positions()) == 3


def test_remove_position():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("Lido", "eth", "stETH", 1, 100, 15, "staking"))
    t.add_position(DefiPosition("AAVE", "eth", "USDC", 500, 500, 20, "lending"))
    assert t.remove_position("Lido", "stETH") is True
    assert len(t.list_positions()) == 1
    assert t.list_positions()[0].protocol == "AAVE"


def test_remove_nonexistent():
    t = DefiYieldTracker()
    assert t.remove_position("Fake", "fake") is False


def test_clear_positions():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("A", "eth", "USDC", 100, 100, 10, "lending"))
    t.add_position(DefiPosition("B", "eth", "USDC", 200, 200, 15, "lending"))
    t.clear_positions()
    assert t.list_positions() == []


def test_monthly_yield():
    p = DefiPosition("Test", "eth", "USDC", 1000, 1000, 12.0, "lending")
    expected = 1000 * (12.0 / 100 / 12)
    assert abs(p.monthly_yield - expected) < 0.01


def test_snapshot():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("A", "eth", "USDC", 500, 500, 12, "lending"))
    t.add_position(DefiPosition("B", "eth", "USDC", 1500, 1500, 24, "lending"))
    snap = t.snapshot()
    assert snap.total_value == 2000.0
    assert snap.position_count == 2
    assert snap.weighted_apy == (12 * 500 + 24 * 1500) / 2000


def test_snapshot_yield():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("A", "eth", "USDC", 1200, 1200, 12, "lending"))
    snap = t.snapshot()
    expected = 1200 * (12 / 100 / 12)
    assert abs(snap.total_monthly_yield - expected) < 0.01


def test_snapshot_to_dict():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("A", "eth", "USDC", 100, 100, 10, "lending"))
    d = t.snapshot().to_dict()
    assert "timestamp" in d
    assert d["total_value"] == 100.0
    assert d["position_count"] == 1
    assert len(d["positions"]) == 1


def test_summary():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("A", "eth", "USDC", 1000, 1000, 12, "lending"))
    s = t.summary()
    assert s["total_positions"] == 1
    assert s["total_value"] == 1000.0
    assert s["total_monthly_yield"] > 0
    assert len(s["positions"]) == 1


def test_summary_empty():
    t = DefiYieldTracker()
    s = t.summary()
    assert s["total_positions"] == 0
    assert s["total_value"] == 0.0


def test_publish_events_no_bus():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("A", "eth", "USDC", 100, 100, 12, "lending"))
    events = t.publish_yield_events()
    assert len(events) == 1
    assert events[0]["protocol"] == "A"
    assert events[0]["monthly_yield"] > 0


def test_apy_refresh_no_network():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("Aave", "ethereum", "USDC", 100, 100, 0, "lending"))
    # Should not crash — gracefully handles network error
    apys = t.refresh_apy_from_defillama(timeout=1)
    assert isinstance(apys, dict)


def test_snapshot_accumulates():
    t = DefiYieldTracker()
    t.add_position(DefiPosition("A", "eth", "USDC", 100, 100, 10, "lending"))
    t.snapshot()
    t.snapshot()
    t.snapshot()
    assert len(t._snapshots) == 3


def test_position_to_dict():
    p = DefiPosition(
        "Test",
        "eth",
        "USDC",
        500,
        500,
        15,
        "lending",
        pool_name="Test Pool",
        tokens=["USDC", "ETH"],
        link="https://test.com",
    )
    d = p.to_dict()
    assert d["protocol"] == "Test"
    assert d["monthly_yield"] == 6.25
    assert d["pool_name"] == "Test Pool"
    assert d["tokens"] == ["USDC", "ETH"]


# ── Strategy tests ─────────────────────────────────────────────


def test_tweet_default_strategy():
    s = CompoundStrategy.tweet_default()
    assert s.initial_capital == 3000.0
    assert s.months_to_target > 0
    assert s.total_after_5y > s.initial_capital
    assert len(s.projections) == 60


def test_custom_strategy():
    s = CompoundStrategy(
        initial_capital=10000,
        protocols=["a", "b"],
        apy_per_protocol=[10, 20],
        reinvest_rate=0.5,
        monthly_yield_target=500,
    )
    proj = s.project(months=12, monthly_contribution=500)
    assert len(proj.projections) == 12
    assert proj.total_after_5y > 0
    assert proj.initial_capital == 10000


def test_strategy_to_dict():
    s = CompoundStrategy.tweet_default()
    d = s.to_dict()
    assert d["initial_capital"] == 3000.0
    assert "months_to_target" in d
    assert "projections" in d
    assert len(d["projections"]) == 60


def test_strategy_zero_protocols():
    s = CompoundStrategy(initial_capital=1000, protocols=[], apy_per_protocol=[])
    proj = s.project(months=12)
    assert proj.months_to_target == 12
    assert proj.total_after_5y == 1000.0
    assert proj.weighted_apy == 0.0


def test_strategy_monthly_progression():
    s = CompoundStrategy(initial_capital=1000, protocols=["a"], apy_per_protocol=[12], reinvest_rate=1.0)
    proj = s.project(months=12)
    # Balance should increase each month (compounding)
    assert all(
        proj.projections[i]["total_balance"] >= proj.projections[i - 1]["total_balance"]
        for i in range(1, len(proj.projections))
    )


def test_strategy_with_contributions():
    s = CompoundStrategy(initial_capital=1000, protocols=["a"], apy_per_protocol=[12], reinvest_rate=1.0)
    proj = s.project(months=6, monthly_contribution=100)
    # Total should be higher with monthly contributions
    assert proj.projections[-1]["total_balance"] > 1100


def test_defi_position_monthly_yield_edge():
    p = DefiPosition("Zero", "eth", "USDC", 0, 0, 0, "lending")
    assert p.monthly_yield == 0.0


def test_yield_snapshot_empty():
    s = YieldSnapshot()
    assert s.total_value == 0.0
    assert s.total_monthly_yield == 0.0
    assert s.weighted_apy == 0.0
