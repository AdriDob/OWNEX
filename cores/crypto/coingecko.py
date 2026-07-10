"""CoinGecko price feed — unified price oracle for all crypto assets.

Free tier (100 calls/min, 10k/month) at api.coingecko.com/api/v3.
No API key required for demo.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request

from cores.crypto.base import cache_usd_price

logger = logging.getLogger("cateye.crypto.coingecko")

BASE_URL = "https://api.coingecko.com/api/v3"

# CoinGecko IDs for common assets
COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "SOL": "solana",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "ARB": "arbitrum",
    "OP": "optimism",
    "APT": "aptos",
    "SUI": "sui",
    "NEAR": "near",
    "FET": "fetch-ai",
    "RENDER": "render-token",
    "INJ": "injective-protocol",
    "TIA": "celestia",
    "SEI": "sei-network",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
}

# Reverse lookup: CoinGecko ID -> symbol
_ID_TO_SYMBOL = {v: k for k, v in COINGECKO_IDS.items()}


class CoinGeckoFeed:
    """Price feed from CoinGecko with in-memory cache."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[dict, float]] = {}  # symbol -> (data, timestamp)
        self._cache_ttl = 60  # seconds
        self._last_call = 0.0
        self._min_interval = 1.5  # sec between calls (respect rate limit)

    def get_price(self, symbol: str, vs_currency: str = "usd") -> float:
        """Get current USD price for a single symbol."""
        data = self._get(symbol, vs_currency)
        if data:
            return data.get(vs_currency, 0.0)
        return 0.0

    def get_prices(self, symbols: list[str], vs_currency: str = "usd") -> dict[str, float]:
        """Get current prices for multiple symbols at once."""
        coin_ids = [COINGECKO_IDS.get(s.upper(), s.lower()) for s in symbols]
        prices = self._fetch_simple_price(coin_ids, vs_currency)
        result: dict[str, float] = {}
        for symbol, cid in COINGECKO_IDS.items():
            if cid in prices:
                result[symbol] = prices[cid].get(vs_currency, 0.0)
        # Also cache
        for symbol, cid in COINGECKO_IDS.items():
            if cid in prices:
                usd_price = prices[cid].get(vs_currency, 0.0)
                cache_usd_price(symbol, usd_price)
        return result

    def get_24h_change(self, symbol: str) -> float | None:
        """Get 24h price change percentage."""
        data = self._get(symbol)
        if data:
            return data.get(f"{list(data.keys())[0]}_24h_change") if len(data) == 1 else None
        return None

    def health(self) -> dict:
        """Check if CoinGecko API is reachable."""
        try:
            req = urllib.request.Request(f"{BASE_URL}/ping", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = resp.status == 200
            return {
                "available": ok,
                "cached_symbols": len(self._cache),
                "cache_ttl": self._cache_ttl,
            }
        except Exception as exc:
            return {"available": False, "error": str(exc), "cached_symbols": len(self._cache)}

    # ── Internal ─────────────────────────────────────

    def _get(self, symbol: str, vs_currency: str = "usd") -> dict | None:
        try:
            coin_id = COINGECKO_IDS.get(symbol.upper())
            if not coin_id:
                return None
            now = time.time()
            cached = self._cache.get(coin_id)
            if cached and (now - cached[1]) < self._cache_ttl:
                return cached[0]

            # Rate limit: ensure at least 1.5s between calls
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)

            result = self._fetch_simple_price([coin_id], vs_currency)
            coin_data = result.get(coin_id, {})
            self._cache[coin_id] = (coin_data, time.time())
            self._last_call = time.time()

            price = coin_data.get(vs_currency, 0.0)
            if price > 0:
                cache_usd_price(symbol.upper(), price)

            return coin_data
        except Exception as exc:
            logger.warning("CoinGecko price fetch failed for %s: %s", symbol, exc)
            return None

    def _fetch_simple_price(self, coin_ids: list[str], vs_currency: str = "usd") -> dict:
        ids_param = ",".join(coin_ids)
        url = f"{BASE_URL}/simple/price?ids={ids_param}&vs_currencies={vs_currency}&include_24hr_change=true"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            logger.warning("CoinGecko API error: %s", exc)
            return {}


_feed: CoinGeckoFeed | None = None


def get_coingecko_feed() -> CoinGeckoFeed:
    global _feed
    if _feed is None:
        _feed = CoinGeckoFeed()
    return _feed
