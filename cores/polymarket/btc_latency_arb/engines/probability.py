"""Direction Scoring & Time Awareness Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.polymarket.btc_latency_arb.indicators.rsi import clamp


@dataclass(slots=True)
class ScoredDirection:
    """Scored direction with raw probability."""

    up_score: float
    down_score: float
    raw_up: float  # 0-1 probability


def score_direction(inputs: dict[str, Any]) -> ScoredDirection:
    """Score UP vs DOWN direction based on technical indicators.

    Returns raw probability (0-1) for UP direction.
    """
    price = inputs.get("price")
    vwap = inputs.get("vwap")
    vwap_slope = inputs.get("vwap_slope")
    rsi = inputs.get("rsi")
    rsi_slope = inputs.get("rsi_slope")
    macd = inputs.get("macd")
    heiken_color = inputs.get("heiken_color")
    heiken_count = inputs.get("heiken_count", 0)
    failed_vwap_reclaim = inputs.get("failed_vwap_reclaim", False)

    up = 1.0
    down = 1.0

    # Price vs VWAP
    if price is not None and vwap is not None:
        if price > vwap:
            up += 2.0
        if price < vwap:
            down += 2.0

    # VWAP slope
    if vwap_slope is not None:
        if vwap_slope > 0:
            up += 2.0
        if vwap_slope < 0:
            down += 2.0

    # RSI + slope
    if rsi is not None and rsi_slope is not None:
        if rsi > 55.0 and rsi_slope > 0:
            up += 2.0
        if rsi < 45.0 and rsi_slope < 0:
            down += 2.0

    # MACD histogram + delta
    if macd is not None:
        macd_hist = macd.get("hist")
        macd_hist_delta = macd.get("hist_delta")

        if macd_hist is not None and macd_hist_delta is not None:
            expanding_green = macd_hist > 0 and macd_hist_delta > 0
            expanding_red = macd_hist < 0 and macd_hist_delta < 0
            if expanding_green:
                up += 2.0
            if expanding_red:
                down += 2.0

        if macd.get("macd") is not None:
            if macd["macd"] > 0:
                up += 1.0
            if macd["macd"] < 0:
                down += 1.0

    # Heiken Ashi
    if heiken_color:
        if heiken_color == "green" and heiken_count >= 2:
            up += 1.0
        if heiken_color == "red" and heiken_count >= 2:
            down += 1.0

    # Failed VWAP reclaim (bearish)
    if failed_vwap_reclaim:
        down += 3.0

    raw_up = up / (up + down)
    return ScoredDirection(up_score=up, down_score=down, raw_up=raw_up)


def apply_time_awareness(raw_up: float, remaining_minutes: float | None, window_minutes: int = 15) -> dict[str, float]:
    """Apply time decay to raw probability as expiry approaches.

    Time decay reduces confidence near expiry.
    """
    if remaining_minutes is None or remaining_minutes <= 0:
        time_decay = 0.0
    else:
        time_decay = clamp(remaining_minutes / window_minutes, 0.0, 1.0)

    # Shrink towards 0.5 (neutral) as time runs out
    adjusted_up = clamp(0.5 + (raw_up - 0.5) * time_decay, 0.0, 1.0)

    return {
        "time_decay": time_decay,
        "adjusted_up": adjusted_up,
        "adjusted_down": 1.0 - adjusted_up,
    }
