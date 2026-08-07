"""HackerOne Adapter — Security Work Cycle.

Largest bug bounty platform. Uses public directory API + optional authenticated API.
Fetches programs with bounties, structured scopes, and hacktivity for reward intelligence.
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

HACKERONE_PUBLIC_API = "https://hackerone.com/programs/search"
HACKERONE_AUTH_API = "https://api.hackerone.com/v1"


class HackerOneAdapter(OpportunityAdapter):
    """Adapter for HackerOne bug bounty programs.

    Uses public directory API for program discovery (no auth required).
    Optionally uses authenticated API for hacktivity and structured scopes if credentials available.
    """

    platform: str = "hackerone"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        # Try to get credentials from vault
        creds = get_platform_credentials("hackerone")
        self._username = creds.get("api_username") or os.environ.get("HACKERONE_API_USERNAME", "")
        self._token = creds.get("api_token") or os.environ.get("HACKERONE_API_TOKEN", "")
        self._enabled = bool(self._username and self._token)

    def _auth_header(self) -> dict[str, str]:
        raw = f"{self._username}:{self._token}"
        encoded = base64.b64encode(raw.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch HackerOne programs with active bounties."""
        raw_opps: list[RawOpportunity] = []

        # 1. Fetch public programs (no auth needed)
        public_programs = await self._fetch_public_programs(max_pages=3)

        # 2. If authenticated, enrich with hacktivity and scopes
        if self._enabled:
            await self._enrich_with_authenticated_data(public_programs)

        for prog in public_programs:
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

    async def _fetch_public_programs(self, max_pages: int = 3) -> list[dict[str, Any]]:
        """Fetch public programs from HackerOne directory API."""
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            for page in range(max_pages):
                try:
                    url = (
                        f"{HACKERONE_PUBLIC_API}?"
                        f"query=sort%3Apublished_at&page%5Bnumber%5D={page + 1}"
                        f"&page%5Bsize%5D=50"
                    )
                    resp = await client.get(url, headers={"Accept": "application/json"}, timeout=15)
                    if resp.status_code != 200:
                        logger.warning("HackerOne public page %d: HTTP %s", page + 1, resp.status_code)
                        continue

                    data = resp.json()
                    items = data if isinstance(data, list) else data.get("data", [])

                    for item in items:
                        attrs = item.get("attributes", {})
                        name = attrs.get("name", attrs.get("handle", ""))
                        if not name:
                            continue

                        # Extract structured scope for domains
                        domains: list[str] = []
                        wildcards: list[str] = []
                        structured_scope = attrs.get("structured_scope", {})
                        if structured_scope:
                            for asset in structured_scope.get("assets", []):
                                asset_id = asset.get("asset_identifier", "")
                                if asset_id:
                                    if asset_id.startswith("*."):
                                        wildcards.append(asset_id[2:])
                                    else:
                                        domains.append(asset_id)

                        prog = {
                            "name": name,
                            "handle": attrs.get("handle", name),
                            "description": attrs.get("description", ""),
                            "platform": "hackerone",
                            "scope_url": f"https://hackerone.com{attrs.get('url', '')}" if attrs.get("url") else None,
                            "has_rewards": bool(attrs.get("offers_bounties", False)),
                            "program_url": f"https://hackerone.com/{attrs.get('handle', name)}",
                            "domains": domains,
                            "wildcards": wildcards,
                            "technologies": attrs.get("technologies", []),
                            "estimated_payout": 0.0,  # Will be enriched if auth available
                            "estimated_effort_hours": 4.0,
                            "created_at": attrs.get("published_at", ""),
                        }
                        results.append(prog)

                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    logger.warning("HackerOne page %d error: %s", page + 1, e)
                    continue
                except Exception as e:
                    logger.warning("HackerOne unexpected error on page %d: %s", page + 1, e)
                    continue

        logger.info("HackerOne public: %d programs scraped", len(results))
        return results

    async def _enrich_with_authenticated_data(self, programs: list[dict[str, Any]]) -> None:
        """Enrich programs with hacktivity data and structured scopes using authenticated API."""
        if not self._enabled:
            return

        async with httpx.AsyncClient() as client:
            # Fetch recent hacktivity for reward intelligence
            try:
                resp = await client.get(
                    f"{HACKERONE_AUTH_API}/hackers/hacktivity",
                    headers=self._auth_header(),
                    params={"page[number]": 1, "page[size]": 50, "sort": "-disclosed_at"},
                    timeout=15,
                )
                if resp.status_code == 200:
                    hacktivity = resp.json().get("data", [])
                    # Build reward map by program
                    reward_map: dict[str, float] = {}
                    for item in hacktivity:
                        attrs = item.get("attributes", {})
                        program_handle = attrs.get("program", {}).get("handle", "")
                        bounty_amount = attrs.get("bounty_amount", 0)
                        if program_handle and bounty_amount:
                            reward_map[program_handle] = max(reward_map.get(program_handle, 0), float(bounty_amount))

                    # Enrich programs
                    for prog in programs:
                        handle = prog.get("handle", "")
                        if handle in reward_map:
                            prog["estimated_payout"] = reward_map[handle]
                            prog["estimated_effort_hours"] = self._estimate_effort_from_payout(reward_map[handle])

            except Exception as e:
                logger.warning("HackerOne hacktivity enrichment failed: %s", e)

            # Fetch structured scopes for each program (sample)
            for prog in programs[:10]:  # Limit to avoid rate limits
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
                    pass  # Silent - not critical

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
