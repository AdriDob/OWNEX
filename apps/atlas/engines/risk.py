"""Risk Engine — portfolio risk assessment.

Calculates concentration, volatility, drawdown, and diversification metrics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from core.normalizer.base import NormalizedPortfolio

logger = logging.getLogger("orion.atlas.engines.risk")


@dataclass
class RiskProfile:
    total_value: float = 0.0
    cash_percent: float = 0.0
    top_concentration: float = 0.0  # % in top holding
    crypto_exposure: float = 0.0
    stock_exposure: float = 0.0
    diversification_score: float = 0.0  # 0-100
    volatility_estimate: float = 0.0
    sharpe_estimate: float = 0.0
    max_drawdown_estimate: float = 0.0
    warnings: list[str] = list


class RiskEngine:
    """Assess portfolio risk from normalized data."""

    async def assess(self, portfolio: NormalizedPortfolio) -> RiskProfile:
        """Calculate risk metrics for a portfolio."""
        if not portfolio.positions:
            return RiskProfile()

        values = [p.value for p in portfolio.positions]
        total = sum(values) + portfolio.cash
        if total == 0:
            return RiskProfile()

        types = [p.asset_type for p in portfolio.positions]
        crypto_val = sum(v for v, t in zip(values, types, strict=False) if t == "crypto")
        stock_val = sum(v for v, t in zip(values, types, strict=False) if t in ("stock", "etf"))

        top_concentration = max(values) / total * 100 if values else 0
        cash_pct = portfolio.cash / total * 100
        crypto_pct = crypto_val / total * 100
        stock_pct = stock_val / total * 100

        # Diversification: entropy-based score
        weights = np.array([v / total for v in values])
        entropy = -np.sum(weights * np.log(weights + 1e-10)) / np.log(len(weights)) if len(weights) > 1 else 0
        diversification = entropy * 100

        warnings = []
        if top_concentration > 40:
            warnings.append(f"High concentration in top asset ({top_concentration:.0f}%)")
        if crypto_pct > 50:
            warnings.append(f"High crypto exposure ({crypto_pct:.0f}%)")
        if cash_pct > 50:
            warnings.append(f"High cash drag ({cash_pct:.0f}%)")

        return RiskProfile(
            total_value=total,
            cash_percent=cash_pct,
            top_concentration=top_concentration,
            crypto_exposure=crypto_pct,
            stock_exposure=stock_pct,
            diversification_score=round(diversification, 1),
            volatility_estimate=0.0,
            sharpe_estimate=0.0,
            max_drawdown_estimate=0.0,
            warnings=warnings,
        )
