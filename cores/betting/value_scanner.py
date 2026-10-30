"""Value Betting Scanner — detects line movement and price discrepancies.

Scans TheOddsAPI + Polymarket Gamma for line movement and price discrepancies.
Outputs ValueSignal with edge_bps and metadata. Pure, testable, no network in tests.
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger("ownex.betting.value_scanner")


@dataclass(slots=True, frozen=True)
class ValueSignal:
    """A value betting signal with edge and metadata."""

    market_id: str
    sport: str
    event: str
    best_book: str
    best_price: Decimal
    consensus_price: Decimal
    edge_bps: int
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def edge_pct(self) -> float:
        return float(self.edge_bps) / 100.0


class ValueScanner:
    """Scans for value bets across sportsbooks and exchanges."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ValueScanner:
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def scan_the_odds_api(self, api_key: str, sports: list[str] | None = None) -> list[ValueSignal]:
        """Scan TheOddsAPI for line movement and value."""
        if not api_key:
            logger.warning("THE_ODDS_API_KEY not set")
            return []

        sports = sports or ["americanfootball_nfl", "basketball_nba", "icehockey_nhl", "soccer_epl"]
        signals: list[ValueSignal] = []

        for sport in sports:
            try:
                markets = await self._fetch_odds_api_markets(sport, api_key)
                signals.extend(self._analyze_odds_markets(markets))
            except Exception as exc:
                logger.warning("TheOddsAPI scan failed for %s: %s", sport, exc)

        return signals

    async def _fetch_odds_api_markets(self, sport: str, api_key: str) -> list[dict]:
        """Fetch markets from TheOddsAPI."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://api.the-odds-api.com/v4/sports/upcoming/odds",
                params={
                    "apiKey": os.environ.get("THE_ODDS_API_KEY", ""),
                    "regions": "us,uk,eu",
                    "markets": "h2h,spreads,totals",
                    "oddsFormat": "decimal",
                },
                timeout=30.0,
            )
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
                            markets.append(
                                {
                                    "event_id": event.get("id"),
                                    "sport": event.get("sport_title", ""),
                                    "home": event.get("home_team", ""),
                                    "away": event.get("away_team", ""),
                                    "bookmaker": bookmaker.get("key", ""),
                                    "bookmaker_title": bookmaker.get("title", ""),
                                    "market_key": market.get("key", ""),
                                    "outcomes": outcomes,
                                    "commence_time": event.get("commence_time"),
                                }
                            )
            return markets

    def _analyze_odds_markets(self, markets: list[dict]) -> list[ValueSignal]:
        """Analyze markets for line movement and value."""
        from collections import defaultdict
        from decimal import Decimal

        # Group by event
        by_event: dict[str, list[dict]] = defaultdict(list)
        for m in markets:
            by_event[m["event_id"]].append(m)

        signals: list[ValueSignal] = []

        for event_id, markets_list in by_event.items():
            if len(markets_list) < 2:
                continue

            # Use first market for event metadata
            first_market = markets_list[0]

            # Find best price across books for each outcome
            best_prices: dict[str, dict] = {}  # outcome_name -> {price, book}
            for m in markets_list:
                for out in m["outcomes"]:
                    name = out.get("name", "")
                    price = Decimal(str(out.get("price", 0)))
                    if price <= 0:
                        continue
                    if name not in best_prices or price > best_prices[name]["price"]:
                        best_prices[name] = {"price": price, "book": m["bookmaker"]}

            if len(best_prices) < 2:
                continue

            # Calculate consensus (median of best prices)
            prices = [v["price"] for v in best_prices.values()]
            consensus = Decimal(str(sorted(prices)[len(prices) // 2]))

            # Find edges
            for outcome, data in best_prices.items():
                best_price = data["price"]
                if consensus > 0:
                    edge_bps = int(((best_price - consensus) / consensus) * 10000)
                    if edge_bps >= 50:  # 50 bps minimum edge
                        signals.append(
                            ValueSignal(
                                market_id=f"{first_market.get('event_id', '')}_{first_market.get('sport', '')}",
                                sport=first_market.get("sport", ""),
                                event=f"{first_market.get('home', '')} vs {first_market.get('away', '')}",
                                best_book=data["book"],
                                best_price=best_price,
                                consensus_price=consensus,
                                edge_bps=edge_bps,
                                timestamp=datetime.now(UTC).isoformat(),
                                metadata={"outcome": outcome},
                            )
                        )

        return signals

    async def scan_polymarket(self) -> list[ValueSignal]:
        """Scan Polymarket Gamma API for discrepancies."""
        # TODO: implement Polymarket Gamma scan
        return []


def defaultdict_factory() -> defaultdict:
    from collections import defaultdict

    return defaultdict(list)


# Need to import at top level
