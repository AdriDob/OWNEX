"""Heiken Ashi Candles Indicator."""

from __future__ import annotations

from typing import Any


def compute_heiken_ashi(candles: list[dict[str, Any]]) -> list[dict[str, float]]:
    """Compute Heiken Ashi candles from regular candles."""
    if not candles:
        return []

    ha_candles = []
    prev_ha_open = None
    prev_ha_close = None

    for i, c in enumerate(candles):
        open_p = c.get("open", 0.0)
        high = c.get("high", 0.0)
        low = c.get("low", 0.0)
        close = c.get("close", 0.0)

        if i == 0:
            ha_open = (open_p + close) / 2.0
        else:
            ha_open = (prev_ha_open + prev_ha_close) / 2.0

        ha_close = (open_p + high + low + close) / 4.0
        ha_high = max(high, ha_open, ha_close)
        ha_low = min(low, ha_open, ha_close)

        ha_candles.append(
            {
                "open": ha_open,
                "high": ha_high,
                "low": ha_low,
                "close": ha_close,
                "color": "green" if ha_close >= ha_open else "red",
            }
        )

        prev_ha_open = ha_open
        prev_ha_close = ha_close

    return ha_candles


def count_consecutive(ha_candles: list[dict[str, float]]) -> dict[str, Any]:
    """Count consecutive same-color Heiken Ashi candles."""
    if not ha_candles:
        return {"color": None, "count": 0}

    last_color = ha_candles[-1].get("color")
    count = 0

    for c in reversed(ha_candles):
        if c.get("color") == last_color:
            count += 1
        else:
            break

    return {"color": last_color, "count": count}
