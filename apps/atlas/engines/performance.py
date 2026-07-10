"""Performance Engine — P&L, returns, and benchmark comparison."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from apps.atlas.models import Asset
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.atlas.engines.performance")


@dataclass
class PerformanceMetrics:
    total_invested: float = 0.0
    current_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    best_performer: str = ""
    worst_performer: str = ""


class PerformanceEngine:
    """Calculate portfolio performance metrics."""

    async def calculate(self) -> PerformanceMetrics:
        """Calculate performance from DB data."""
        db = get_db_manager().get_session("atlas")
        try:
            assets = db.query(Asset).all()
            total_invested = sum(a.quantity * a.avg_price for a in assets)
            current_value = sum(a.quantity * a.avg_price for a in assets)  # TODO: use live prices
            total_pnl = current_value - total_invested
            total_pnl_pct = ((current_value - total_invested) / total_invested * 100) if total_invested else 0.0

            # Best/worst performers by value
            performers = sorted(assets, key=lambda a: a.quantity * a.avg_price, reverse=True)

            return PerformanceMetrics(
                total_invested=round(total_invested, 2),
                current_value=round(current_value, 2),
                total_pnl=round(total_pnl, 2),
                total_pnl_percent=round(total_pnl_pct, 2),
                best_performer=performers[0].symbol if performers else "",
                worst_performer=performers[-1].symbol if performers and len(performers) > 1 else "",
            )
        finally:
            db.close()
