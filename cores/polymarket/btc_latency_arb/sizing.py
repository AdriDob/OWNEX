"""Position Sizing for Polymarket BTC Latency Arb."""

from __future__ import annotations

import logging
from typing import Any

from core.polymarket.btc_latency_arb.config import BTCArbConfig, SizingConfig

logger = logging.getLogger("orion.polymarket.btc_latency_arb.sizing")


class PositionSizer:
    """Position sizing calculator."""

    def __init__(self, config: SizingConfig) -> None:
        self.config = config
        self._trade_history: list[dict[str, Any]] = []

    def calculate_size(
        self,
        capital: float,
        win_rate: float = 0.55,
        avg_win: float = 0.02,
        avg_loss: float = 0.015,
        edge: float = 0.10,
    ) -> float:
        """Calculate position size based on configured method."""
        if self.config.method == "kelly":
            return self._kelly_size(capital, win_rate, avg_win, avg_loss, edge)
        elif self.config.method == "fixed_fractional":
            return self._fixed_fractional_size(capital)
        elif self.config.method == "fixed_usd":
            return self._fixed_usd_size()
        else:
            return self._fixed_fractional_size(capital)

    def _kelly_size(
        self,
        capital: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        edge: float,
    ) -> float:
        """Kelly criterion position sizing."""
        if win_rate <= 0.5 or avg_loss <= 0:
            return self.config.fixed_usd

        # Kelly formula: f = (p * b - q) / b
        # where p = win_rate, b = avg_win/avg_loss, q = 1-p
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p

        kelly_f = (p * b - q) / b

        # Apply Kelly fraction (conservative)
        kelly_f *= self.config.kelly_fraction

        # Cap at reasonable maximum
        kelly_f = min(kelly_f, 0.10)  # Max 10% of capital

        size = capital * kelly_f
        return max(self.config.fixed_usd, size)

    def _fixed_fractional_size(self, capital: float) -> float:
        """Fixed fractional position sizing."""
        size = capital * self.config.fixed_fraction_pct
        return max(self.config.fixed_usd, size)

    def _fixed_usd_size(self) -> float:
        """Fixed USD position sizing."""
        return self.config.fixed_usd

    def update_trade_history(self, trade: dict[str, Any]) -> None:
        """Update trade history for win rate calculation."""
        self._trade_history.append(trade)
        # Keep last 100 trades
        if len(self._trade_history) > 100:
            self._trade_history = self._trade_history[-100:]

    def get_estimated_win_rate(self) -> float:
        """Estimate win rate from history."""
        if not self._trade_history:
            return 0.55  # Default assumption

        wins = sum(1 for t in self._trade_history if t.get("pnl_usd", 0) > 0)
        return wins / len(self._trade_history)

    def get_avg_win_loss(self) -> tuple[float, float]:
        """Get average win and loss from history."""
        if not self._trade_history:
            return 0.02, 0.015  # Defaults

        wins = [t.get("pnl_pct", 0) for t in self._trade_history if t.get("pnl_usd", 0) > 0]
        losses = [abs(t.get("pnl_pct", 0)) for t in self._trade_history if t.get("pnl_usd", 0) < 0]

        avg_win = sum(wins) / len(wins) if wins else 0.02
        avg_loss = sum(losses) / len(losses) if losses else 0.015

        return avg_win / 100.0, avg_loss / 100.0  # Convert from pct

    def get_optimal_size(
        self,
        capital: float,
        signal_strength: str = "OPTIONAL",
    ) -> float:
        """Get optimal position size for current signal."""
        base_size = self.calculate_size(capital)

        # Adjust by signal strength
        if signal_strength == "STRONG":
            multiplier = 1.5
        elif signal_strength == "GOOD":
            multiplier = 1.2
        else:  # OPTIONAL
            multiplier = 1.0

        return base_size * multiplier
