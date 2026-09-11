"""Exit engine for memecoin paper/live positions (v1). Pure functions.

Priority order per evaluation: stop-loss > take-profit tier > trailing stop >
time stop > hold. Fractions allow staged exits (e.g. sell half at +50%).
All thresholds are fractions of entry (0.25 = 25%).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ExitConfig:
    stop_loss_pct: float = 0.25  # exit fully at -25%
    take_profit_tiers: tuple[tuple[float, float], ...] = ((0.5, 0.5), (1.0, 0.3), (2.0, 0.2))
    trailing_pct: float = 0.20  # exit fully at -20% from peak
    max_hold_minutes: float = 120.0


@dataclass(frozen=True, slots=True)
class ExitDecision:
    action: str  # hold | stop_loss | take_profit | trailing_stop | time_stop
    sell_pct: float  # 0-100 of remaining position
    reason: str
    new_high: float  # updated peak price to persist


def evaluate_exit(
    entry_price: float,
    peak_price: float,
    current_price: float,
    age_minutes: float,
    config: ExitConfig | None = None,
) -> ExitDecision:
    """Decide exit action for one position snapshot. Never raises on bad input."""
    cfg = config or ExitConfig()
    try:
        entry = float(entry_price)
        peak = max(float(peak_price), entry)
        price = float(current_price)
        age = max(0.0, float(age_minutes))
    except (TypeError, ValueError):
        return ExitDecision("hold", 0.0, "invalid price input (fail safe)", float(peak_price or 0))
    if entry <= 0 or price <= 0:
        return ExitDecision("hold", 0.0, "non-positive price (fail safe)", peak)

    new_high = max(peak, price)
    ret = (price - entry) / entry

    if ret <= -abs(cfg.stop_loss_pct):
        return ExitDecision("stop_loss", 100.0, f"stop-loss at {ret:.1%}", new_high)
    for tier_gain, tier_pct in sorted(cfg.take_profit_tiers):
        if ret >= tier_gain:
            return ExitDecision("take_profit", float(tier_pct * 100.0), f"take-profit tier +{tier_gain:.0%}", new_high)
    drawdown = (new_high - price) / new_high if new_high > 0 else 0.0
    if drawdown >= abs(cfg.trailing_pct):
        return ExitDecision("trailing_stop", 100.0, f"trailing stop {drawdown:.1%} off peak", new_high)
    if age >= cfg.max_hold_minutes:
        return ExitDecision("time_stop", 100.0, f"max hold {cfg.max_hold_minutes:.0f}m reached", new_high)
    return ExitDecision("hold", 0.0, f"within bands ({ret:+.1%})", new_high)


def summarize_decision(decision: ExitDecision) -> dict[str, Any]:
    return {
        "action": decision.action,
        "sell_pct": decision.sell_pct,
        "reason": decision.reason,
        "new_high": decision.new_high,
    }
