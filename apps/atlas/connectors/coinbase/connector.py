"""Coinbase Connector — REST API wrapper (free tier available)."""

from __future__ import annotations

import logging
import os
import time

import httpx

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPosition, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.coinbase")

BASE_URL = "https://api.coinbase.com"


class CoinbaseConnector(AtlasConnector):
    connector_id = "coinbase"
    display_name = "Coinbase"

    def __init__(self) -> None:
        self._api_key = os.environ.get("COINBASE_API_KEY", "")
        self._secret = os.environ.get("COINBASE_SECRET", "")
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        if not self._api_key:
            logger.warning("Coinbase not configured: set COINBASE_API_KEY")
            return False
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)
        logger.info("Coinbase connector initialized")
        return True

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health(self) -> ConnectorHealth:
        try:
            start = time.time()
            if self._client is None:
                return ConnectorHealth(connected=False, error="Not connected")
            resp = await self._client.get("/api/v3/brokerage/time")
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        if self._client is None:
            return None
        try:
            resp = await self._client.get("/v2/accounts", headers=self._auth_headers("GET", "/v2/accounts"))
            if resp.status_code != 200:
                return None
            data = resp.json()
            positions = []
            total_value = 0.0
            for acc in data.get("data", []):
                balance = float(acc.get("balance", {}).get("amount", 0))
                if balance > 0:
                    currency = acc.get("currency", "")
                    positions.append(NormalizedPosition(
                        symbol=currency,
                        name=acc.get("name", currency),
                        asset_type="crypto",
                        quantity=balance,
                        value=balance,
                    ))
                    total_value += balance
            return NormalizedPortfolio(total_value=total_value, positions=positions, provider="coinbase")
        except Exception as exc:
            logger.warning("Coinbase portfolio failed: %s", exc)
            return None

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "COINBASE_API_KEY", "label": "API Key", "type": "password"},
            {"key": "COINBASE_SECRET", "label": "Secret", "type": "password"},
        ]

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict:
        timestamp = str(int(time.time()))
        # Real Coinbase uses CB-ACCESS-SIGN header with HMAC
        return {
            "CB-ACCESS-KEY": self._api_key,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
        }
