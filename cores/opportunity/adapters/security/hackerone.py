"""HackerOne Adapter — Security Work Cycle.

Uses GitHub bounty-targets-data (arkadiyt) as primary source with real payout data.
Optionally enriches with authenticated HackerOne API for hacktivity and scopes.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.hackerone")

HACKERONE_AUTH_API = "https://api.hackerone.com/v1"
BOUNTY_TARGETS_URL = "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json"


class HackerOneAdapter(OpportunityAdapter):
    """Adapter for HackerOne bug bounty programs.

    Uses curated bounty-targets-data from GitHub for program discovery with real payout data.
    Optionally uses authenticated HackerOne API for hacktivity and structured scopes if credentials available.
    """

    platform: str = "hackerone"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("hackerone")
        self._username = creds.get("api_username") or os.environ.get("HACKERONE_API_USERNAME", "")
        self._token = creds.get("api_token") or os.environ.get("HACKERONE_API_TOKEN", "")
        self._enabled = bool(self._username and self._token)

    def _auth_header(self) -> dict[str, str]:
        raw = f"{self._username}:{self._token}"
        encoded = base64.b64encode(raw.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch HackerOne programs with active bounties and real payout data."""
        raw_opps: list[RawOpportunity] = []

        programs = await self._fetch_from_bounty_targets()

        if self._enabled:
            await self._enrich_with_authenticated_data(programs)

        for prog in programs:
            if not prog.get("has_rewards"):
                continue

            raw_opps.append(
                RawOpportunity(
                    id=f"hackerone_{prog.get('handle', prog.get('name', ''))}",
                    name=prog.get("name", ""),
                    description=prog.get("description", "") or f"HackerOne program: {prog.get('name', '')}",
                    platform="hackerone",
                    url=prog.get("program_url", ""),
                    reward=prog.get("estimated_payout", 0.0),
                    effort_hours=prog.get("estimated_effort_hours", 4.0),
                    tags=prog.get("technologies", ["bug-bounty"]),
                    cycle="security",
                    source_type="platform",
                    source_name="hackerone",
                    metadata={"original": prog, "personal": personal},
                    created_at=prog.get("created_at", ""),
                )
            )

        logger.info("HackerOneAdapter: fetched %d opportunities", len(raw_opps))
        return raw_opps

    async def _fetch_from_bounty_targets(self) -> list[dict[str, Any]]:
        """Fetch curated HackerOne programs from GitHub bounty-targets-data."""
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(BOUNTY_TARGETS_URL, headers={"Accept": "application/json"}, timeout=20)
                if resp.status_code != 200:
                    logger.warning("HackerOne bounty-targets-data: HTTP %s", resp.status_code)
                    return results

                items = resp.json() if isinstance(resp.json(), list) else []

                for item in items:
                    name = item.get("name", item.get("handle", ""))
                    if not name:
                        continue

                    handle = item.get("handle", name.lower().replace(" ", "-"))
                    offers_bounties = item.get("offers_bounties", False)
                    max_payout = self._extract_max_payout(item)

                    # Extract domains from targets.in_scope where eligible_for_bounty is True
                    domains: list[str] = []
                    wildcards: list[str] = []
                    targets = item.get("targets", {})
                    for asset in targets.get("in_scope", []):
                        if not asset.get("eligible_for_bounty", False):
                            continue
                        asset_id = asset.get("asset_identifier", "")
                        if asset_id:
                            if asset_id.startswith("*."):
                                wildcards.append(asset_id[2:])
                            else:
                                domains.append(asset_id)

                    prog = {
                        "name": name,
                        "handle": handle,
                        "description": item.get("description", "") or item.get("summary", ""),
                        "platform": "hackerone",
                        "scope_url": item.get("url", f"https://hackerone.com/{handle}"),
                        "has_rewards": bool(offers_bounties) and max_payout > 0,
                        "program_url": f"https://hackerone.com/{handle}",
                        "domains": domains,
                        "wildcards": wildcards,
                        "technologies": item.get("technologies", []),
                        "estimated_payout": float(max_payout) if max_payout else 0.0,
                        "estimated_effort_hours": self._estimate_effort_from_payout(float(max_payout) if max_payout else 0),
                        "created_at": item.get("published_at", item.get("created_at", "")),
                    }
                    results.append(prog)

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning("HackerOne bounty-targets-data error: %s", e)
            except Exception as e:
                logger.warning("HackerOne unexpected error: %s", e)

        logger.info("HackerOne bounty-targets-data: %d programs scraped", len(results))
        return results

    def _extract_max_payout(self, item: dict[str, Any]) -> float:
        """Extract maximum payout from HackerOne item using targets.in_scope."""
        targets = item.get("targets", {})
        max_payout = 0.0

        # Try to get max severity and calculate from that
        for asset in targets.get("in_scope", []):
            if not asset.get("eligible_for_bounty", False):
                continue
            max_severity = asset.get("max_severity", "").lower()
            # Estimate payout based on max severity
            severity_payout = {
                "critical": 10000,
                "high": 5000,
                "medium": 1000,
                "low": 200,
                "none": 0,
            }
            payout = severity_payout.get(max_severity, 0)
            if payout > max_payout:
                max_payout = payout

        return max_payout

    async def _enrich_with_authenticated_data(self, programs: list[dict[str, Any]]) -> None:
        """Enrich programs with hacktivity data and structured scopes using authenticated API."""
        if not self._enabled:
            return

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{HACKERONE_AUTH_API}/hackers/hacktivity",
                    headers=self._auth_header(),
                    params={"page[number]": 1, "page[size]": 50, "sort": "-disclosed_at"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    hacktivity = resp.json().get("data", [])
                    reward_map: dict[str, float] = {}
                    for item in hacktivity:
                        attrs = item.get("attributes", {})
                        program_handle = attrs.get("program", {}).get("handle", "")
                        bounty_amount = attrs.get("bounty_amount", 0)
                        if program_handle and bounty_amount:
                            reward_map[program_handle] = max(reward_map.get(program_handle, 0), float(bounty_amount))

                    for prog in programs:
                        handle = prog.get("handle", "")
                        if handle in reward_map and reward_map[handle] > prog.get("estimated_payout", 0):
                            prog["estimated_payout"] = reward_map[handle]
                            prog["estimated_effort_hours"] = self._estimate_effort_from_payout(reward_map[handle])

            except Exception as e:
                logger.warning("HackerOne hacktivity enrichment failed: %s", e)

            for prog in programs[:10]:
                handle = prog.get("handle", "")
                if not handle:
                    continue
                try:
                    resp = await client.get(
                        f"{HACKERONE_AUTH_API}/hackers/programs/{handle}/structured_scopes",
                        headers=self._auth_header(),
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        scopes = resp.json().get("data", [])
                        domains = []
                        wildcards = []
                        for scope in scopes:
                            attrs = scope.get("attributes", {})
                            asset_id = attrs.get("asset_identifier", "")
                            if asset_id:
                                if asset_id.startswith("*."):
                                    wildcards.append(asset_id[2:])
                                else:
                                    domains.append(asset_id)
                        prog["domains"] = domains
                        prog["wildcards"] = wildcards
                except Exception:
                    pass

    def _estimate_effort_from_payout(self, payout: float) -> float:
        """Estimate effort hours based on bounty amount."""
        if payout >= 10000:
            return 20.0
        elif payout >= 5000:
            return 12.0
        elif payout >= 1000:
            return 8.0
        elif payout >= 500:
            return 5.0
        return 3.0
