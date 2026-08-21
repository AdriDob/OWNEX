"""VWAP (Volume Weighted Average Price) Indicators."""

from __future__ import annotations

from typing import Any


def compute_session_vwap(candles: list[dict[str, Any]]) -> float | None:
    """Compute session VWAP from candles.

    VWAP = sum(close * volume) / sum(volume) where close is typical price (H+L+C)/3
    """
    if not candles:
        return None

    pv = 0.0
    v = 0.0
    for c in candles:
        high = c.get("high", 0.0)
        low = c.get("low", 0.0)
        close = c.get("close", 0.0)
        volume = c.get("volume", 0.0)

        tp = (high + low + close) / 3.0
        pv += tp * volume
        v += volume

    if v == 0:
        return None
    return pv / v


def compute_vwap_series(candles: list[dict[str, Any]]) -> list[float]:
    """Compute cumulative VWAP series."""
    series = []
    for i in range(len(candles)):
        sub = candles[: i + 1]
        vwap = compute_session_vwap(sub)
        series.append(vwap if vwap is not None else 0.0)
    return series


def compute_vwap_slope(vwap_series: list[float], lookback: int = 5) -> float | None:
    """Compute VWAP slope over lookback periods."""
    if len(vwap_series) < lookback:
        return None
    recent = vwap_series[-lookback:]
    first = recent[0]
    last = recent[-1]
    return (last - first) / (lookback - 1)


def compute_vwap_distance(price: float, vwap: float) -> float | None:
    """Compute price distance from VWAP as percentage."""
    if vwap == 0:
        return None
    return (price - vwap) / vwap


def count_vwap_crosses(closes: list[float], vwap_series: list[float], lookback: int = 20) -> int | None:
    """Count VWAP crosses in recent lookback."""
    if len(closes) < lookback or len(vwap_series) < lookback:
        return None

    crosses = 0
    for i in range(len(closes) - lookback + 1, len(closes)):
        prev = closes[i - 1] - vwap_series[i - 1]
        cur = closes[i] - vwap_series[i]
        if prev == 0:
            continue
        if (prev > 0 and cur < 0) or (prev < 0 and cur > 0):
            crosses += 1
    return crosses
