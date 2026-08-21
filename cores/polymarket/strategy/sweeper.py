"""Sweeper Strategy — buy outcomes near resolution at 99¢ → $1.

The simplest Polymarket strategy:
1. Find markets about to resolve (99% probability)
2. Buy the winning outcome at ~$0.99
3. Wait for resolution → receive $1.00
4. Profit: ~1% per trade (minus fees)

Risk: If the market reverses (99% → 0%), you lose your position.
Mitigation: Only trade high-volume, high-liquidity markets with clear resolution.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from core.polymarket.client import PolymarketClient, get_client

logger = logging.getLogger("orion.polymarket.strategy.sweeper")


@dataclass
class SweeperConfig:
    """Sweeper strategy configuration."""

    # Price thresholds
    min_price: float = 0.93  # Minimum price to consider buying
    max_price: float = 0.99  # Maximum price to buy at
    target_profit_pct: float = 0.01  # Minimum 1% profit target

    # Filters
    min_volume_24h: float = 10_000  # Minimum $10k daily volume
    min_liquidity: float = 5_000  # Minimum $5k liquidity
    min_time_to_resolution: float = 3600  # At least 1 hour to resolution
    max_time_to_resolution: float = 86400 * 7  # Max 7 days to resolution

    # Position sizing
    max_position_usd: float = 100.0  # Max $100 per position
    max_total_exposure: float = 500.0  # Max $500 total exposure

    # Risk management
    max_spread: float = 0.02  # Max 2% bid-ask spread
    min_book_depth: float = 100.0  # Min $100 book depth

    # Scanning
    scan_interval: float = 60.0  # Scan every 60 seconds
    max_markets_to_scan: int = 100


@dataclass
class SweeperOpportunity:
    """A sweeper trading opportunity."""

    market_id: str
    question: str
    token_id: str
    outcome: str
    current_price: float
    spread: float
    volume_24h: float
    liquidity: float
    estimated_profit_pct: float
    time_to_resolution: float | None
    score: float  # Combined opportunity score


class SweeperStrategy:
    """Sweeper strategy — buy near-certain outcomes at discount.

    Scans Polymarket for markets where:
    - One outcome is priced at 93-99¢
    - High volume and liquidity
    - Clear resolution expected

    The strategy identifies opportunities but does NOT execute trades automatically.
    Trades require manual approval or explicit dry_run=False configuration.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = SweeperConfig(**{k: v for k, v in (config or {}).items() if k in SweeperConfig.__dataclass_fields__})
        self._client: PolymarketClient | None = None
        self._opportunities: list[SweeperOpportunity] = []
        self._positions: dict[str, dict[str, Any]] = {}  # market_id -> position info
        self._scan_count = 0
        self._running = False

    @property
    def name(self) -> str:
        return "sweeper"

    def _get_client(self) -> PolymarketClient:
        if self._client is None:
            self._client = get_client()
        return self._client

    # ── Scanning ───────────────────────────────────────────────────────

    async def scan_opportunities(self) -> list[SweeperOpportunity]:
        """Scan for sweeper opportunities."""
        client = self._get_client()
        self._scan_count += 1

        logger.info("Scanning for sweeper opportunities (scan #%d)", self._scan_count)

        # Fetch markets
        markets = await client.list_markets(
            closed=False,
            limit=self._config.max_markets_to_scan,
        )

        opportunities = []

        for market in markets:
            try:
                opp = await self._evaluate_market(market, client)
                if opp:
                    opportunities.append(opp)
            except Exception as e:
                logger.debug("Failed to evaluate market %s: %s", market.get("condition_id"), e)
                continue

        # Sort by score (best first)
        opportunities.sort(key=lambda x: x.score, reverse=True)

        self._opportunities = opportunities
        logger.info("Found %d sweeper opportunities", len(opportunities))

        return opportunities

    async def _evaluate_market(
        self,
        market: dict[str, Any],
        client: PolymarketClient,
    ) -> SweeperOpportunity | None:
        """Evaluate a single market for sweeper opportunity."""
        # Check volume
        volume = float(market.get("volume24hr", 0) or 0)
        if volume < self._config.min_volume_24h:
            return None

        # Check liquidity
        liquidity = float(market.get("liquidity", 0) or 0)
        if liquidity < self._config.min_liquidity:
            return None

        # Get tokens
        tokens = market.get("tokens", [])
        if not tokens:
            return None

        # Evaluate each token
        best_opp: SweeperOpportunity | None = None

        for token in tokens:
            token_id = token.get("token_id")
            if not token_id:
                continue

            # Get current price
            price = await client.get_price(token_id)
            if price is None:
                continue

            # Check if price is in sweeper range
            if price < self._config.min_price or price > self._config.max_price:
                continue

            # Get order book for spread calculation
            book = await client.get_order_book(token_id)
            spread = 0.0
            book_depth = 0.0

            if book:
                bids = book.get("bids", [])
                asks = book.get("asks", [])

                if bids and asks:
                    best_bid = float(bids[0].get("price", 0))
                    best_ask = float(asks[0].get("price", 0))
                    spread = best_ask - best_bid if best_ask > best_bid else 0.0

                    # Calculate book depth
                    book_depth = sum(float(b.get("size", 0)) for b in bids[:5])

            # Check spread limit
            if spread > self._config.max_spread:
                continue

            # Check book depth
            if book_depth < self._config.min_book_depth:
                continue

            # Calculate profit potential
            profit_pct = (1.0 - price) / price  # Profit if resolves to $1

            if profit_pct < self._config.target_profit_pct:
                continue

            # Calculate score (higher is better)
            score = self._calculate_score(
                price=price,
                spread=spread,
                volume=volume,
                liquidity=liquidity,
                profit_pct=profit_pct,
                book_depth=book_depth,
            )

            opp = SweeperOpportunity(
                market_id=market.get("condition_id", ""),
                question=market.get("question", ""),
                token_id=token_id,
                outcome=token.get("outcome", ""),
                current_price=price,
                spread=spread,
                volume_24h=volume,
                liquidity=liquidity,
                estimated_profit_pct=profit_pct,
                time_to_resolution=None,  # TODO: parse end_date_iso
                score=score,
            )

            if best_opp is None or opp.score > best_opp.score:
                best_opp = opp

        return best_opp

    def _calculate_score(
        self,
        price: float,
        spread: float,
        volume: float,
        liquidity: float,
        profit_pct: float,
        book_depth: float,
    ) -> float:
        """Calculate opportunity score (0-100)."""
        # Profit score (higher profit = higher score)
        profit_score = min(profit_pct * 100, 30)  # Max 30 points

        # Spread score (lower spread = higher score)
        spread_score = max(0, (0.02 - spread) / 0.02 * 20)  # Max 20 points

        # Volume score (higher volume = higher score)
        volume_score = min(volume / 100_000 * 20, 20)  # Max 20 points

        # Liquidity score (higher liquidity = higher score)
        liquidity_score = min(liquidity / 50_000 * 15, 15)  # Max 15 points

        # Depth score (deeper book = higher score)
        depth_score = min(book_depth / 1_000 * 15, 15)  # Max 15 points

        return profit_score + spread_score + volume_score + liquidity_score + depth_score

    # ── Position Tracking ──────────────────────────────────────────────

    def get_positions(self) -> dict[str, dict[str, Any]]:
        """Get current positions."""
        return self._positions.copy()

    def get_total_exposure(self) -> float:
        """Get total USD exposure across all positions."""
        return sum(pos.get("size_usd", 0) for pos in self._positions.values())

    def can_open_position(self, size_usd: float) -> bool:
        """Check if we can open a new position within limits."""
        current = self.get_total_exposure()
        return (current + size_usd) <= self._config.max_total_exposure

    # ── Summary ────────────────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Get strategy summary."""
        return {
            "strategy": self.name,
            "scan_count": self._scan_count,
            "opportunities_found": len(self._opportunities),
            "positions_open": len(self._positions),
            "total_exposure_usd": self.get_total_exposure(),
            "config": {
                "min_price": self._config.min_price,
                "max_price": self._config.max_price,
                "min_volume_24h": self._config.min_volume_24h,
                "min_liquidity": self._config.min_liquidity,
                "max_position_usd": self._config.max_position_usd,
                "max_total_exposure": self._config.max_total_exposure,
            },
            "top_opportunities": [
                {
                    "question": opp.question[:60],
                    "price": opp.current_price,
                    "profit_pct": f"{opp.estimated_profit_pct:.1%}",
                    "score": round(opp.score, 1),
                }
                for opp in self._opportunities[:5]
            ],
        }

    # ── Health Check ───────────────────────────────────────────────────

    async def check_setup(self) -> dict[str, Any]:
        """Check if the strategy is properly configured."""
        client = self._get_client()
        health = await client.health_check()

        return {
            "strategy": self.name,
            "api_health": health,
            "config_valid": True,
            "ready": health.get("status") == "ok",
        }
