"""MACD (Moving Average Convergence Divergence) Indicator."""

from __future__ import annotations

from typing import Any

from core.polymarket.btc_latency_arb.indicators.rsi import ema


def compute_macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, float] | None:
    """Compute MACD line, signal line, histogram, and histogram delta."""
    if not closes or len(closes) < slow + signal:
        return None

    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)

    if fast_ema is None or slow_ema is None:
        return None

    macd_line = fast_ema - slow_ema

    # Build MACD series for signal line
    macd_series = []
    for i in range(len(closes)):
        sub = closes[: i + 1]
        f = ema(sub, fast)
        s = ema(sub, slow)
        if f is not None and s is not None:
            macd_series.append(f - s)

    signal_line = ema(macd_series, signal)
    if signal_line is None:
        return None

    hist = macd_line - signal_line

    # Compute previous histogram for delta
    prev_hist = None
    if len(macd_series) >= signal + 1:
        # Get MACD series without last element
        prev_macd_series = macd_series[:-1]
        prev_signal = ema(prev_macd_series, signal)
        if prev_signal is not None:
            prev_macd = prev_macd_series[-1]
            prev_hist = prev_macd - prev_signal

    hist_delta = None
    if prev_hist is not None:
        hist_delta = hist - prev_hist

    return {
        "macd": macd_line,
        "signal": signal_line,
        "hist": hist,
        "hist_delta": hist_delta,
    }
