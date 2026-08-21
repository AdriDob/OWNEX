"""Market Regime Detection Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class RegimeInfo:
    """Market regime information."""

    regime: str  # "CHOP", "TREND_UP", "TREND_DOWN", "RANGE"
    reason: str


def detect_regime(
    price: float | None,
    vwap: float | None,
    vwap_slope: float | None,
    vwap_cross_count: int | None,
    volume_recent: float | None,
    volume_avg: float | None,
) -> RegimeInfo:
    """Detect market regime based on VWAP, volume, and price action."""
    if price is None or vwap is None or vwap_slope is None:
        return RegimeInfo(regime="CHOP", reason="missing_inputs")

    above_vwap = price > vwap

    # Low volume chop detection
    low_volume = False
    if volume_recent is not None and volume_avg is not None:
        low_volume = volume_recent < 0.6 * volume_avg

    if low_volume and abs((price - vwap) / vwap) < 0.001:
        return RegimeInfo(regime="CHOP", reason="low_volume_flat")

    # Trend detection
    if above_vwap and vwap_slope > 0:
        return RegimeInfo(regime="TREND_UP", reason="price_above_vwap_slope_up")

    if not above_vwap and vwap_slope < 0:
        return RegimeInfo(regime="TREND_DOWN", reason="price_below_vwap_slope_down")

    # Range detection via VWAP crosses
    if vwap_cross_count is not None and vwap_cross_count >= 3:
        return RegimeInfo(regime="RANGE", reason="frequent_vwap_cross")

    return RegimeInfo(regime="RANGE", reason="default")
