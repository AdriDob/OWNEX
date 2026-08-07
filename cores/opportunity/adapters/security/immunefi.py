"""Immunefi Adapter — Security Work Cycle.

Web3/crypto bug bounty platform. Scrapes explore page (Next.js __NEXT_DATA__).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.immunefi")

IMMUNEFI_EXPLORE = "https://immunefi.com/explore/"


class ImmunefiAdapter(OpportunityAdapter):
    """Adapter for Immunefi smart contract bounty programs.

    Uses HTML scraping of explore page with Next.js __NEXT_DATA__ extraction.
    """

    platform: str = "immunefi"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        creds = get_platform_credentials("immunefi")
        self._token = creds.get("api_key") or os.environ.get("IMMUNEFI_API_KEY", "")
        self._enabled = bool(self._token)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Immunefi bounty programs."""
        raw_opps: list[RawOpportunity] = []
        programs = await self._fetch_programs()

        for prog in programs:
            if not prog.get("has_rewards"):
                continue

            raw_opps.append(
                RawOpportunity(
                    id=f"immunefi_{prog.get('slug', prog.get('name', ''))}",
                    name=prog.get("name", ""),
                    description=prog.get("description", "") or f"Immunefi bounty: {prog.get('name', '')}",
                    platform="immunefi",
                    url=prog.get("program_url", ""),
                    reward=prog.get("estimated_payout", 0.0),
                    effort_hours=prog.get("estimated_effort_hours", 8.0),
                    tags=prog.get("technologies", ["web3", "smart-contracts", "bug-bounty"]),
                    cycle="security",
                    source_type="platform",
                    source_name="immunefi",
                    metadata={"original": prog, "personal": personal},
                    created_at=prog.get("created_at", ""),
                )
            )

        logger.info("ImmunefiAdapter: fetched %d opportunities", len(raw_opps))
        return raw_opps

    async def _fetch_programs(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(IMMUNEFI_EXPLORE, headers={"Accept": "text/html"}, timeout=20)
                if resp.status_code != 200:
                    logger.warning("Immunefi explore: HTTP %s", resp.status_code)
                    return results

                body = resp.text

                # Try Next.js __NEXT_DATA__ embedded JSON
                match = re.search(
                    r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*type=["\']application/json["\'][^>]*>'
                    r"(.*?)</script>",
                    body,
                    re.DOTALL,
                )
                if match:
                    import json
                    data = json.loads(match.group(1))
                    props = data.get("props", {}).get("pageProps", {})
                    projects = props.get("projects", props.get("bounties", []))

                    for item in projects:
                        name = item.get("name", item.get("project", item.get("title", "")))
                        if not name:
                            continue

                        slug = item.get("slug", item.get("id", name.lower().replace(" ", "-")))
                        payout_raw = item.get("maxPayout", item.get("maximum_payout", item.get("reward", 0)))

                        if isinstance(payout_raw, (int, float)):
                            payout = int(float(payout_raw))
                        else:
                            payout = self._parse_payout(str(payout_raw))

                        techs = item.get("technologies", item.get("techStack", []))
                        if isinstance(techs, str):
                            techs = [t.strip() for t in techs.split(",") if t.strip()]

                        prog = {
                            "name": name,
                            "slug": slug,
                            "description": item.get("description", ""),
                            "platform": "immunefi",
                            "has_rewards": True,
                            "estimated_payout": payout,
                            "raw_payout_range": f"${payout:,}" if payout else "",
                            "technologies": techs if isinstance(techs, list) else [],
                            "program_url": f"https://immunefi.com/bounty/{slug}/",
                            "estimated_effort_hours": self._estimate_effort(payout),
                            "created_at": item.get("createdAt", ""),
                        }
                        results.append(prog)

            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning("Immunefi fetch error: %s", e)
            except Exception as e:
                logger.warning("Immunefi parse error: %s", e)

        # Fallback: regex-based extraction
        if not results:
            await self._fallback_scrape(results)

        logger.info("Immunefi: %d programs scraped", len(results))
        return results

    async def _fallback_scrape(self, results: list[dict[str, Any]]) -> None:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(IMMUNEFI_EXPLORE, timeout=20)
                body = resp.text
                cards = re.findall(
                    r'<a[^>]*href=["\'](/bounty/[^"\'/]+/)["\'][^>]*>(.*?)</a>',
                    body,
                    re.DOTALL,
                )
                for href, title_html in cards:
                    name = re.sub(r"<[^>]+>", "", title_html).strip()
                    if not name:
                        continue
                    results.append({
                        "name": name,
                        "slug": href.strip("/").split("/")[-1],
                        "platform": "immunefi",
                        "has_rewards": True,
                        "program_url": f"https://immunefi.com{href}",
                        "technologies": ["web3", "smart-contracts"],
                        "estimated_payout": 0,
                        "estimated_effort_hours": 8.0,
                    })
            except Exception:
                pass

    def _parse_payout(self, text: str) -> int:
        if not text:
            return 0
        amounts = re.findall(r"[\d,]+(?:\.\d+)?", str(text).replace(",", ""))
        parsed = [float(a) for a in amounts if a.replace(".", "").isdigit()]
        return int(max(parsed)) if parsed else 0

    def _estimate_effort(self, payout: float) -> float:
        # Immunefi bounties tend to be higher effort (smart contract auditing)
        if payout >= 50000:
            return 40.0
        elif payout >= 10000:
            return 20.0
        elif payout >= 5000:
            return 15.0
        elif payout >= 1000:
            return 10.0
        return 8.0
