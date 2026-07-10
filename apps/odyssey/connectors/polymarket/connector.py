"""Polymarket Connector — read-only access to prediction markets.

Uses Polymarket CLOB API (no key needed) + Gamma API for market data.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from apps.odyssey.connectors.base import OdysseyConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedBet, NormalizedMarket

logger = logging.getLogger("orion.odyssey.connectors.polymarket")

CLOB_API = "https://clob.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


class PolymarketConnector(OdysseyConnector):
    connector_id = "polymarket"
    display_name = "Polymarket"

    def __init__(self) -> None:
        self._client_clob: httpx.AsyncClient | None = None
        self._client_gamma: httpx.AsyncClient | None = None
        self._api_key: str = ""

    async def connect(self) -> bool:
        self._client_clob = httpx.AsyncClient(base_url=CLOB_API, timeout=15)
        self._client_gamma = httpx.AsyncClient(base_url=GAMMA_API, timeout=15)
        logger.info("Polymarket connector ready (no API key needed for public data)")
        return True

    async def disconnect(self) -> None:
        for client in (self._client_clob, self._client_gamma):
            if client:
                await client.aclose()

    async def health(self) -> ConnectorHealth:
        try:
            start = time.time()
            if not self._client_gamma:
                return ConnectorHealth(connected=False, error="Not connected")
            resp = await self._client_gamma.get("/markets", params={"limit": 1})
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_bets(self, since_days: int = 30) -> list[NormalizedBet]:
        return []

    async def get_markets(self, sport: str = "") -> list[NormalizedMarket]:
        if not self._client_gamma:
            return []
        try:
            params: dict[str, Any] = {"limit": 50, "closed": "false"}
            if sport:
                params["tag"] = sport
            resp = await self._client_gamma.get("/markets", params=params)
            if resp.status_code != 200:
                return []
            data = resp.json()
            markets = []
            for m in data:
                outcome_prices = m.get("outcomePrices", [])
                yes_price = float(outcome_prices[0]) if outcome_prices else 0.0
                no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 else 0.0
                volume = m.get("volume", 0)
                if isinstance(volume, str):
                    volume = float(volume)
                markets.append(NormalizedMarket(
                    name=m.get("question", m.get("name", "")),
                    sport=m.get("category", "prediction"),
                    event=m.get("question", ""),
                    odds_home=1.0 / yes_price if yes_price > 0 else 0.0,
                    odds_away=1.0 / no_price if no_price > 0 else 0.0,
                    volume=float(volume),
                    platform="polymarket",
                ))
            return markets
        except Exception as exc:
            logger.warning("Polymarket markets failed: %s", exc)
            return []

    async def get_balance(self) -> float:
        return 0.0

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "POLYMARKET_API_KEY", "label": "API Key (optional)", "type": "password"},
        ]
