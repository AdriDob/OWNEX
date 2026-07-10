"""Market Engine — analyze market liquidity, depth, and competitiveness."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.normalizer.base import NormalizedMarket

logger = logging.getLogger("orion.odyssey.engines.market")


@dataclass
class MarketAnalysis:
    total_volume: float = 0.0
    liquidity_score: float = 0.0  # 0-100
    market_count: int = 0
    sport_distribution: dict[str, int] = dict
    avg_odds: float = 0.0
    best_odds_available: bool = False


class MarketEngine:
    """Analyze available markets for opportunities."""

    async def analyze(self, markets: list[NormalizedMarket]) -> MarketAnalysis:
        total_volume = sum(m.volume for m in markets if m.volume)
        sports: dict[str, int] = {}
        odds_values = []

        for m in markets:
            sport = m.sport or "unknown"
            sports[sport] = sports.get(sport, 0) + 1
            if m.odds_home and m.odds_away:
                odds_values.extend([m.odds_home, m.odds_away])

        avg_odds = sum(odds_values) / len(odds_values) if odds_values else 0.0
        liquidity_score = min(100.0, total_volume / 100_000 * 100) if total_volume else 0.0

        return MarketAnalysis(
            total_volume=round(total_volume, 2),
            liquidity_score=round(liquidity_score, 1),
            market_count=len(markets),
            sport_distribution=sports,
            avg_odds=round(avg_odds, 2),
            best_odds_available=False,
        )
