"""YesWeHack Adapter — Security Work Cycle.

Uses GitHub bounty-targets-data (arkadiyt) as primary source with real payout data.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.yeswehack")

BOUNTY_TARGETS_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/yeswehack_data.json"


class YesWeHackAdapter(OpportunityAdapter):
    """Adapter for YesWeHack bug bounty programs.

    Uses curated bounty-targets-data from GitHub for program discovery with real payout data.
    """

    platform: str = "yeswehack"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("yeswehack")
        self._token = creds.get("api_key") or os.environ.get("YESWEHACK_API_KEY", "")
        self._enabled = bool(self._token)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch YesWeHack programs with active bounties and real payout data."""
        raw_opps: list[RawOpportunity] = []
        programs = await self._fetch_from_bounty_targets()

        for prog in programs:
            if not prog.get("has_rewards"):
                continue

            raw_opps.append(
                RawOpportunity(
                    id=f"yeswehack_{prog.get('id', prog.get('name', ''))}",
                    name=prog.get("name", ""),
                    description=prog.get("description", "") or f"YesWeHack program: {prog.get('name', '')}",
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

    async def _fetch_from_bounty_targets(self) -> list[dict[str, Any]]:
        """Fetch curated YesWeHack programs from GitHub bounty-targets-data."""
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(BOUNTY_TARGETS_URL, headers={"Accept": "application/json"}, timeout=20)
                if resp.status_code != 200:
                    logger.warning("YesWeHack bounty-targets-data: HTTP %s", resp.status_code)
                    return results

                items = resp.json() if isinstance(resp.json(), list) else []

                for item in items:
                    name = item.get("name", "")
                    if not name:
                        continue

                    program_id = item.get("id", name.lower().replace(" ", "-"))
                    max_bounty = item.get("max_bounty", 0)
                    public = item.get("public", False)

                    domains: list[str] = []
                    wildcards: list[str] = []
                    targets = item.get("targets", {})
                    for asset in targets.get("in_scope", []):
                        asset_id = asset.get("target", asset.get("asset_identifier", ""))
                        if asset_id:
                            if asset_id.startswith("*."):
                                wildcards.append(asset_id[2:])
                            else:
                                domains.append(asset_id)

                    prog = {
                        "id": program_id,
                        "name": name,
                        "description": item.get("description", ""),
                        "platform": "yeswehack",
                        "scope_url": item.get("scope_url", item.get("url", "")),
                        "has_rewards": (max_bounty or 0) > 0 and public,
                        "program_url": item.get("public_url", f"https://yeswehack.com/programs/{program_id}"),
                        "domains": domains,
                        "wildcards": wildcards,
                        "technologies": item.get("technologies", []),
                        "estimated_payout": float(max_bounty) if max_bounty else 0.0,
                        "estimated_effort_hours": self._estimate_effort_from_payout(
                            float(max_bounty) if max_bounty else 0
                        ),
                        "created_at": item.get("created_at", ""),
                    }
                    results.append(prog)

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning("YesWeHack bounty-targets-data error: %s", e)
            except Exception as e:
                logger.warning("YesWeHack unexpected error: %s", e)

        logger.info("YesWeHack bounty-targets-data: %d programs scraped", len(results))
        return results

    def _estimate_effort_from_payout(self, payout: float) -> float:
        if payout >= 10000:
            return 20.0
        elif payout >= 5000:
            return 12.0
        elif payout >= 1000:
            return 8.0
        elif payout >= 500:
            return 5.0
        return 3.0
