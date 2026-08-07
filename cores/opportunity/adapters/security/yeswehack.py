"""YesWeHack Adapter — Security Work Cycle.

European bug bounty platform (EUR payouts). Public API for program discovery.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.yeswehack")

YESWEHACK_API = "https://api.yeswehack.com/public"


class YesWeHackAdapter(OpportunityAdapter):
    """Adapter for YesWeHack bug bounty programs."""

    platform: str = "yeswehack"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("yeswehack")
        self._token = creds.get("api_key") or os.environ.get("YESWEHACK_API_KEY", "")
        self._enabled = bool(self._token)

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch YesWeHack programs."""
        raw_opps: list[RawOpportunity] = []
        programs = await self._fetch_programs(max_pages=2)

        for prog in programs:
            if not prog.get("has_rewards"):
                continue

            raw_opps.append(
                RawOpportunity(
                    id=f"yeswehack_{prog.get('id', prog.get('title', ''))}",
                    name=prog.get("title", prog.get("name", "")),
                    description=prog.get("description", "") or f"YesWeHack program: {prog.get('title', '')}",
                    platform="yeswehack",
                    url=prog.get("program_url", ""),
                    reward=prog.get("estimated_payout", 0.0),
                    effort_hours=prog.get("estimated_effort_hours", 4.0),
                    tags=prog.get("technologies", ["bug-bounty"]),
                    cycle="security",
                    source_type="platform",
                    source_name="yeswehack",
                    metadata={"original": prog, "personal": personal},
                    created_at=prog.get("created_at", ""),
                )
            )

        logger.info("YesWeHackAdapter: fetched %d opportunities", len(raw_opps))
        return raw_opps

    async def _fetch_programs(self, max_pages: int = 2) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            for page in range(max_pages):
                try:
                    url = f"{YESWEHACK_API}/programs?page={page + 1}&per_page=50"
                    resp = await client.get(url, headers=self._headers(), timeout=15)
                    if resp.status_code != 200:
                        logger.warning("YesWeHack page %d: HTTP %s", page + 1, resp.status_code)
                        continue

                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("items", data.get("data", []))

                    for item in items:
                        name = item.get("title", item.get("name", ""))
                        if not name:
                            continue

                        payout_text = item.get("reward_range", "")
                        estimated_payout = self._parse_payout(payout_text)

                        prog = {
                            "id": item.get("id", name.lower().replace(" ", "-")),
                            "title": name,
                            "description": item.get("description", ""),
                            "platform": "yeswehack",
                            "scope_url": item.get("scope_url", item.get("url", "")),
                            "has_rewards": True,
                            "program_url": item.get("public_url", ""),
                            "technologies": item.get("technologies", []),
                            "raw_payout_range": payout_text,
                            "estimated_payout": estimated_payout,
                            "estimated_effort_hours": self._estimate_effort(estimated_payout),
                            "created_at": item.get("created_at", ""),
                        }
                        results.append(prog)

                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    logger.warning("YesWeHack page %d error: %s", page + 1, e)
                    continue
                except Exception as e:
                    logger.warning("YesWeHack unexpected error: %s", e)
                    continue

        logger.info("YesWeHack: %d programs scraped", len(results))
        return results

    def _parse_payout(self, text: str) -> float:
        import re

        if not text:
            return 0.0
        amounts = re.findall(r"[\d,]+(?:\.\d+)?", str(text).replace(",", ""))
        parsed = [float(a) for a in amounts if a.replace(".", "").isdigit()]
        return max(parsed) if parsed else 0.0

    def _estimate_effort(self, payout: float) -> float:
        if payout >= 10000:
            return 20.0
        elif payout >= 5000:
            return 12.0
        elif payout >= 1000:
            return 8.0
        elif payout >= 500:
            return 5.0
        return 3.0
