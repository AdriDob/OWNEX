"""Bankroll Engine — track capital allocation across platforms."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from apps.odyssey.models import Bankroll
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.odyssey.engines.bankroll")


@dataclass
class BankrollSummary:
    total_balance: float = 0.0
    platform_count: int = 0
    by_platform: dict[str, float] = dict
    largest_position: str = ""
    risk_distribution: dict[str, int] = dict  # low/medium/high


class BankrollEngine:
    """Aggregate and analyze bankroll data."""

    async def summarize(self) -> BankrollSummary:
        db = get_db_manager().get_session("odyssey")
        try:
            bankrolls = db.query(Bankroll).all()
            if not bankrolls:
                return BankrollSummary()

            total = sum(b.balance for b in bankrolls)
            by_platform: dict[str, float] = {}
            risk_dist: dict[str, int] = {}

            for b in bankrolls:
                by_platform[b.platform or "manual"] = by_platform.get(b.platform or "manual", 0) + b.balance
                rl = b.risk_level or "medium"
                risk_dist[rl] = risk_dist.get(rl, 0) + 1

            largest = max(by_platform, key=by_platform.get) if by_platform else ""

            return BankrollSummary(
                total_balance=round(total, 2),
                platform_count=len(bankrolls),
                by_platform=by_platform,
                largest_position=largest,
                risk_distribution=risk_dist,
            )
        finally:
            db.close()

    async def get_balance(self, platform: str) -> float:
        db = get_db_manager().get_session("odyssey")
        try:
            result = db.query(Bankroll).filter(Bankroll.platform == platform).first()
            return result.balance if result else 0.0
        finally:
            db.close()
