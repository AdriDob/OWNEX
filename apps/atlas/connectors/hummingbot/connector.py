"""Hummingbot Connector — REST API to a running Hummingbot instance."""

from __future__ import annotations

import logging
import os
import time

import httpx

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.hummingbot")

HUMBINGOT_URL = os.environ.get("HUMBINGOT_API_URL", "http://localhost:15871")


class HummingbotConnector(AtlasConnector):
    connector_id = "hummingbot"
    display_name = "Hummingbot"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        self._client = httpx.AsyncClient(base_url=HUMBINGOT_URL, timeout=10)
        logger.info("Hummingbot connector initialized")
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
            resp = await self._client.get("/status")
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        return None

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "HUMBINGOT_API_URL", "label": "API URL", "type": "text", "default": "http://localhost:15871"},
        ]
