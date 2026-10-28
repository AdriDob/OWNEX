from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("orion.investment.polymarket")


class PolymarketAdapter:
    """Adapter for Polymarket prediction market trading.

    Interfaces with the Polymarket CLOB API and Gamma market data.
    Supports market scanning, order placement, and position tracking.
    This is a structured adapter — actual bot logic lives in strategies.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._api_key = self._config.get("api_key", "")
        self._secret = self._config.get("secret", "")
        self._connected = False
        self._base_url = "https://clob.polymarket.com"
        self._gamma_url = "https://gamma-api.polymarket.com"

    @property
    def name(self) -> str:
        return "polymarket"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        if not self._api_key:
            logger.warning("Polymarket adapter: no API key configured")
            return False
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._gamma_url}/markets?limit=1", timeout=10)
                if resp.status_code == 200:
                    self._connected = True
                    logger.info("Connected to Polymarket")
                    return True
                logger.warning("Polymarket API returned status %d", resp.status_code)
                return False
        except ImportError:
            logger.error("httpx not installed")
            return False
        except Exception as e:
            logger.error("Failed to connect to Polymarket: %s", e)
            return False

    async def disconnect(self) -> None:
        self._connected = False

    async def get_markets(self, limit: int = 50, tag: str = "") -> list[dict[str, Any]]:
        """Fetch active markets from Polymarket."""
        if not self._connected:
            return []
        try:
            import httpx

            params: dict[str, Any] = {
                "limit": min(limit, 100),
                "closed": "false",
                "order": "volume",
                "asc": "false",
            }
            if tag:
                params["tag"] = tag

            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._gamma_url}/markets", params=params, timeout=15)
                if resp.status_code != 200:
                    logger.warning("Polymarket markets API: %d", resp.status_code)
                    return []

                markets = resp.json()
                return [
                    {
                        "id": m.get("id"),
                        "slug": m.get("slug"),
                        "question": m.get("question"),
                        "description": m.get("description", "")[:200],
                        "volume": m.get("volume"),
                        "liquidity": m.get("liquidity"),
                        "end_date": m.get("endDate"),
                        "outcomes": m.get("outcomes", []),
                        "tags": m.get("tags", []),
                    }
                    for m in (markets or [])
                ]
        except Exception as e:
            logger.error("Failed to fetch Polymarket markets: %s", e)
            return []

    async def get_market_prices(self, market_id: str) -> dict[str, Any]:
        """Get current prices for a market's outcomes via CLOB."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/prices",
                    params={"market": market_id},
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "market_id": market_id,
                        "prices": data,
                        "spread": max(data.values()) - min(data.values()) if data else 0,
                    }
                return {"market_id": market_id, "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"market_id": market_id, "error": str(e)}

    async def find_arbitrage_opportunities(self, min_spread: float = 0.05) -> list[dict[str, Any]]:
        """Scan markets for arbitrage opportunities (price mismatches).

        Looks for markets where outcomes don't sum to 1 (inefficient pricing).
        """
        markets = await self.get_markets(limit=50)
        opportunities: list[dict[str, Any]] = []

        for market in markets:
            mid = market.get("id", "")
            if not mid:
                continue
            prices = await self.get_market_prices(mid)
            px = prices.get("prices", {})
            if not px or not isinstance(px, dict):
                continue

            total_prob = sum(float(v) for v in px.values() if v is not None)
            if abs(total_prob - 1.0) > min_spread:
                arb_type = "overpriced" if total_prob > 1.0 else "underpriced"
                opportunities.append(
                    {
                        "market_id": mid,
                        "question": market.get("question", ""),
                        "total_probability": round(total_prob, 4),
                        "spread": round(abs(total_prob - 1.0), 4),
                        "type": arb_type,
                        "prices": px,
                    }
                )

        return sorted(opportunities, key=lambda o: o["spread"], reverse=True)

    async def place_order(
        self,
        market_id: str,
        outcome: str,
        side: str,
        size: float,
        price: float,
    ) -> dict[str, Any]:
        """Place an order on Polymarket CLOB.

        Note: Requires proper API authentication with signed headers.
        This is a structured interface — actual signing is handled by
        the Polymarket CLOB SDK or manual EIP-712 signing.
        """
        logger.info(
            "Polymarket order: %s %s %.4f @ %.2f on %s",
            side,
            outcome,
            size,
            price,
            market_id,
        )
        return {
            "success": False,
            "message": "CLOB order signing requires EIP-712 implementation. Use polymarket-trading-bot-python-V2 for full bot logic.",
            "market_id": market_id,
            "outcome": outcome,
            "side": side,
            "size": size,
            "price": price,
        }

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get current positions."""
        logger.debug("Polymarket positions: query not yet implemented")
        return []

    async def get_portfolio_summary(self) -> dict[str, Any]:
        """Get summary of Polymarket portfolio performance."""
        positions = await self.get_positions()
        return {
            "connected": self._connected,
            "exchange": "Polymarket",
            "positions_count": len(positions),
            "summary": "Polymarket adapter connected. Full trading requires CLOB SDK integration.",
            "docs_url": "https://docs.polymarket.com/api/rest",
        }


def build_polymarket_adapter(config: dict[str, Any] | None = None) -> PolymarketAdapter:
    """Factory function to create Polymarket adapter."""
    return PolymarketAdapter(config)
