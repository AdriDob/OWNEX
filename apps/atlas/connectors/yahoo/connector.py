"""Yahoo Finance Connector — free quotes via yfinance.

No API key required. 100% free, unlimited requests.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.yahoo")


class YahooConnector(AtlasConnector):
    connector_id = "yahoo"
    display_name = "Yahoo Finance"

    def __init__(self) -> None:
        self._yf: Any = None

    async def connect(self) -> bool:
        try:
            import yfinance as yf
            self._yf = yf
            logger.info("Yahoo Finance connector ready (free tier)")
            return True
        except ImportError:
            logger.warning("yfinance not installed — run: pip install yfinance")
            return False
        except Exception as exc:
            logger.error("Yahoo connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        self._yf = None

    async def health(self) -> ConnectorHealth:
        try:
            start = time.time()
            if self._yf is None:
                return ConnectorHealth(connected=False, error="Not connected")
            ticker = self._yf.Ticker("SPY")
            info = ticker.info
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected="currentPrice" in info, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        return None  # Yahoo doesn't hold portfolios

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        if self._yf is None:
            return None
        try:
            ticker = self._yf.Ticker(symbol)
            info = ticker.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            if price is None:
                return None
            return NormalizedPrice(
                symbol=symbol,
                price=float(price),
                currency=info.get("currency", "USD"),
                change_24h=info.get("regularMarketChangePercent"),
                volume_24h=info.get("regularMarketVolume"),
                source="yahoo",
            )
        except Exception as exc:
            logger.warning("Yahoo quote failed for %s: %s", symbol, exc)
            return None

    async def search_symbols(self, query: str) -> list[dict]:
        if self._yf is None:
            return []
        try:
            tickers = self._yf.Tickers(query)
            results = []
            if hasattr(tickers, "symbols") and tickers.symbols:
                for sym in tickers.symbols[:10]:
                    results.append({"symbol": sym, "name": "", "type": "stock"})
            return results
        except Exception:
            return []

    async def get_config_fields(self) -> list[dict]:
        return []  # No config needed — free and open
