"""Bugcrowd Adapter — Security Work Cycle.

Uses GitHub bounty-targets-data (arkadiyt) as primary source with real payout data.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.bugcrowd")

BOUNTY_TARGETS_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/bugcrowd_data.json"


class BugcrowdAdapter(OpportunityAdapter):
    """Adapter for Bugcrowd bug bounty programs.

    Uses curated bounty-targets-data from GitHub for program discovery with real payout data.
    """

    platform: str = "bugcrowd"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("bugcrowd")
        self._token = creds.get("api_token") or os.environ.get("BUGCROWD_API_TOKEN", "")
        self._enabled = bool(self._token)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Bugcrowd programs with active bounties and real payout data."""
        raw_opps: list[RawOpportunity] = []
        programs = await self._fetch_from_bounty_targets()

        for prog in programs:
            if not prog.get("has_rewards"):
                continue

            raw_opps.append(
                RawOpportunity(
                    id=f"bugcrowd_{prog.get('code', prog.get('name', ''))}",
                    name=prog.get("name", ""),
                    description=prog.get("description", "") or f"Bugcrowd program: {prog.get('name', '')}",
                    platform="bugcrowd",
                    url=prog.get("program_url", ""),
                    reward=prog.get("estimated_payout", 0.0),
                    effort_hours=prog.get("estimated_effort_hours", 4.0),
                    tags=prog.get("technologies", ["bug-bounty"]),
                    cycle="security",
                    source_type="platform",
                    source_name="bugcrowd",
                    metadata={"original": prog, "personal": personal},
                    created_at=prog.get("created_at", ""),
                )
            )

        logger.info("BugcrowdAdapter: fetched %d opportunities", len(raw_opps))
        return raw_opps

    async def _fetch_from_bounty_targets(self) -> list[dict[str, Any]]:
        """Fetch curated Bugcrowd programs from GitHub bounty-targets-data."""
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(BOUNTY_TARGETS_URL, headers={"Accept": "application/json"}, timeout=20)
                if resp.status_code != 200:
                    logger.warning("Bugcrowd bounty-targets-data: HTTP %s", resp.status_code)
                    return results

                items = resp.json() if isinstance(resp.json(), list) else []

                for item in items:
                    name = item.get("name", "")
                    if not name:
                        continue

                    code = item.get("code", item.get("slug", item.get("handle", name.lower().replace(" ", "-"))))
                    max_payout = item.get("max_payout", 0)
                    managed = item.get("managed_by_bugcrowd", False)

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
                        "name": name,
                        "code": code,
                        "description": item.get("description", ""),
                        "platform": "bugcrowd",
                        "scope_url": f"https://bugcrowd.com/{code}" if code else None,
                        "has_rewards": max_payout > 0 or managed,
                        "program_url": item.get("url", f"https://bugcrowd.com/{code}") if code else "",
                        "domains": domains,
                        "wildcards": wildcards,
                        "technologies": item.get("technologies", []),
                        "estimated_payout": float(max_payout) if max_payout else 0.0,
                        "estimated_effort_hours": self._estimate_effort_from_payout(
                            float(max_payout) if max_payout else 0
                        ),
                        "created_at": item.get("created_at", ""),
                    }
                    results.append(prog)

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning("Bugcrowd bounty-targets-data error: %s", e)
            except Exception as e:
                logger.warning("Bugcrowd unexpected error: %s", e)

        logger.info("Bugcrowd bounty-targets-data: %d programs scraped", len(results))
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
