"""Intigriti Adapter — Security Work Cycle.

Uses GitHub bounty-targets-data (arkadiyt) as primary source with real payout data.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.intigriti")

BOUNTY_TARGETS_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/intigriti_data.json"


class IntigritiAdapter(OpportunityAdapter):
    """Adapter for Intigriti bug bounty programs.

    Uses curated bounty-targets-data from GitHub for program discovery with real payout data.
    """

    platform: str = "intigriti"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("intigriti")
        self._token = creds.get("api_key") or os.environ.get("INTIGRITI_API_KEY", "")
        self._enabled = bool(self._token)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Intigriti programs with active bounties and real payout data."""
        raw_opps: list[RawOpportunity] = []
        programs = await self._fetch_from_bounty_targets()

        for prog in programs:
            if not prog.get("has_rewards"):
                continue

            raw_opps.append(
                RawOpportunity(
                    id=f"intigriti_{prog.get('id', prog.get('handle', ''))}",
                    name=prog.get("name", ""),
                    description=prog.get("description", "") or f"Intigriti program: {prog.get('name', '')}",
                    platform="intigriti",
                    url=prog.get("program_url", ""),
                    reward=prog.get("estimated_payout", 0.0),
                    effort_hours=prog.get("estimated_effort_hours", 4.0),
                    tags=prog.get("technologies", ["bug-bounty"]),
                    cycle="security",
                    source_type="platform",
                    source_name="intigriti",
                    metadata={"original": prog, "personal": personal},
                    created_at=prog.get("created_at", ""),
                )
            )

        logger.info("IntigritiAdapter: fetched %d opportunities", len(raw_opps))
        return raw_opps

    async def _fetch_from_bounty_targets(self) -> list[dict[str, Any]]:
        """Fetch curated Intigriti programs from GitHub bounty-targets-data."""
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(BOUNTY_TARGETS_URL, headers={"Accept": "application/json"}, timeout=20)
                if resp.status_code != 200:
                    logger.warning("Intigriti bounty-targets-data: HTTP %s", resp.status_code)
                    return results

                items = resp.json() if isinstance(resp.json(), list) else []

                for item in items:
                    name = item.get("name", item.get("programName", item.get("title", "")))
                    if not name:
                        continue

                    program_id = item.get("id", item.get("handle", name.lower().replace(" ", "-")))
                    handle = item.get("handle", program_id)
                    max_bounty = item.get("max_bounty", {})
                    max_payout = 0
                    if isinstance(max_bounty, dict):
                        max_payout = max_bounty.get("value", 0)
                    elif isinstance(max_bounty, (int, float)):
                        max_payout = max_bounty

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
                        "handle": handle,
                        "description": item.get("description", ""),
                        "platform": "intigriti",
                        "scope_url": item.get("scopeUrl", item.get("url", "")),
                        "has_rewards": max_payout > 0,
                        "program_url": item.get("publicUrl", item.get("url", f"https://www.intigriti.com/programs/{handle}")),
                        "domains": domains,
                        "wildcards": wildcards,
                        "technologies": item.get("technologies", []),
                        "estimated_payout": float(max_payout) if max_payout else 0.0,
                        "estimated_effort_hours": self._estimate_effort_from_payout(float(max_payout) if max_payout else 0),
                        "created_at": item.get("createdAt", item.get("date", "")),
                    }
                    results.append(prog)

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning("Intigriti bounty-targets-data error: %s", e)
            except Exception as e:
                logger.warning("Intigriti unexpected error: %s", e)

        logger.info("Intigriti bounty-targets-data: %d programs scraped", len(results))
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
