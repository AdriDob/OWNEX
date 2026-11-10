"""Exchange connectors — Binance, Coinbase, Kraken integration for OWNEX.

Provides unified interface for exchange API access, including:
- Balance fetching
- Ticker/price data
- Order placement (paper trading mode)
- Account management
- Rate limiting and error handling
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger("ownex.crypto.exchanges")

# ── Exchange Configuration ─────────────────────────────────────────────────

EXCHANGE_CONFIG = {
    "binance": {
        "base_url": "https://api.binance.com/api/v3",
        "endpoints": {
            "balance": "/account",
            "tickers": "/ticker/price",
            "account_info": "/account",
            "symbols": "/exchangeInfo",
        },
        "requires_api_key": True,
        "paper_trading": False,  # Binance doesn't offer simple paper trading via REST
    },
    "coinbase": {
        "base_url": "https://api.coinbase.com/v2/prices",
        "endpoints": {
            "balance": "/accounts",
            "spot_price": "/spot",
            "portfolio": "/portfolio",
        },
        "requires_api_key": True,
        "paper_trading": True,
    },
    "kraken": {
        "base_url": "https://api.kraken.com/0/public",
        "endpoints": {
            "balance": "/balance",
            "tickers": "/Ticker",
            "asset_info": "/Asset",
        },
        "requires_api_key": False,  # Public endpoints
        "paper_trading": True,
    },
}


# ── Base Connector Class ──────────────────────────────────────────────────


class ExchangeConnector:
    """Base class for exchange API connectors."""

    def __init__(self, exchange_id: str, api_key: str | None = None, secret: str | None = None):
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.secret = secret
        self.base_config = EXCHANGE_CONFIG.get(exchange_id, {})
        self.rate_limit = 1.0  # seconds between requests
        self._last_request = 0.0

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between API calls."""
        import time

        elapsed = asyncio.get_event_loop().time() - self._last_request
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            await asyncio.sleep(wait_time)
        self._last_request = asyncio.get_event_loop().time()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an authenticated API request."""
        await self._rate_limit()

        base_url = self.base_config.get("base_url", "https://api.example.com")
        url = f"{base_url}{endpoint}"

        headers = {}
        if self.api_key and self.base_config.get("requires_api_key"):
            headers["X-API-KEY"] = self.api_key
            if self.secret:
                headers["X-SECRET"] = self.secret

        # Placeholder - in production would use httpx/aiohttp
        logger.debug(f"Making {method} request to {url} with headers {headers}")
        return {"status": "placeholder", "data": {}}

    async def get_balance(self) -> dict[str, Any]:
        """Get account balance."""
        raise NotImplementedError

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Get ticker price for symbol."""
        raise NotImplementedError

    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio summary."""
        raise NotImplementedError


# ── Binance Connector ─────────────────────────────────────────────────────


class BinanceConnector(ExchangeConnector):
    """Binance exchange connector."""

    def __init__(self, api_key: str, secret: str, testnet: bool = True):
        super().__init__("binance", api_key, secret)
        self.base_url = "https://api.binance.us/api/v3" if not testnet else "https://testnet.binance.vision/api/v3"
        self.rate_limit = 2.0  # Binance is stricter

    async def get_balance(self) -> dict[str, Any]:
        """Get Balances from Binance."""
        await self._rate_limit()
        # In production would make real API call
        # resp = await client.get(f"{self.base_url}/account", headers=headers)
        return {
            "exchange": "binance",
            "balances": {
                "BTC": {"free": 1.5, "locked": 0.0},
                "ETH": {"free": 15.0, "locked": 0.0},
                "USDT": {"free": 5000.0, "locked": 0.0},
            },
            "total_usd": 25000.0,
        }

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Get ticker price from Binance."""
        await self._rate_limit()
        # Mock price data
        prices = {"BTCUSDT": 65000.0, "ETHUSDT": 3500.0, "SOLUSDT": 180.0}
        price = prices.get(symbol, 0.0)
        return {
            "exchange": "binance",
            "symbol": symbol,
            "price": price,
            "last_update": "2026-01-15T00:00:00Z",
        }

    async def get_portfolio(self) -> dict[str, Any]:
        """Get full portfolio from Binance."""
        balance = await self.get_balance()
        tickers: dict[str, dict[str, Any]] = {}
        for asset in balance["balances"]:
            symbol = f"{asset}USDT"
            tickers[asset] = await self.get_ticker(symbol)
        return {
            "exchange": "binance",
            "balances": balance["balances"],
            "tickers": tickers,
            "total_value_usd": balance["total_usd"],
        }


# ── Coinbase Connector ───────────────────────────────────────────────────


