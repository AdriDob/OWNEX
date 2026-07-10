"""TheOddsAPI Connector — free sportsbook odds aggregation.

Free tier: 500 monthly requests, covers NFL, NBA, MLB, NHL, EPL, and more.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

from apps.odyssey.connectors.base import OdysseyConnector
from core.interfaces.connector import ConnectorHealth
from core.normalizer.base import NormalizedBet, NormalizedMarket

logger = logging.getLogger("orion.odyssey.connectors.the_odds_api")

BASE_URL = "https://api.the-odds-api.com/v4"


class OddsHarvesterConnector(OdysseyConnector):
    connector_id = "the_odds_api"
    display_name = "TheOddsAPI"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._api_key: str = ""

    async def connect(self) -> bool:
        self._api_key = os.environ.get("THE_ODDS_API_KEY", "")
        if not self._api_key:
            logger.warning("THE_ODDS_API_KEY not set — data fetches will fail")
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)
        logger.info("TheOddsAPI connector ready (free tier, 500 req/mo)")
        return True

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def health(self) -> ConnectorHealth:
        try:
            start = time.time()
            if not self._client or not self._api_key:
                return ConnectorHealth(connected=False, error="No API key")
            resp = await self._client.get("/sports", params={"apiKey": self._api_key})
            latency = (time.time() - start) * 1000
            return ConnectorHealth(
                connected=resp.status_code == 200,
                latency_ms=round(latency, 1),
                rate_limit_remaining=int(resp.headers.get("x-requests-remaining", 0)) if "x-requests-remaining" in resp.headers else None,
            )
        except Exception as exc:
            return ConnectorHealth(connected=False, error=str(exc))

    async def get_bets(self, since_days: int = 30) -> list[NormalizedBet]:
        return []

    async def get_markets(self, sport: str = "") -> list[NormalizedMarket]:
        if not self._client or not self._api_key:
            return []
        try:
            sport_key = sport or "upcoming"
            resp = await self._client.get(f"/sports/{sport_key}/odds", params={
                "apiKey": self._api_key,
                "regions": "us,uk,eu",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "decimal",
            })
            if resp.status_code != 200:
                logger.warning("TheOddsAPI returned %d", resp.status_code)
                return []
            data = resp.json()
            markets = []
            for event in data:
                for bookmaker in event.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        outcomes = market.get("outcomes", [])
                        if len(outcomes) >= 2:
                            markets.append(NormalizedMarket(
                                name=f"{event.get('home_team', '')} vs {event.get('away_team', '')}",
                                sport=event.get("sport_title", sport_key),
                                event=event.get("id", ""),
                                odds_home=float(outcomes[0].get("price", 0)),
                                odds_away=float(outcomes[1].get("price", 0)),
                                volume=0.0,
                                platform="the_odds_api",
                            ))
            return markets
        except Exception as exc:
            logger.warning("TheOddsAPI markets failed: %s", exc)
            return []

    async def get_balance(self) -> float:
        return 0.0

    async def get_config_fields(self) -> list[dict]:
        return [
            {"key": "THE_ODDS_API_KEY", "label": "API Key", "type": "password"},
        ]
