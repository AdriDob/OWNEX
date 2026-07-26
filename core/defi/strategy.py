"""Compound strategy — the $3K → 5 high-yield protocols → retire simulator.

Models the tweet strategy:

    1. Save $3000
    2. Convert to USDC
    3. Put into 5 high-yield DeFi protocols
    4. Earn ~$1000/month
    5. Reinvest profits
    6. Retire in 3-4 years

Provides projections with configurable:
    - initial capital
    - number of protocols
    - APY per protocol
    - monthly contribution (reinvest rate)
    - target monthly income for "retirement"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.defi.positions import HIGH_YIELD_PROTOCOLS


@dataclass
class StrategyProjection:
    """Projected outcome of a compounding strategy."""

    initial_capital: float
    monthly_contribution: float
    total_protocols: int
    weighted_apy: float
    monthly_yield_target: float
    projections: list[dict[str, Any]] = field(default_factory=list)
    months_to_target: int = 0
    total_after_5y: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "monthly_contribution": self.monthly_contribution,
            "total_protocols": self.total_protocols,
            "weighted_apy": round(self.weighted_apy, 2),
            "monthly_yield_target": self.monthly_yield_target,
            "months_to_target": self.months_to_target,
            "years_to_target": round(self.months_to_target / 12, 1),
            "total_after_5y": round(self.total_after_5y, 2),
            "monthly_income_at_target": round(self.monthly_yield_target, 2),
            "projections": self.projections,
        }


@dataclass
class CompoundStrategy:
    """The $3K → 5 protocols → compound → retire strategy."""

    initial_capital: float = 3000.0
    protocols: list[str] = field(default_factory=lambda: list(HIGH_YIELD_PROTOCOLS))
    apy_per_protocol: list[float] = field(default_factory=lambda: [20.0, 25.0, 15.0, 18.0, 30.0])
    reinvest_rate: float = 1.0  # 1.0 = 100% reinvested
    monthly_yield_target: float = 1000.0

    def project(
        self,
        months: int = 60,
        monthly_contribution: float = 0.0,
    ) -> StrategyProjection:
        """Project the strategy over time.

        Args:
            months: Number of months to project.
            monthly_contribution: Additional capital added each month.

        Returns:
            StrategyProjection with monthly breakdown.
        """
        n = min(len(self.protocols), len(self.apy_per_protocol))
        if n == 0:
            return StrategyProjection(
                initial_capital=self.initial_capital,
                monthly_contribution=monthly_contribution,
                total_protocols=0,
                weighted_apy=0.0,
                monthly_yield_target=self.monthly_yield_target,
                months_to_target=months,
                total_after_5y=self.initial_capital,
            )

        weighted_apy = sum(self.apy_per_protocol[:n]) / n
        # Distribute capital evenly across protocols
        capital_per_protocol = self.initial_capital / n
        monthly_rate_per_protocol = [a / 100 / 12 for a in self.apy_per_protocol[:n]]

        # Track each protocol separately
        balances = [capital_per_protocol] * n
        result = StrategyProjection(
            initial_capital=self.initial_capital,
            monthly_contribution=monthly_contribution,
            total_protocols=n,
            weighted_apy=weighted_apy,
            monthly_yield_target=self.monthly_yield_target,
        )

        total = self.initial_capital
        target_reached_month = None

        for m in range(1, months + 1):
            # Earn yield on each protocol
            for i in range(n):
                yield_earned = balances[i] * monthly_rate_per_protocol[i]
                reinvested = yield_earned * self.reinvest_rate
                balances[i] += reinvested

            # Add monthly contribution (distributed evenly)
            if monthly_contribution > 0:
                per_protocol = monthly_contribution / n
                for i in range(n):
                    balances[i] += per_protocol

            total = sum(balances)
            monthly_yield = sum(b * r for b, r in zip(balances, monthly_rate_per_protocol, strict=False))

            entry = {
                "month": m,
                "year": round(m / 12, 1),
                "total_balance": round(total, 2),
                "monthly_yield": round(monthly_yield, 2),
                "monthly_yield_pct": round(monthly_yield / total * 100, 2) if total > 0 else 0.0,
                "capital_gain": round(total - self.initial_capital - monthly_contribution * m, 2),
            }
            result.projections.append(entry)

            if monthly_yield >= self.monthly_yield_target and target_reached_month is None:
                target_reached_month = m

        result.months_to_target = target_reached_month or months
        result.total_after_5y = total

        return result

    @staticmethod
    def tweet_default() -> StrategyProjection:
        """The exact tweet strategy: $3K in 5 high-yield protocols."""
        strategy = CompoundStrategy(
            initial_capital=3000.0,
            protocols=list(HIGH_YIELD_PROTOCOLS),
            apy_per_protocol=[20.0, 25.0, 15.0, 18.0, 30.0],
            reinvest_rate=1.0,
            monthly_yield_target=1000.0,
        )
        return strategy.project(months=60, monthly_contribution=0.0)
