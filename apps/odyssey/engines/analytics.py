"""Analytics Engine — deep betting statistics and pattern detection."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from apps.odyssey.models import Bet
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.odyssey.engines.analytics")


@dataclass
class Pattern:
    sport: str = ""
    bet_type: str = ""
    roi: float = 0.0
    bet_count: int = 0
    win_rate: float = 0.0


@dataclass
class AnalyticsSummary:
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    pending: int = 0
    win_rate: float = 0.0
    roi: float = 0.0
    profit: float = 0.0
    avg_odds: float = 0.0
    avg_ev: float = 0.0
    avg_clv: float = 0.0
    best_patterns: list[Pattern] = list
    worst_patterns: list[Pattern] = list


class AnalyticsEngine:
    """Deep betting analytics and pattern detection."""

    async def full_analytics(self) -> AnalyticsSummary:
        db = get_db_manager().get_session("odyssey")
        try:
            bets = db.query(Bet).all()
            settled = [b for b in bets if b.outcome in ("win", "loss")]
            wins = [b for b in settled if b.outcome == "win"]
            losses = [b for b in settled if b.outcome == "loss"]
            pending = [b for b in bets if b.outcome == "pending"]

            win_rate = len(wins) / len(settled) * 100 if settled else 0.0
            total_staked = sum(b.stake for b in settled)
            total_payout = sum(b.payout for b in settled)
            profit = total_payout - total_staked
            roi = profit / total_staked * 100 if total_staked else 0.0
            avg_odds = sum(b.odds for b in settled) / len(settled) if settled else 0.0
            avg_ev = sum(b.ev for b in settled) / len(settled) if settled else 0.0
            valid_clv = [b.clv for b in settled if b.clv is not None]
            avg_clv = sum(valid_clv) / len(valid_clv) if valid_clv else 0.0

            return AnalyticsSummary(
                total_bets=len(bets),
                wins=len(wins),
                losses=len(losses),
                pushes=sum(1 for b in bets if b.outcome == "push"),
                pending=len(pending),
                win_rate=round(win_rate, 1),
                roi=round(roi, 2),
                profit=round(profit, 2),
                avg_odds=round(avg_odds, 2),
                avg_ev=round(avg_ev, 4),
                avg_clv=round(avg_clv, 4),
            )
        finally:
            db.close()
