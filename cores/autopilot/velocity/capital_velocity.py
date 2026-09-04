"""Capital Velocity - Tracks net capital growth rate and ETA to targets."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CapitalVelocityData:
    """Capital velocity metrics."""

    income_today: float = 0.0
    saved_today: float = 0.0
    invested_today: float = 0.0
    portfolio_return_today: float = 0.0
    trading_pnl_today: float = 0.0
    dividends_today: float = 0.0
    net_capital_added: float = 0.0
    target_500k_pct: float = 0.0
    eta_500k_months: float = 0.0
    velocity_trend: str = "stable"  # accelerating, stable, decelerating
    last_updated: datetime = field(default_factory=datetime.utcnow)


class CapitalVelocity:
    """
    Tracks capital velocity - the rate at which net worth grows.

    Key metrics:
    - Net capital added per day/week/month
    - Progress toward $500k target
    - ETA to $500k based on current velocity
    - Trend analysis (accelerating/stable/decelerating)
    """

    def __init__(self, config: Any):
        self.config = config
        self._velocity = CapitalVelocityData()
        self._history: list[dict[str, Any]] = []
        self._storage_path = Path.home() / ".ownex" / "capital_velocity.json"
        self._initialized = False

    async def initialize(self) -> None:
        """Load historical data."""
        await self._load()
        self._initialized = True
        logger.info("CapitalVelocity initialized")

    async def update(self) -> CapitalVelocityData:
        """Update velocity metrics from all sources."""
        # This would integrate with actual system metrics:
        # - Income from WorkBank/RevenueTracker
        # - Savings from budget tracking
        # - Investment returns from CapitalEngine
        # - Trading PnL from QuantEngine
        # - Dividends from portfolio

        # For now, return current state
        self._velocity.last_updated = datetime.utcnow()

        # Save history point
        self._save_history_point()

        # Analyze trend
        self._analyze_trend()

        return self._velocity

    def get_velocity(self) -> dict[str, Any]:
        """Get current velocity metrics for dashboard."""
        return {
            "income_today": self._velocity.income_today,
            "saved_today": self._velocity.saved_today,
            "invested_today": self._velocity.invested_today,
            "portfolio_return_today": self._velocity.portfolio_return_today,
            "trading_pnl_today": self._velocity.trading_pnl_today,
            "dividends_today": self._velocity.dividends_today,
            "net_capital_added": self._velocity.net_capital_added,
            "target_500k_pct": self._velocity.target_500k_pct,
            "eta_500k_months": round(self._velocity.eta_500k_months, 1),
            "velocity_trend": self._velocity.velocity_trend,
            "last_updated": self._velocity.last_updated.isoformat(),
        }

    async def record_income(self, amount: float, source: str) -> None:
        """Record new income."""
        self._velocity.income_today += amount
        await self._save()

    async def record_savings(self, amount: float) -> None:
        self._velocity.saved_today += amount
        await self._save()

    async def record_investment(self, amount: float) -> None:
        self._velocity.invested_today += amount
        await self._save()

    async def record_portfolio_return(self, amount: float) -> None:
        self._velocity.portfolio_return_today += amount
        await self._save()

    async def record_trading_pnl(self, amount: float) -> None:
        self._velocity.trading_pnl_today += amount
        await self._save()

    async def record_dividends(self, amount: float) -> None:
        self._velocity.dividends_today += amount
        await self._save()

    def _recalculate_net_capital(self) -> None:
        """Recalculate net capital added."""
        self._velocity.net_capital_added = (
            self._velocity.saved_today
            + self._velocity.invested_today
            + self._velocity.portfolio_return_today
            + self._velocity.trading_pnl_today
            + self._velocity.dividends_today
        )

        # Update target progress
        # This would need actual net worth - for now use a placeholder
        current_net_worth = 315_000  # Placeholder
        self._velocity.target_500k_pct = (current_net_worth / 500_000) * 100

        # Calculate ETA
        daily_velocity = self._velocity.net_capital_added
        if daily_velocity > 0:
            remaining = 500_000 - current_net_worth
            self._velocity.eta_500k_months = remaining / (daily_velocity * 30)
        else:
            self._velocity.eta_500k_months = 0

    def _analyze_trend(self) -> None:
        """Analyze velocity trend from history."""
        if len(self._history) < 7:
            self._velocity.velocity_trend = "stable"
            return

        # Get last 7 days of net capital added
        recent = [h.get("net_capital_added", 0) for h in self._history[-7:]]
        older = [h.get("net_capital_added", 0) for h in self._history[-14:-7]] if len(self._history) >= 14 else []

        if not older:
            self._velocity.velocity_trend = "stable"
            return

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older) if older else recent_avg

        if recent_avg > older_avg * 1.1:
            self._velocity.velocity_trend = "accelerating"
        elif recent_avg < older_avg * 0.9:
            self._velocity.velocity_trend = "decelerating"
        else:
            self._velocity.velocity_trend = "stable"

    def _save_history_point(self) -> None:
        """Save current velocity as history point."""
        point = {
            "timestamp": datetime.utcnow().isoformat(),
            "income_today": self._velocity.income_today,
            "saved_today": self._velocity.saved_today,
            "invested_today": self._velocity.invested_today,
            "portfolio_return_today": self._velocity.portfolio_return_today,
            "trading_pnl_today": self._velocity.trading_pnl_today,
            "dividends_today": self._velocity.dividends_today,
            "net_capital_added": self._velocity.net_capital_added,
            "target_500k_pct": self._velocity.target_500k_pct,
            "eta_500k_months": self._velocity.eta_500k_months,
            "velocity_trend": self._velocity.velocity_trend,
        }

        self._history.append(point)

        # Keep last 90 days
        if len(self._history) > 90:
            self._history = self._history[-90:]

        self._recalculate_net_capital()

    async def _save(self) -> None:
        """Persist velocity data."""
        storage_path = Path.home() / ".ownex" / "capital_velocity.json"
        storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "velocity": {
                "income_today": self._velocity.income_today,
                "saved_today": self._velocity.saved_today,
                "invested_today": self._velocity.invested_today,
                "portfolio_return_today": self._velocity.portfolio_return_today,
                "trading_pnl_today": self._velocity.trading_pnl_today,
                "dividends_today": self._velocity.dividends_today,
                "net_capital_added": self._velocity.net_capital_added,
                "target_500k_pct": self._velocity.target_500k_pct,
                "eta_500k_months": self._velocity.eta_500k_months,
                "velocity_trend": self._velocity.velocity_trend,
                "last_updated": self._velocity.last_updated.isoformat(),
            },
            "history": self._history[-90:],
        }

        storage_path = Path.home() / ".ownex" / "capital_velocity.json"
        storage_path.parent.mkdir(parents=True, exist_ok=True)
        import json

        storage_path.write_text(json.dumps(data, indent=2, default=str))

    async def _load(self) -> None:
        storage_path = Path.home() / ".ownex" / "capital_velocity.json"
        if not storage_path.exists():
            return

        try:
            import json

            data = json.loads(storage_path.read_text())

            v = data.get("velocity", {})
            self._velocity.income_today = v.get("income_today", 0)
            self._velocity.saved_today = v.get("saved_today", 0)
            self._velocity.invested_today = v.get("invested_today", 0)
            self._velocity.portfolio_return_today = v.get("portfolio_return_today", 0)
            self._velocity.trading_pnl_today = v.get("trading_pnl_today", 0)
            self._velocity.dividends_today = v.get("dividends_today", 0)
            self._velocity.net_capital_added = v.get("net_capital_added", 0)
            self._velocity.target_500k_pct = v.get("target_500k_pct", 0)
            self._velocity.eta_500k_months = v.get("eta_500k_months", 0)
            self._velocity.velocity_trend = v.get("velocity_trend", "stable")
            if v.get("last_updated"):
                self._velocity.last_updated = datetime.fromisoformat(v["last_updated"])

            self._history = data.get("history", [])

            logger.info("CapitalVelocity loaded from storage")
        except Exception as e:
            logger.error(f"Failed to load CapitalVelocity: {e}")

    def reset_daily(self) -> None:
        """Reset daily counters (call at midnight)."""
        self._velocity.income_today = 0
        self._velocity.saved_today = 0
        self._velocity.invested_today = 0
        self._velocity.portfolio_return_today = 0
        self._velocity.trading_pnl_today = 0
        self._velocity.dividends_today = 0
