"""Polymarket CLOB Client Adapter for OWNEX.

Official Polymarket CLOB (Central Limit Order Book) client integration.
Based on: https://github.com/Polymarket/py-clob-client
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.polymarket_clob")


class PolymarketCLOBAdapter:
    """Polymarket CLOB (Central Limit Order Book) client adapter.

    Provides access to:
    - Order books for all markets
    - Real-time price feeds
    - Order placement and management
    - Market data and analytics
    - User positions and balances

    Official docs: https://docs.polymarket.com/api-reference/introduction
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._client: Any = None
        self._connected = False

    @property
    def name(self) -> str:
        return "polymarket_clob"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Connect to Polymarket CLOB API."""
        try:
            from py_clob_client.client import ClobClient
            from py_clob_client.clob_types import OrderArgs

            self._clob_client = ClobClient
            self._order_args = OrderArgs

            # CLOB endpoint
            host = self._config.get("host", "https://clob.polymarket.com")
            self._client = ClobClient(host=host)

            # Load markets
            await self._load_markets()
            self._connected = True
            logger.info("Connected to Polymarket CLOB")
            return True
        except ImportError:
            logger.error("py-clob-client not installed. Run: pip install py-clob-client")
            return False
        except Exception as e:
            logger.error("Failed to connect to Polymarket CLOB: %s", e)
            return False

    async def _load_markets(self) -> None:
        """Load available markets."""
        try:
            markets = self._client.get_markets()
            self._markets = {m["condition_id"]: m for m in markets}
            logger.info("Loaded %d Polymarket markets", len(self._markets))
        except Exception as e:
            logger.error("Failed to load markets: %s", e)
            self._markets = {}

    async def disconnect(self) -> None:
        """Disconnect from CLOB."""
        self._connected = False

    async def get_order_book(self, condition_id: str, depth: int = 20) -> dict[str, Any]:
        """Get order book for a market."""
        if not self._connected:
            return {"error": "Not connected"}
        try:
            book = self._client.get_order_book(condition_id)
            return {
                "condition_id": condition_id,
                "bids": book.get("bids", [])[:depth],
                "asks": book.get("asks", [])[:depth],
                "timestamp": book.get("timestamp"),
            }
        except Exception as e:
            logger.error("Order book fetch failed for %s: %s", condition_id, e)
            return {"error": str(e)}

    async def get_market_prices(self, condition_ids: list[str] | None = None) -> dict[str, Any]:
        """Get current prices for markets."""
        if not self._connected:
            return {"error": "Not connected"}
        try:
            if condition_ids is None:
                condition_ids = list(self._markets.keys())[:50]  # Limit
            prices = {}
            for cid in condition_ids:
                book = await self.get_order_book(cid, depth=1)
                if "bids" in book and book["bids"]:
                    prices[cid] = {
                        "bid": book["bids"][0]["price"],
                        "ask": book["asks"][0]["price"] if book["asks"] else None,
                        "mid": (
                            book["bids"][0]["price"]
                            + (book["asks"][0]["price"] if book["asks"] else book["bids"][0]["price"])
                        )
                        / 2,
                    }
            return {"prices": prices}
        except Exception as e:
            logger.error("Market prices fetch failed: %s", e)
            return {"error": str(e)}

    async def place_order(
        self,
        condition_id: str,
        side: str,  # "buy" or "sell"
        price: float,
        size: float,
    ) -> dict[str, Any]:
        """Place an order on Polymarket CLOB."""
        if not self._connected:
            return {"error": "Not connected"}
        try:
            order = self._order_args(
                condition_id=condition_id,
                side=side,
                price=price,
                size=size,
            )
            result = self._client.create_order(order)
            return {
                "order_id": result.get("order_id"),
                "status": result.get("status"),
                "condition_id": condition_id,
                "side": side,
                "price": price,
                "size": size,
            }
        except Exception as e:
            logger.error("Order placement failed: %s", e)
            return {"error": str(e)}

    async def get_user_positions(self, address: str) -> list[dict[str, Any]]:
        """Get user positions."""
        if not self._connected:
            return []
        try:
            positions = self._client.get_positions(address)
            return [
                {
                    "condition_id": p.get("condition_id"),
                    "size": p.get("size"),
                    "entry_price": p.get("entry_price"),
                    "current_price": p.get("current_price"),
                    "pnl": p.get("pnl"),
                }
                for p in positions
            ]
        except Exception as e:
            logger.error("Positions fetch failed: %s", e)
            return []

    async def get_market_info(self, condition_id: str) -> dict[str, Any]:
        """Get detailed market information."""
        if condition_id not in self._markets:
            return {"error": "Market not found"}
        market = self._markets[condition_id]
        return {
            "condition_id": condition_id,
            "question": market.get("question"),
            "outcomes": market.get("outcomes"),
            "outcome_prices": market.get("outcome_prices"),
            "volume": market.get("volume"),
            "liquidity": market.get("liquidity"),
            "end_date": market.get("end_date"),
            "category": market.get("category"),
        }

    async def scan_mispriced_markets(self, min_edge: float = 0.02) -> list[dict[str, Any]]:
        """Scan for potentially mispriced markets.

        Compares implied probabilities across outcomes and identifies
        markets where probabilities don't sum to ~1 or show anomalies.
        """
        if not self._connected:
            return []

        mispriced = []
        try:
            for cid, market in list(self._markets.items())[:100]:  # Sample
                prices = market.get("outcome_prices", {})
                if not prices:
                    continue

                # Sum of probabilities
                total_prob = sum(float(p) for p in prices.values() if p)

                # Check for arbitrage opportunity (sum < 1 - min_edge)
                if total_prob < (1.0 - min_edge):
                    edge = 1.0 - total_prob
                    mispriced.append(
                        {
                            "condition_id": cid,
                            "question": market.get("question"),
                            "total_probability": round(total_prob, 4),
                            "edge": round(edge, 4),
                            "outcomes": prices,
                            "volume": market.get("volume"),
                            "liquidity": market.get("liquidity"),
                        }
                    )

            mispriced.sort(key=lambda x: x["edge"], reverse=True)
            return mispriced[:20]
        except Exception as e:
            logger.error("Mispriced scan failed: %s", e)
            return []

    async def get_liquidity_analysis(self, condition_id: str) -> dict[str, Any]:
        """Analyze market liquidity."""
        book = await self.get_order_book(condition_id, depth=50)
        if "error" in book:
            return book

        bids = book.get("bids", [])
        asks = book.get("asks", [])

        bid_liquidity = sum(float(b["size"]) * float(b["price"]) for b in bids)
        ask_liquidity = sum(float(a["size"]) * float(a["price"]) for a in asks)

        spread = None
        if bids and asks:
            spread = float(asks[0]["price"]) - float(bids[0]["price"])

        return {
            "condition_id": condition_id,
            "bid_liquidity_usd": round(bid_liquidity, 2),
            "ask_liquidity_usd": round(ask_liquidity, 2),
            "total_liquidity_usd": round(bid_liquidity + ask_liquidity, 2),
            "spread": spread,
            "bid_depth": len(bids),
            "ask_depth": len(asks),
        }


def build_polymarket_clob_adapter(config: dict[str, Any] | None = None) -> PolymarketCLOBAdapter:
    """Factory function to create Polymarket CLOB adapter."""
    return PolymarketCLOBAdapter(config)
