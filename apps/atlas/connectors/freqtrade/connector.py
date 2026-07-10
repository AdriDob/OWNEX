"""Freqtrade Connector — REST API to a running Freqtrade instance."""

from __future__ import annotations

import logging
import os
import time

import httpx

from apps.atlas.connectors.base import AtlasConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedPortfolio, NormalizedPosition, NormalizedPrice, NormalizedTransaction

logger = logging.getLogger("orion.atlas.connectors.freqtrade")

FREQTRADE_URL = os.environ.get("FREQTRADE_API_URL", "http://localhost:8080/api/v1")


class FreqtradeConnector(AtlasConnector):
    connector_id = "freqtrade"
    display_name = "Freqtrade"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> bool:
        self._client = httpx.AsyncClient(base_url=FREQTRADE_URL, timeout=10)
        try:
            resp = await self._client.get("/ping")
            ok = resp.status_code == 200
            if ok:
                logger.info("Freqtrade connected at %s", FREQTRADE_URL)
            return ok
        except Exception as exc:
            logger.warning("Freqtrade connect failed: %s", exc)
            return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health(self) -> ConnectorHealth:
        try:
            start = time.time()
            if self._client is None:
                return ConnectorHealth(connected=False, error="Not connected")
            resp = await self._client.get("/ping")
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_portfolio(self) -> NormalizedPortfolio | None:
        if self._client is None:
            return None
        try:
            resp = await self._client.get("/trades", params={"limit": 100})
            if resp.status_code != 200:
                return None
            data = resp.json()
            positions = []
            total_value = 0.0
            for trade in data.get("trades", []):
                val = float(trade.get("current_profit", 0)) * float(trade.get("stake_amount", 0))
                total_value += val
                positions.append(NormalizedPosition(
                    symbol=trade.get("pair", ""),
                    asset_type="crypto",
                    quantity=float(trade.get("amount", 0)),
                    avg_price=float(trade.get("open_rate", 0)),
                    current_price=float(trade.get("current_rate", 0)),
                    value=val,
                    pnl_percent=float(trade.get("current_profit", 0)) * 100,
                ))
            return NormalizedPortfolio(total_value=total_value, positions=positions, provider="freqtrade")
        except Exception as exc:
            logger.warning("Freqtrade portfolio failed: %s", exc)
            return None

    async def get_transactions(self, since_days: int = 30) -> list[NormalizedTransaction]:
        return []

    async def get_quote(self, symbol: str) -> NormalizedPrice | None:
        return None

    async def search_symbols(self, query: str) -> list[dict]:
        return []

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "FREQTRADE_API_URL", "label": "API URL", "type": "text", "default": "http://localhost:8080/api/v1"},
        ]
