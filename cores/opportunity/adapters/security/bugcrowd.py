"""Bugcrowd Adapter — Security Work Cycle.

Second largest bug bounty platform. Uses public programs.json API + optional authenticated API.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.bugcrowd")

BUGCROWD_PUBLIC_API = "https://bugcrowd.com/programs.json"
BUGCROWD_AUTH_API = "https://api.bugcrowd.com"


class BugcrowdAdapter(OpportunityAdapter):
    """Adapter for Bugcrowd bug bounty programs.

    Uses public directory API for program discovery (no auth required).
    Optionally uses authenticated API for submissions and payout data if credentials available.
    """

    platform: str = "bugcrowd"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("bugcrowd")
        self._token = creds.get("api_token") or os.environ.get("BUGCROWD_API_TOKEN", "")
        self._enabled = bool(self._token)

    def _auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Token {self._token}"} if self._token else {}

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Bugcrowd programs with active bounties."""
        raw_opps: list[RawOpportunity] = []

        programs = await self._fetch_public_programs(max_pages=3)

        if self._enabled:
            await self._enrich_with_authenticated_data(programs)

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

    async def _fetch_public_programs(self, max_pages: int = 3) -> list[dict[str, Any]]:
        """Fetch public programs from Bugcrowd directory."""
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            for page in range(max_pages):
                try:
                    url = f"{BUGCROWD_PUBLIC_API}?page={page + 1}&sort=promoted&order=desc"
                    resp = await client.get(url, headers={"Accept": "application/json"}, timeout=15)
                    if resp.status_code != 200:
                        logger.warning("Bugcrowd public page %d: HTTP %s", page + 1, resp.status_code)
                        continue

                    data = resp.json()
                    programs = data if isinstance(data, list) else data.get("programs", [])

                    for item in programs:
                        name = item.get("name", item.get("handle", ""))
                        if not name:
                            continue

                        code = item.get("code", item.get("slug", ""))
                        payout_range = item.get("reward_range", "")
                        estimated_payout = self._parse_payout_range(payout_range)

                        prog = {
                            "name": name,
                            "code": code,
                            "description": item.get("description", ""),
                            "platform": "bugcrowd",
                            "scope_url": f"https://bugcrowd.com/{code}" if code else None,
                            "has_rewards": bool(item.get("payout", False)),
                            "program_url": f"https://bugcrowd.com/{code}" if code else "",
                            "technologies": item.get("target_groups", []),
                            "raw_payout_range": payout_range,
                            "estimated_payout": estimated_payout,
                            "estimated_effort_hours": self._estimate_effort_from_payout(estimated_payout),
                            "created_at": item.get("created_at", item.get("published_at", "")),
                        }
                        results.append(prog)

                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    logger.warning("Bugcrowd page %d error: %s", page + 1, e)
                    continue
                except Exception as e:
                    logger.warning("Bugcrowd unexpected error on page %d: %s", page + 1, e)
                    continue

        logger.info("Bugcrowd public: %d programs scraped", len(results))
        return results

    def _parse_payout_range(self, payout_text: str) -> float:
        """Extract max payout from reward range like '$500 - $10,000'."""
        import re

        if not payout_text:
            return 0.0
        amounts = re.findall(r"\$?([\d,]+(?:\.\d+)?)", str(payout_text).replace(",", ""))
        parsed = []
        for a in amounts:
            try:
                parsed.append(float(a.replace(",", "")))
            except ValueError:
                continue
        return max(parsed) if parsed else 0.0

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

    async def _enrich_with_authenticated_data(self, programs: list[dict[str, Any]]) -> None:
        """Enrich with authenticated API data if available."""
        if not self._enabled:
            return

        async with httpx.AsyncClient() as client:
            # Could fetch submission data, payouts, etc. from authenticated endpoints
            # For now, we rely on public data
            pass