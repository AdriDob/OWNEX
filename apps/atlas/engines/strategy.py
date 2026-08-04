"""Strategy Engine — allocation targets and rebalance recommendations."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.normalizer.base import NormalizedPortfolio

logger = logging.getLogger("orion.atlas.engines.strategy")


@dataclass
class RebalanceSuggestion:
    symbol: str
    current_percent: float
    target_percent: float
    action: str  # buy, sell, hold
    delta_value: float = 0.0


@dataclass
class StrategyRecommendation:
    suggestions: list[RebalanceSuggestion] = list
    total_trades: int = 0
    estimated_cost: float = 0.0
    portfolio_value: float = 0.0


# Default target allocation
DEFAULT_TARGETS: dict[str, float] = {
    "stock": 40.0,
    "etf": 20.0,
    "crypto": 20.0,
    "bond": 10.0,
    "cash": 10.0,
}


class StrategyEngine:
    """Compare current allocation vs target and suggest rebalances."""

    def __init__(self, targets: dict[str, float] | None = None) -> None:
        self.targets = targets or DEFAULT_TARGETS

    async def recommend_rebalance(self, portfolio: NormalizedPortfolio | None = None) -> StrategyRecommendation:
        """Compare actual allocation vs target and generate suggestions."""
        if portfolio is None or not portfolio.positions:
            return StrategyRecommendation()

        total = portfolio.total_value or sum(p.value for p in portfolio.positions)
        if total == 0:
            return StrategyRecommendation()

        # Calculate current allocation by type
        current: dict[str, float] = {}
        for pos in portfolio.positions:
            t = pos.asset_type or "other"
            current[t] = current.get(t, 0) + pos.value

        current_pct = {k: v / total * 100 for k, v in current.items()}
        suggestions = []

        for asset_type, target_pct in self.targets.items():
            current_pct_val = current_pct.get(asset_type, 0.0)
            diff = current_pct_val - target_pct
            if abs(diff) < 5.0:  # 5% threshold before suggesting
                continue

            action = "sell" if diff > 0 else "buy"
            delta_value = total * abs(diff) / 100

            suggestions.append(
                RebalanceSuggestion(
                    symbol=asset_type,
                    current_percent=round(current_pct_val, 1),
                    target_percent=target_pct,
                    action=action,
                    delta_value=round(delta_value, 2),
                )
            )

        return StrategyRecommendation(
            suggestions=suggestions,
            total_trades=len(suggestions),
            estimated_cost=round(len(suggestions) * 5.0, 2),
            portfolio_value=total,
        )
