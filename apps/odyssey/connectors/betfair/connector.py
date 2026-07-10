"""Betfair Connector — REST API (read-only, analytical)."""

from __future__ import annotations

import logging
import os
import time

import httpx

from apps.odyssey.connectors.base import OdysseyConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedBet, NormalizedMarket

logger = logging.getLogger("orion.odyssey.connectors.betfair")

BETFAIR_API = os.environ.get("BETFAIR_API_URL", "https://api.betfair.com/exchange/betting/rest/v1.0")


class BetfairConnector(OdysseyConnector):
    connector_id = "betfair"
    display_name = "Betfair Exchange"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._session_token: str | None = None

    async def connect(self) -> bool:
        app_key = os.environ.get("BETFAIR_APP_KEY", "")
        username = os.environ.get("BETFAIR_USERNAME", "")
        password = os.environ.get("BETFAIR_PASSWORD", "")
        if not app_key:
            logger.warning("BETFAIR_APP_KEY not set")
            return False

        self._client = httpx.AsyncClient(
            base_url=BETFAIR_API,
            headers={"X-Application": app_key, "Accept": "application/json"},
            timeout=15,
        )

        # Login via identity API
        if username and password:
            try:
                login_url = "https://identitysso-cert.betfair.com/api/certlogin"
                resp = await self._client.post(login_url, data={"username": username, "password": password})
                if resp.status_code == 200:
                    data = resp.json()
                    self._session_token = data.get("sessionToken")
                    if self._session_token:
                        self._client.headers["X-Authentication"] = self._session_token
                        logger.info("Betfair connected")
                        return True
            except Exception as exc:
                logger.warning("Betfair login failed: %s", exc)
                return False

        logger.warning("Betfair credentials not configured — using anonymous mode")
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
            resp = await self._client.post("/listEventTypes", json={"filter": {}})
            latency = (time.time() - start) * 1000
            return ConnectorHealth(connected=resp.status_code == 200, latency_ms=round(latency, 1))
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_bets(self, since_days: int = 30) -> list[NormalizedBet]:
        return []

    async def get_markets(self, sport: str = "") -> list[NormalizedMarket]:
        return []

    async def get_balance(self) -> float:
        return 0.0

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "BETFAIR_APP_KEY", "label": "App Key", "type": "password"},
            {"key": "BETFAIR_USERNAME", "label": "Username", "type": "text"},
            {"key": "BETFAIR_PASSWORD", "label": "Password", "type": "password"},
        ]
