"""Memecoin strategy v1 — filters + exits (pure, no network)."""

from __future__ import annotations

from cores.trading.strategies.memecoin_exits import ExitConfig, evaluate_exit
from cores.trading.strategies.memecoin_filters import evaluate_pair

NOW_MS = 1_757_000_000_000


def good_pair(**overrides):
    base = {
        "mint": "MintAAA",
        "symbol": "AAA",
        "liquidity_usd": 50_000,
        "volume_h24": 80_000,
        "price_usd": "0.001",
        "pair_created_at": NOW_MS - 60 * 60_000,
        "boosts_active": 0,
    }
    base.update(overrides)
    return base


def clean_rug(**overrides):
    base = {
        "holder_count": 300,
        "top_10_pct": 12.0,
        "liquidity_locked": True,
        "mint_disabled": True,
        "freeze_disabled": True,
        "score": 12,
        "risks": [],
    }
    base.update(overrides)
    return base


class TestFilters:
    def test_clean_pair_passes(self):
        v = evaluate_pair(good_pair(), clean_rug(), now_ms=NOW_MS)
        assert v.passed is True
        assert v.reasons == ()

    def test_low_liquidity_fails(self):
        v = evaluate_pair(good_pair(liquidity_usd=100.0), clean_rug(), now_ms=NOW_MS)
        assert v.passed is False
        assert any("liquidity" in r for r in v.reasons)

    def test_mint_authority_fails(self):
        v = evaluate_pair(good_pair(), clean_rug(mint_disabled=False), now_ms=NOW_MS)
        assert v.passed is False
        assert any("mint authority" in r for r in v.reasons)

    def test_unlocked_liquidity_fails(self):
        v = evaluate_pair(good_pair(), clean_rug(liquidity_locked=False), now_ms=NOW_MS)
        assert v.passed is False

    def test_concentrated_holders_fail(self):
        v = evaluate_pair(good_pair(), clean_rug(top_10_pct=80.0), now_ms=NOW_MS)
        assert v.passed is False

    def test_danger_risk_fails_warn_warns(self):
        rug = clean_rug(risks=[{"name": "copycat", "level": "warn"}, {"name": "honeypot", "level": "danger"}])
        v = evaluate_pair(good_pair(), rug, now_ms=NOW_MS)
        assert v.passed is False
        assert any("danger" in r for r in v.reasons)
        rug2 = clean_rug(risks=[{"name": "copycat", "level": "warn"}])
        v2 = evaluate_pair(good_pair(), rug2, now_ms=NOW_MS)
        assert v2.passed is True
        assert any("warn" in w for w in v2.warnings)

    def test_missing_rug_fails_closed(self):
        v = evaluate_pair(good_pair(), None, now_ms=NOW_MS)
        assert v.passed is False

    def test_fresh_pair_fails_snipe_window(self):
        v = evaluate_pair(good_pair(pair_created_at=NOW_MS - 60_000), clean_rug(), now_ms=NOW_MS)
        assert v.passed is False
        assert any("snipe" in r for r in v.reasons)

    def test_score_travels_as_info_not_threshold(self):
        v = evaluate_pair(good_pair(), clean_rug(score=9999), now_ms=NOW_MS)
        assert v.passed is True
        assert v.info["rug_score"] == 9999


class TestExits:
    def test_hold_inside_bands(self):
        d = evaluate_exit(1.0, 1.0, 1.1, 10.0)
        assert d.action == "hold" and d.sell_pct == 0.0 and d.new_high == 1.1

    def test_stop_loss(self):
        d = evaluate_exit(1.0, 1.0, 0.70, 10.0)
        assert d.action == "stop_loss" and d.sell_pct == 100.0

    def test_take_profit_first_tier(self):
        d = evaluate_exit(1.0, 1.2, 1.6, 10.0)
        assert d.action == "take_profit" and d.sell_pct == 50.0

    def test_trailing_stop(self):
        d = evaluate_exit(1.0, 2.0, 1.4, 10.0)  # +40% (under TP tier), -30% off peak
        assert d.action == "trailing_stop" and d.sell_pct == 100.0

    def test_time_stop(self):
        d = evaluate_exit(1.0, 1.05, 1.05, 180.0)
        assert d.action == "time_stop"

    def test_priority_stop_beats_time(self):
        d = evaluate_exit(1.0, 1.0, 0.5, 999.0)
        assert d.action == "stop_loss"

    def test_bad_input_holds_safe(self):
        d = evaluate_exit(0.0, 0.0, 0.0, 0.0)
        assert d.action == "hold"
        d2 = evaluate_exit("x", 1.0, 1.0, 1.0)  # type: ignore[arg-type]
        assert d2.action == "hold"

    def test_custom_config(self):
        cfg = ExitConfig(stop_loss_pct=0.1, take_profit_tiers=((1.0, 100.0),), trailing_pct=0.5, max_hold_minutes=60)
        assert evaluate_exit(1.0, 1.0, 0.85, 5.0, cfg).action == "stop_loss"
