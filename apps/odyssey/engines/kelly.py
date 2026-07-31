"""Kelly Engine — optimal stake sizing."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from apps.odyssey.providers.kelly import KellyProvider

logger = logging.getLogger("orion.odyssey.engines.kelly")


@dataclass
class KellyRecommendation:
    full_kelly: float = 0.0
    fractional_kelly: float = 0.0
    stake_amount: float = 0.0
    ev: float = 0.0
    growth_rate: float = 0.0
    is_positive_ev: bool = False
    risk_label: str = "skip"  # skip, low, medium, high


class KellyEngine:
    """Calculate and analyze Kelly-optimal stakes."""

    def __init__(self, default_fraction: float = 0.25) -> None:
        self._provider = KellyProvider()
        self.default_fraction = default_fraction

    async def recommend(self, odds: float, win_prob: float, bankroll: float, fraction: float | None = None) -> KellyRecommendation:
        result = self._provider.calculate(odds, win_prob, bankroll, fraction or self.default_fraction)

        ev = result["ev"]
        kelly = result["full_kelly"]
        stake = result["stake_amount"]

        if ev <= 0 or kelly <= 0:
            return KellyRecommendation(ev=round(ev, 4), is_positive_ev=False, risk_label="skip")

        # Risk labels
        if kelly <= 0.05:
            risk = "low"
        elif kelly <= 0.15:
            risk = "medium"
        elif kelly <= 0.30:
            risk = "high"
        else:
            risk = "very_high"

        return KellyRecommendation(
            full_kelly=round(result["full_kelly"], 4),
            fractional_kelly=round(result["fractional_kelly"], 4),
            stake_amount=round(stake, 2),
            ev=round(ev, 4),
            growth_rate=round(result["growth_rate"], 4),
            is_positive_ev=True,
            risk_label=risk,
        )

    async def monte_carlo_bankroll(
        self, bankroll: float, edge: float, odds: float, fraction: float, num_bets: int = 1000, simulations: int = 1000
    ) -> dict:
        """Simulate bankroll growth over N bets."""
        win_prob = edge * odds  # approximate
        stake_pct = fraction * ((edge * (odds - 1) - (1 - win_prob)) / (odds - 1))
        stake_pct = max(0.0, min(stake_pct, 1.0))

        results = []
        for _ in range(simulations):
            bal = bankroll
            for _ in range(num_bets):
                stake = bal * stake_pct
                if stake <= 0:
                    break
                if np.random.random() < win_prob:
                    bal += stake * (odds - 1)
                else:
                    bal -= stake
                if bal <= 0:
                    break
            results.append(bal)

        return {
            "median": round(float(np.median(results)), 2),
            "mean": round(float(np.mean(results)), 2),
            "min": round(float(np.min(results)), 2),
            "max": round(float(np.max(results)), 2),
            "ruin_probability": round(float(np.mean(np.array(results) <= 0) * 100), 1),
            "percentile_5": round(float(np.percentile(results, 5)), 2),
            "percentile_95": round(float(np.percentile(results, 95)), 2),
        }
