"""Risk Management for Polymarket BTC Latency Arb."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.polymarket.btc_latency_arb.config import RiskConfig

logger = logging.getLogger("orion.polymarket.btc_latency_arb.risk")


@dataclass(slots=True)
class RiskCheck:
    """Result of a risk check."""

    allowed: bool
    reason: str
    metadata: dict[str, Any] = None


class RiskManager:
    """Risk management for the latency arbitrage bot."""

    def __init__(self, config: RiskConfig) -> None:
        self.config = config
        self._consecutive_losses = 0
        self._daily_pnl = 0.0
        self._day_start = 0.0
        self._paused = False
        self._pause_reason = ""

    def check_pre_trade(
        self,
        signal_strength: str,
        position_size_usd: float,
        current_capital: float,
        open_positions: int,
        daily_pnl: float,
    ) -> RiskCheck:
        """Check if a trade should be allowed."""
        # Check global pause
        if self._paused:
            return RiskCheck(False, f"Bot paused: {self._pause_reason}")

        # Check daily loss limit
        if daily_pnl <= -self.config.max_daily_loss_usd:
            self._pause_bot(f"Daily loss limit reached: ${daily_pnl:.2f}")
            return RiskCheck(False, f"Daily loss limit reached: ${daily_pnl:.2f}")

        # Check max concurrent positions
        if open_positions >= self.config.max_concurrent_positions:
            return RiskCheck(False, f"Max positions ({self.config.max_concurrent_positions}) reached")

        # Check position size limits
        max_position = current_capital * self.config.max_position_pct
        if position_size_usd > max_position:
            return RiskCheck(False, f"Position size ${position_size_usd:.2f} exceeds max ${max_position:.2f}")

        # Check consecutive losses
        if self._consecutive_losses >= self.config.max_consecutive_losses:
            self._pause_bot(f"Max consecutive losses ({self.config.max_consecutive_losses}) reached")
            return RiskCheck(False, "Max consecutive losses reached")

        # Check drawdown
        if current_capital > 0:
            drawdown_pct = abs(daily_pnl) / current_capital
            if drawdown_pct >= self.config.drawdown_pause_pct:
                self._pause_bot(f"Drawdown limit reached: {drawdown_pct:.1%}")
                return RiskCheck(False, f"Drawdown limit reached: {drawdown_pct:.1%}")

        return RiskCheck(True, "OK")

    def record_trade_result(self, pnl_usd: float) -> None:
        """Record trade result for risk tracking."""
        self._daily_pnl += pnl_usd

        if pnl_usd < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        logger.debug("Risk: daily_pnl=%.2f, consecutive_losses=%d", self._daily_pnl, self._consecutive_losses)

    def reset_daily(self) -> None:
        """Reset daily counters (call at day boundary)."""
        self._daily_pnl = 0.0
        # Don't reset consecutive losses - they persist

    def _pause_bot(self, reason: str) -> None:
        """Pause the bot."""
        self._paused = True
        self._pause_reason = reason
        logger.warning("BTC Latency Arb PAUSED: %s", reason)

    def resume(self) -> None:
        """Resume the bot."""
        self._paused = False
        self._pause_reason = ""
        logger.info("BTC Latency Arb RESUMED")

    def is_paused(self) -> bool:
        return self._paused

    def get_status(self) -> dict[str, Any]:
        return {
            "paused": self._paused,
            "pause_reason": self._pause_reason,
            "daily_pnl": self._daily_pnl,
            "consecutive_losses": self._consecutive_losses,
            "max_daily_loss_usd": self.config.max_daily_loss_usd,
            "max_concurrent_positions": self.config.max_concurrent_positions,
            "max_consecutive_losses": self.config.max_consecutive_losses,
            "drawdown_pause_pct": self.config.drawdown_pause_pct,
        }
