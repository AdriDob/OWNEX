"""Polymarket Health Monitor — PnL tracking, strategy health, alerts.

Tracks:
- Realized and unrealized PnL
- Win/loss ratio
- Strategy performance
- Risk metrics
- System health
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("orion.polymarket.health")


@dataclass
class Position:
    """A trading position."""

    market_id: str
    token_id: str
    outcome: str
    entry_price: float
    size_usd: float
    entry_time: float
    current_price: float = 0.0
    exit_price: float | None = None
    exit_time: float | None = None
    pnl: float = 0.0
    status: str = "open"  # open, closed, resolved

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized PnL."""
        if self.status != "open":
            return 0.0
        return (self.current_price - self.entry_price) * (self.size_usd / self.entry_price)

    @property
    def holding_time(self) -> float:
        """Holding time in seconds."""
        end = self.exit_time or time.time()
        return end - self.entry_time


@dataclass
class TradeRecord:
    """A completed trade."""

    market_id: str
    outcome: str
    entry_price: float
    exit_price: float
    size_usd: float
    pnl: float
    entry_time: float
    exit_time: float
    strategy: str
    notes: str = ""


class HealthMonitor:
    """Health monitor for Polymarket strategies.

    Tracks PnL, win rate, and system health across all strategies.
    """

    def __init__(self) -> None:
        self._positions: dict[str, Position] = {}
        self._trades: list[TradeRecord] = []
        self._start_time = time.time()
        self._peak_pnl: float = 0.0
        self._max_drawdown: float = 0.0
        self._alerts: list[dict[str, Any]] = []

    # ── Position Management ────────────────────────────────────────────

    def open_position(
        self,
        market_id: str,
        token_id: str,
        outcome: str,
        entry_price: float,
        size_usd: float,
        strategy: str = "",
    ) -> Position:
        """Record a new position."""
        pos = Position(
            market_id=market_id,
            token_id=token_id,
            outcome=outcome,
            entry_price=entry_price,
            size_usd=size_usd,
            entry_time=time.time(),
            current_price=entry_price,
        )
        self._positions[market_id] = pos
        logger.info(
            "Position opened: %s @ $%.4f, size $%.2f",
            outcome,
            entry_price,
            size_usd,
        )
        return pos

    def close_position(
        self,
        market_id: str,
        exit_price: float,
        notes: str = "",
    ) -> TradeRecord | None:
        """Close a position and record the trade."""
        pos = self._positions.get(market_id)
        if not pos:
            logger.warning("No open position for market %s", market_id)
            return None

        # Calculate PnL
        pnl = (exit_price - pos.entry_price) * (pos.size_usd / pos.entry_price)

        # Create trade record
        trade = TradeRecord(
            market_id=market_id,
            outcome=pos.outcome,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            size_usd=pos.size_usd,
            pnl=pnl,
            entry_time=pos.entry_time,
            exit_time=time.time(),
            strategy="sweeper",
            notes=notes,
        )
        self._trades.append(trade)

        # Update position
        pos.exit_price = exit_price
        pos.exit_time = time.time()
        pos.pnl = pnl
        pos.status = "closed"

        # Remove from active positions
        del self._positions[market_id]

        logger.info("Position closed: %s, PnL: $%.4f", pos.outcome, pnl)
        return trade

    def update_position_price(self, market_id: str, current_price: float) -> None:
        """Update the current price of a position."""
        pos = self._positions.get(market_id)
        if pos:
            pos.current_price = current_price

    # ── PnL Calculations ──────────────────────────────────────────────

    def get_realized_pnl(self) -> float:
        """Get total realized PnL from closed trades."""
        return sum(t.pnl for t in self._trades)

    def get_unrealized_pnl(self) -> float:
        """Get total unrealized PnL from open positions."""
        return sum(pos.unrealized_pnl for pos in self._positions.values())

    def get_total_pnl(self) -> float:
        """Get total PnL (realized + unrealized)."""
        return self.get_realized_pnl() + self.get_unrealized_pnl()

    def get_win_rate(self) -> float:
        """Get win rate (0.0 to 1.0)."""
        if not self._trades:
            return 0.0
        wins = sum(1 for t in self._trades if t.pnl > 0)
        return wins / len(self._trades)

    def get_max_drawdown(self) -> float:
        """Get maximum drawdown."""
        return self._max_drawdown

    def _update_peak_and_drawdown(self) -> None:
        """Update peak PnL and max drawdown."""
        total = self.get_total_pnl()
        if total > self._peak_pnl:
            self._peak_pnl = total
        drawdown = self._peak_pnl - total
        if drawdown > self._max_drawdown:
            self._max_drawdown = drawdown

    # ── Risk Metrics ───────────────────────────────────────────────────

    def get_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio (simplified)."""
        if not self._trades:
            return 0.0

        returns = [t.pnl / t.size_usd for t in self._trades]
        if not returns:
            return 0.0

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance**0.5

        if std_dev == 0:
            return 0.0

        return (avg_return - risk_free_rate) / std_dev

    def get_profit_factor(self) -> float:
        """Calculate profit factor (gross profits / gross losses)."""
        gross_profit = sum(t.pnl for t in self._trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self._trades if t.pnl < 0))

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    # ── Alerts ─────────────────────────────────────────────────────────

    def add_alert(self, level: str, message: str) -> None:
        """Add a health alert."""
        alert = {
            "level": level,
            "message": message,
            "timestamp": time.time(),
        }
        self._alerts.append(alert)
        logger.log(
            logging.WARNING if level == "warning" else logging.INFO,
            "Alert: %s",
            message,
        )

    def get_alerts(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent alerts."""
        return self._alerts[-limit:]

    # ── Summary ────────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Get comprehensive health summary."""
        self._update_peak_and_drawdown()

        uptime = time.time() - self._start_time

        return {
            "uptime_seconds": round(uptime),
            "uptime_human": self._format_uptime(uptime),
            "pnl": {
                "realized": round(self.get_realized_pnl(), 4),
                "unrealized": round(self.get_unrealized_pnl(), 4),
                "total": round(self.get_total_pnl(), 4),
                "peak": round(self._peak_pnl, 4),
                "max_drawdown": round(self._max_drawdown, 4),
            },
            "trades": {
                "total": len(self._trades),
                "wins": sum(1 for t in self._trades if t.pnl > 0),
                "losses": sum(1 for t in self._trades if t.pnl < 0),
                "win_rate": f"{self.get_win_rate():.1%}",
                "avg_pnl": round(sum(t.pnl for t in self._trades) / len(self._trades), 4) if self._trades else 0.0,
            },
            "risk": {
                "sharpe_ratio": round(self.get_sharpe_ratio(), 2),
                "profit_factor": round(self.get_profit_factor(), 2),
            },
            "positions": {
                "open": len(self._positions),
                "total_exposure": round(sum(p.size_usd for p in self._positions.values()), 2),
            },
            "alerts": len(self._alerts),
            "recent_alerts": self.get_alerts(5),
        }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime as human-readable string."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"


# ── Singleton ─────────────────────────────────────────────────────────────

_monitor: HealthMonitor | None = None


def get_health_monitor() -> HealthMonitor:
    """Get or create the singleton health monitor."""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor
