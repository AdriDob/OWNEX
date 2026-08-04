"""Portfolio Engine — aggregates positions across all connectors."""

from __future__ import annotations

import logging
from typing import Any

from apps.atlas.models import Asset
from core.database.manager import get_db_manager
from core.normalizer.base import NormalizedPortfolio, NormalizedPosition

logger = logging.getLogger("orion.atlas.engines.portfolio")


class PortfolioEngine:
    """Aggregates portfolio data from all connected sources."""

    def __init__(self) -> None:
        self._connectors: list[Any] = []

    def register_connector(self, connector: Any) -> None:
        self._connectors.append(connector)

    async def aggregate(self) -> NormalizedPortfolio:
        """Fetch and merge portfolios from all registered connectors."""
        all_positions: dict[str, NormalizedPosition] = {}
        total_value = 0.0

        for connector in self._connectors:
            try:
                portfolio = await connector.get_portfolio()
                if portfolio is None:
                    continue
                total_value += portfolio.total_value
                for pos in portfolio.positions:
                    key = f"{pos.symbol}:{pos.asset_type}"
                    if key in all_positions:
                        existing = all_positions[key]
                        total_qty = existing.quantity + pos.quantity
                        existing.quantity = total_qty
                        existing.value += pos.value
                    else:
                        all_positions[key] = pos
            except Exception as exc:
                logger.warning("Portfolio fetch failed for %s: %s", getattr(connector, "connector_id", "?"), exc)

        return NormalizedPortfolio(
            total_value=total_value,
            positions=list(all_positions.values()),
            provider="aggregated",
        )

    async def save_snapshot(self, portfolio: NormalizedPortfolio) -> None:
        """Save current portfolio state to DB."""
        db = get_db_manager().get_session("atlas")
        try:
            for pos in portfolio.positions:
                asset = (
                    db.query(Asset)
                    .filter(
                        Asset.symbol == pos.symbol,
                        Asset.portfolio_id == 1,
                    )
                    .first()
                )
                if asset:
                    asset.quantity = pos.quantity
                    asset.avg_price = pos.avg_price
                else:
                    db.add(
                        Asset(
                            portfolio_id=1,
                            symbol=pos.symbol,
                            name=pos.name,
                            asset_type=pos.asset_type,
                            quantity=pos.quantity,
                            avg_price=pos.avg_price,
                        )
                    )
            db.commit()
            logger.info("Portfolio snapshot saved (%d positions)", len(portfolio.positions))
        except Exception as exc:
            db.rollback()
            logger.error("Failed to save portfolio: %s", exc)
        finally:
            db.close()
