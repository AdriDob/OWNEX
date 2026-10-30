"""Gitcoin Discovery Adapter for Direct Work Engine.

Fetches grants and bounties from Gitcoin and converts them to
DirectWorkEngine Opportunities with web3 barrier assessment.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    EntryMechanism,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.gitcoin")

GITCOIN_API_BASE = "https://grants-api.gitcoin.co"


class GitcoinDweAdapter(BaseDiscoveryAdapter):
    """Discovers Gitcoin grants and bounties via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="gitcoin",
            platform=WorkPlatform.GITCOIN,
            categories=[
                OpportunityCategory.OPEN_SOURCE,
                OpportunityCategory.DEV_BOUNTY,
                OpportunityCategory.OPEN_CALL,
            ],
            tier=1,
            analysis_cadence_hours=24,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch active Gitcoin grants/bounties and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                endpoints = [
                    f"{GITCOIN_API_BASE}/v1/grants",
                    "https://gitcoin.co/api/v1/grants",
                ]

                grants = []
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            grants = data if isinstance(data, list) else data.get("data", data.get("grants", []))
                            if grants:
                                logger.info("Gitcoin: successfully fetched from %s", endpoint)
                                break
                    except Exception as e:
                        logger.debug("Gitcoin endpoint %s failed: %s", endpoint, e)
                        continue

                if not grants:
                    logger.warning("Gitcoin: all endpoints failed")
                    return opportunities

                for grant in grants:
                    opp = self._convert_grant(grant)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching Gitcoin grants: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(f"{GITCOIN_API_BASE}/v1/grants")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_grant(self, grant: dict[str, Any]) -> Opportunity | None:
        """Convert Gitcoin grant to Opportunity with web3 barrier assessment."""
        try:
            grant_id = str(grant.get("id", "") or grant.get("slug", ""))
            name = str(grant.get("title", "") or grant.get("name", ""))
            if not grant_id or not name:
                return None

            max_bounty = float(grant.get("amount", 0) or grant.get("amountUSD", 0) or 0)
            avg_bounty = max_bounty * 0.2  # Grants typically pay full amount

            # Determine difficulty based on grant type
            grant_type = str(grant.get("type", "") or grant.get("category", "")).lower()
            if "technical" in grant_type or "development" in grant_type or "code" in grant_type:
                difficulty = DifficultyLevel.INTERMEDIATE
                effort_hours = 20.0
            else:
                difficulty = DifficultyLevel.BEGINNER
                effort_hours = 10.0

            return self._create_opportunity(
                external_id=grant_id,
                title=f"{name} — Gitcoin Grant",
                category=OpportunityCategory.OPEN_SOURCE,
                url=f"https://gitcoin.co/grants/{grant_id}",
                description=self._build_description(grant),
                company="Gitcoin",
                country="Global",
                payment=avg_bounty or max_bounty * 0.1,
                currency="USD",
                payment_method=PaymentMethod.CRYPTO,
                difficulty=difficulty,
                language_required="english",
                estimated_time_hours=effort_hours,
                experience_required=ExperienceLevel.NONE,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=30.0,
                reputation=0.85,
                risk=0.2,
                payment_proven=True,
                stability=0.8,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(grant),
                employment_type=EmploymentType.OPEN_CALL,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=None,
                time_to_first_work_hours=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.error("Error converting Gitcoin grant %s: %s", grant.get("id"), e)
            return None

    def _build_description(self, grant: dict[str, Any]) -> str:
        parts = []
        if grant.get("description"):
            parts.append(grant["description"][:500])
        if grant.get("category"):
            parts.append(f"Category: {grant['category']}")
        if grant.get("tags"):
            parts.append(f"Tags: {', '.join(grant['tags'][:5])}")
        return " | ".join(parts)

    def _extract_tags(self, grant: dict[str, Any]) -> list[str]:
        tags = ["web3", "grants", "gitcoin", "open_source", "public_goods"]
        if grant.get("category"):
            tags.append(grant["category"].lower())
        if grant.get("tags"):
            tags.extend([t.lower() for t in grant["tags"][:5]])
        return tags


def build_gitcoin_adapter() -> GitcoinDweAdapter:
    """Factory function for building the Gitcoin adapter."""
    return GitcoinDweAdapter()
