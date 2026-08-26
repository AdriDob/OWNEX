"""RSI (Relative Strength Index) and Moving Average Indicators."""

from __future__ import annotations


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Compute RSI from closing prices."""
    if not closes or len(closes) < period + 1:
        return None

    gains = 0.0
    losses = 0.0
    for i in range(len(closes) - period, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        diff = cur - prev
        if diff > 0:
            gains += diff
        else:
            losses += -diff

    avg_gain = gains / period
    avg_loss = losses / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return clamp(rsi, 0.0, 100.0)


def sma(values: list[float], period: int) -> float | None:
    """Simple Moving Average."""
    if not values or len(values) < period:
        return None
    slice_vals = values[-period:]
    return sum(slice_vals) / period


def ema(values: list[float], period: int) -> float | None:
    """Exponential Moving Average."""
    if not values or len(values) < period:
        return None

    k = 2.0 / (period + 1.0)
    prev_ema = values[0]
    for i in range(1, len(values)):
        prev_ema = values[i] * k + prev_ema * (1.0 - k)
    return prev_ema


def slope_last(values: list[float], points: int = 3) -> float | None:
    """Compute slope of last N points."""
    if not values or len(values) < points:
        return None
    slice_vals = values[-points:]
    first = slice_vals[0]
    last = slice_vals[-1]
    return (last - first) / (points - 1)


def compute_rsi_series(closes: list[float], period: int = 14) -> list[float]:
    """Compute RSI for each point in series."""
    rsi_series = []
    for i in range(len(closes)):
        sub = closes[: i + 1]
        rsi = compute_rsi(sub, period)
        rsi_series.append(rsi if rsi is not None else 50.0)
    return rsi_series