class CoinbaseConnector(ExchangeConnector):
    """Coinbase exchange connector."""

    def __init__(self, api_key: str, secret: str, use_base_url: str = "https://api.coinbase.com"):
        super().__init__("coinbase", api_key, secret)
        self.base_url = use_base_url

    async def get_balance(self) -> dict[str, Any]:
        """Get balances from Coinbase."""
        await self._rate_limit()
        # Mock balance data
        return {
            "exchange": "coinbase",
            "accounts": [
                {"id": "acct_1", "name": "BTC Wallet", "balance": {"amount": "1.5", "currency": "BTC"}},
                {"id": "acct_2", "name": "ETH Wallet", "balance": {"amount": "15.0", "currency": "ETH"}},
                {"id": "acct_3", "name": "USD Wallet", "balance": {"amount": "5000.0", "currency": "USD"}},
            ],
            "total_usd": 25000.0,
        }

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Get ticker from Coinbase."""
        await self._rate_limit()
        # Mock price data
        prices = {"BTC-USD": 65000.0, "ETH-USD": 3500.0, "SOL-USD": 180.0}
        price = prices.get(symbol, 0.0)
        return {
            "exchange": "coinbase",
            "product_id": symbol,
            "price": price,
            "last_update": "2026-01-15T00:00:00Z",
        }

    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio from Coinbase."""
        balance = await self.get_balance()
        tickers: dict[str, dict[str, Any]] = {}
        for account in balance["accounts"]:
            symbol = account["name"].replace(" Wallet", "-USD")
            tickers[account["id"]] = await self.get_ticker(symbol)
        return {
            "exchange": "coinbase",
            "accounts": balance["accounts"],
            "tickers": tickers,
            "total_value_usd": balance["total_usd"],
        }


# ── Kraken Connector ─────────────────────────────────────────────────────


class KrakenConnector(ExchangeConnector):
    """Kraken exchange connector."""

    def __init__(self, api_key: str | None = None, secret: str | None = None):
        super().__init__("kraken", api_key, secret)
        # Kraken public endpoints don't require API key

    async def get_balance(self) -> dict[str, Any]:
        """Get balances from Kraken (public endpoint)."""
        await self._rate_limit()
        # Mock balance data for supported assets
        return {
            "exchange": "kraken",
            "balances": {
                "XBT": {"free": 1.5, "locked": 0.0},
                "ETH": {"free": 15.0, "locked": 0.0},
                "SOL": {"free": 500.0, "locked": 0.0},  # SOL mapped to KAVA or similar
            },
            "total_usd": 25000.0,
        }

    async def get_ticker(self, symbol: str) -> dict[str, Any]:
        """Get ticker from Kraken."""
        await self._rate_limit()
        # Mock price data
        prices = {"BTC-USD": 65000.0, "ETH-USD": 3500.0, "SOL-USD": 180.0}
        price = prices.get(symbol, 0.0)
        return {
            "exchange": "kraken",
            "symbol": symbol,
            "price": price,
            "last_update": "2026-01-15T00:00:00Z",
        }

    async def get_portfolio(self) -> dict[str, Any]:
        """Get portfolio from Kraken."""
        balance = await self.get_balance()
        tickers: dict[str, dict[str, Any]] = {}
        for asset in balance["balances"]:
            symbol = f"{asset}-USD"
            tickers[asset] = await self.get_ticker(symbol)
        return {
            "exchange": "kraken",
            "balances": balance["balances"],
            "tickers": tickers,
            "total_value_usd": balance["total_usd"],
        }


# ── Connector Factory ─────────────────────────────────────────────────────


def get_exchange_connector(
    exchange: str,
    api_key: str | None = None,
    secret: str | None = None,
    **kwargs: Any,
) -> ExchangeConnector:
    """Factory function to create exchange connector by name."""
    connectors: dict[str, type[ExchangeConnector]] = {
        "binance": BinanceConnector,
        "coinbase": CoinbaseConnector,
        "kraken": KrakenConnector,
    }

    connector_class = connectors.get(exchange.lower())
    if not connector_class:
        raise ValueError(f"Unsupported exchange: {exchange}. Supported: {list(connectors.keys())}")

    return connector_class(api_key=api_key, secret=secret, **kwargs)


# ── Convenience Functions ─────────────────────────────────────────────────


def get_all_exchange_balances(
    binance_key: str | None = None,
    binance_secret: str | None = None,
    coinbase_key: str | None = None,
    coinbase_secret: str | None = None,
    kraken_key: str | None = None,
    kraken_secret: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Get balances from all exchanges concurrently.

    Placeholder implementation - in production would run async gather.
    """
    results: dict[str, dict[str, Any]] = {}

    if binance_key and binance_secret:
        try:
            binance = get_exchange_connector("binance", binance_key, binance_secret)
            results["binance"] = asyncio.get_event_loop().run_until_complete(binance.get_portfolio())
        except Exception as e:
            logger.error(f"Binance balance fetch error: {e}")
            results["binance"] = {"error": str(e)}

    if coinbase_key and coinbase_secret:
        try:
            coinbase = get_exchange_connector("coinbase", coinbase_key, coinbase_secret)
            results["coinbase"] = asyncio.get_event_loop().run_until_complete(coinbase.get_portfolio())
        except Exception as e:
            logger.error(f"Coinbase balance fetch error: {e}")
            results["coinbase"] = {"error": str(e)}

    if kraken_key or kraken_secret:
        try:
            kraken = get_exchange_connector("kraken", kraken_key, kraken_secret)
            results["kraken"] = asyncio.get_event_loop().run_until_complete(kraken.get_portfolio())
        except Exception as e:
            logger.error(f"Kraken balance fetch error: {e}")
            results["kraken"] = {"error": str(e)}

    # Add CoinGecko as fallback
    from cores.crypto.coingecko import get_coingecko_feed

    try:
        cg_feed = get_coingecko_feed()
        results["coingecko"] = {"total_usd": cg_feed.get("total_crypto_usd", 0.0)}
    except Exception:
        results["coingecko"] = {"total_usd": 0.0}

    return results


__all__ = [
    "ExchangeConnector",
    "BinanceConnector",
    "CoinbaseConnector",
    "KrakenConnector",
    "get_exchange_connector",
    "get_all_exchange_balances",
    "EXCHANGE_CONFIG",
]
