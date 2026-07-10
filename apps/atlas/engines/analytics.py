"""Analytics Engine — advanced portfolio analytics.

Allocation by type, sector, currency, and historical comparisons.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.normalizer.base import NormalizedPortfolio

logger = logging.getLogger("orion.atlas.engines.analytics")


@dataclass
class AllocationBreakdown:
    by_type: dict[str, float]  # stock: 45.2, crypto: 30.1, cash: 24.7
    by_symbol: dict[str, float]
    num_assets: int = 0
    top_symbols: list[dict] = list


class AnalyticsEngine:
    """Generate allocation and distribution analytics."""

    async def analyze_allocation(self, portfolio: NormalizedPortfolio | None = None) -> AllocationBreakdown:
        """Analyze portfolio allocation."""
        if portfolio is None or not portfolio.positions:
            return AllocationBreakdown()

        total = portfolio.total_value or sum(p.value for p in portfolio.positions)
        if total == 0:
            return AllocationBreakdown()

        by_type: dict[str, float] = {}
        by_symbol: dict[str, float] = {}

        for pos in portfolio.positions:
            t = pos.asset_type or "other"
            by_type[t] = by_type.get(t, 0) + pos.value
            by_symbol[pos.symbol] = by_symbol.get(pos.symbol, 0) + pos.value

        # Convert to percentages
        by_type_pct = {k: round(v / total * 100, 1) for k, v in by_type.items()}
        by_symbol_pct = {k: round(v / total * 100, 1) for k, v in by_symbol.items()}

        top_symbols = sorted(by_symbol_pct.items(), key=lambda x: x[1], reverse=True)[:5]
        top_symbols_list = [{"symbol": s, "percent": p} for s, p in top_symbols]

        return AllocationBreakdown(
            by_type=by_type_pct,
            by_symbol=by_symbol_pct,
            num_assets=len(portfolio.positions),
            top_symbols=top_symbols_list,
        )
