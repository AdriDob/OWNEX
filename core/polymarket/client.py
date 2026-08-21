"""Polymarket API client — wrapper around the official Python SDK.

Provides:
- Market discovery and filtering
- Order book access
- Price history
- Rate limiting and retry logic
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("orion.polymarket.client")

# ── Rate limiter ──────────────────────────────────────────────────────────


@dataclass
class RateLimiter:
    """Simple token bucket rate limiter."""

    max_requests: int = 100
    window_seconds: float = 60.0
    _timestamps: list[float] = field(default_factory=list)

    def _prune(self) -> None:
        cutoff = time.monotonic() - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]

    def acquire(self) -> bool:
        self._prune()
        if len(self._timestamps) < self.max_requests:
            self._timestamps.append(time.monotonic())
            return True
        return False

    def wait_time(self) -> float:
        self._prune()
        if len(self._timestamps) < self.max_requests:
            return 0.0
        oldest = self._timestamps[0]
        return max(0.0, self.window_seconds - (time.monotonic() - oldest))


# ── Client ────────────────────────────────────────────────────────────────

# Polymarket public API endpoints
GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"


class PolymarketClient:
    """Async client for Polymarket public data.

    Uses httpx directly (no SDK dependency required for read-only operations).
    For trading, use the official polymarket-client SDK.
    """

    def __init__(
        self,
        rate_limit: int = 100,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self._rate_limiter = RateLimiter(max_requests=rate_limit)
        self._timeout = timeout
        self._max_retries = max_retries
        self._markets_cache: dict[str, Any] = {}
        self._cache_ttl: float = 60.0
        self._cache_timestamp: float = 0.0

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any] | None:
        """Make an HTTP request with rate limiting and retries."""
        import httpx

        for attempt in range(self._max_retries):
            if not self._rate_limiter.acquire():
                wait = self._rate_limiter.wait_time()
                logger.warning("Rate limited, waiting %.1fs", wait)
                await asyncio.sleep(wait)

            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.request(method, url, **kwargs)

                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", 5))
                        logger.warning("429 Too Many Requests, retry after %.1fs", retry_after)
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException:
                logger.warning("Request timeout (attempt %d/%d)", attempt + 1, self._max_retries)
                await asyncio.sleep(1 * (attempt + 1))

            except httpx.HTTPStatusError as e:
                logger.error("HTTP %d: %s", e.response.status_code, e.response.text[:200])
                if e.response.status_code >= 500:
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                return None

            except Exception as e:
                logger.error("Request failed: %s", e)
                await asyncio.sleep(1 * (attempt + 1))

        logger.error("All %d retries exhausted for %s", self._max_retries, url)
        return None

    # ── Market Data ────────────────────────────────────────────────────

    async def list_markets(
        self,
        closed: bool = False,
        limit: int = 50,
        offset: int = 0,
        order: str = "volume24hr",
        ascending: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch active markets from Polymarket."""
        params = {
            "closed": str(closed).lower(),
            "limit": str(limit),
            "offset": str(offset),
            "order": order,
            "ascending": str(ascending).lower(),
        }
        result = await self._request("GET", f"{GAMMA_API}/markets", params=params)
        return result if isinstance(result, list) else []

    async def get_market(self, condition_id: str) -> dict[str, Any] | None:
        """Get a specific market by condition ID."""
        result = await self._request("GET", f"{GAMMA_API}/markets/{condition_id}")
        return result if isinstance(result, dict) else None

    async def search_markets(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search markets by keyword."""
        params = {"query": query, "limit": str(limit)}
        result = await self._request("GET", f"{GAMMA_API}/markets", params=params)
        return result if isinstance(result, list) else []

    async def get_order_book(self, token_id: str) -> dict[str, Any] | None:
        """Get order book for a specific token."""
        result = await self._request("GET", f"{CLOB_API}/book", params={"token_id": token_id})
        return result if isinstance(result, dict) else None

    async def get_price(self, token_id: str) -> float | None:
        """Get current price for a token."""
        result = await self._request("GET", f"{CLOB_API}/price", params={"token_id": token_id})
        if result and "price" in result:
            return float(result["price"])
        return None

    async def get_prices(self, token_ids: list[str]) -> dict[str, float]:
        """Get prices for multiple tokens."""
        prices = {}
        for token_id in token_ids:
            price = await self.get_price(token_id)
            if price is not None:
                prices[token_id] = price
        return prices

    async def get_markets_with_prices(
        self,
        min_volume: float = 1000.0,
        min_liquidity: float = 500.0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get markets with current prices, filtered by volume and liquidity."""
        markets = await self.list_markets(limit=limit)
        enriched = []

        for market in markets:
            try:
                volume = float(market.get("volume24hr", 0) or 0)
                liquidity = float(market.get("liquidity", 0) or 0)

                if volume < min_volume or liquidity < min_liquidity:
                    continue

                # Get token IDs for this market
                tokens = market.get("tokens", [])
                if not tokens:
                    continue

                prices = {}
                for token in tokens:
                    token_id = token.get("token_id")
                    if token_id:
                        price = await self.get_price(token_id)
                        if price is not None:
                            prices[token_id] = price

                market["current_prices"] = prices
                enriched.append(market)

            except Exception as e:
                logger.warning("Failed to enrich market %s: %s", market.get("condition_id"), e)
                continue

        return enriched

    # ── Utility ────────────────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Check API health."""
        start = time.monotonic()
        markets = await self.list_markets(limit=1)
        latency = (time.monotonic() - start) * 1000

        return {
            "status": "ok" if markets else "error",
            "latency_ms": round(latency, 1),
            "markets_available": len(markets) > 0,
        }


# ── Singleton ─────────────────────────────────────────────────────────────

_client: PolymarketClient | None = None


def get_client() -> PolymarketClient:
    """Get or create the singleton Polymarket client."""
    global _client
    if _client is None:
        _client = PolymarketClient()
    return _client
