"""Alert Engine — trigger notifications based on conditions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from apps.odyssey.engines.kelly import KellyEngine
from apps.odyssey.models import Bet
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.odyssey.engines.alert")


@dataclass
class Alert:
    type: str  # positive_ev, losing_streak, bankroll_drop, opportunity
    severity: str  # info, warning, critical
    message: str
    data: dict[str, Any] = dict


class AlertEngine:
    """Check for conditions that should trigger alerts."""

    def __init__(self) -> None:
        self._kelly = KellyEngine()

    async def check_all(self) -> list[Alert]:
        alerts: list[Alert] = []
        alerts.extend(await self._check_losing_streak())
        return alerts

    async def _check_losing_streak(self) -> list[Alert]:
        db = get_db_manager().get_session("odyssey")
        try:
            recent = (
                db.query(Bet).filter(Bet.outcome.in_(["win", "loss"])).order_by(Bet.placed_at.desc()).limit(20).all()
            )

            streak = 0
            for bet in recent:
                if bet.outcome == "loss":
                    streak += 1
                else:
                    break

            if streak >= 5:
                return [
                    Alert(
                        type="losing_streak",
                        severity="warning",
                        message=f"Losing streak of {streak} consecutive bets",
                        data={"streak": streak},
                    )
                ]
            return []
        finally:
            db.close()
