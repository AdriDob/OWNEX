"""Kraken Connector — REST API wrapper."""

from __future__ import annotations

import logging
import os
import time

import httpx

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.kraken")

BASE_URL = "https://api.kraken.com"


class KrakenConnector(AtlasConnector):
    connector_id = "kraken"
    display_name = "Kraken"

    def __init__(self) -> None:
        self._api_key = os.environ.get("KRAKEN_API_KEY", "")
        self._secret = os.environ.get("KRAKEN_SECRET", "")
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        if not self._api_key:
            logger.warning("Kraken not configured: set KRAKEN_API_KEY")
            return False
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)
        logger.info("Kraken connector initialized")
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
            resp = await self._client.get("/0/public/Time")
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        return None  # TODO: implement with Kraken's private API

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "KRAKEN_API_KEY", "label": "API Key", "type": "password"},
            {"key": "KRAKEN_SECRET", "label": "Secret", "type": "password"},
        ]
