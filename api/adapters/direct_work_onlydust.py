"""OnlyDust Discovery Adapter for Direct Work Engine.

Fetches OSS funding opportunities from OnlyDust and converts them to
DirectWorkEngine Opportunities with open source focus.
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

logger = logging.getLogger("ownex.api.direct_work.adapters.onlydust")

ONLYDUST_API_BASE = "https://api.onlydust.com"


class OnlyDustDweAdapter(BaseDiscoveryAdapter):
    """Discovers OnlyDust OSS funding opportunities via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="onlydust",
            platform=WorkPlatform.ONLY_DUST,
            categories=[
                OpportunityCategory.OPEN_SOURCE,
                OpportunityCategory.OSS_BOUNTIES,
                OpportunityCategory.OPEN_CALL,
            ],
            tier=1,
            analysis_cadence_hours=24,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch active OnlyDust funding opportunities and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                endpoints = [
                    "https://api.onlydust.com/v1/opportunities",
                    "https://onlydust.com/api/opportunities",
                ]

                opportunities_data = []
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            opportunities_data = (
                                data if isinstance(data, list) else data.get("data", data.get("opportunities", []))
                            )
                            if opportunities_data:
                                logger.info("OnlyDust: successfully fetched from %s", endpoint)
                                break
                    except Exception as e:
                        logger.debug("OnlyDust endpoint %s failed: %s", endpoint, e)
                        continue

                if not opportunities_data:
                    logger.warning("OnlyDust: all endpoints failed")
                    return opportunities

                for opp_data in opportunities_data:
                    opp = self._convert_opportunity(opp_data)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching OnlyDust opportunities: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get("https://api.onlydust.com/v1/opportunities")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_opportunity(self, opp_data: dict[str, Any]) -> Opportunity | None:
        """Convert OnlyDust opportunity to Opportunity with OSS barrier assessment."""
        try:
            opp_id = str(opp_data.get("id", "") or opp_data.get("slug", ""))
            name = str(opp_data.get("title", "") or opp_data.get("name", ""))
            if not opp_id or not name:
                return None

            max_bounty = float(
                opp_data.get("reward", 0) or opp_data.get("amount", 0) or opp_data.get("reward_usd", 0) or 0
            )
            avg_bounty = max_bounty * 0.4

            effort_hours = 10.0 if max_bounty > 2000 else 5.0

            return self._create_opportunity(
                external_id=opp_id,
                title=f"{name} — OnlyDust",
                category=OpportunityCategory.OPEN_SOURCE,
                url=f"https://onlydust.com/opportunities/{opp_id}",
                description=self._build_description(opp_data),
                company="OnlyDust",
                country="Global",
                payment=avg_bounty or max_bounty * 0.2,
                currency="USD",
                payment_method=PaymentMethod.CRYPTO,
                difficulty=DifficultyLevel.INTERMEDIATE,
                language_required="english",
                estimated_time_hours=effort_hours,
                experience_required=ExperienceLevel.NONE,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=14.0,
                reputation=0.8,
                risk=0.15,
                payment_proven=True,
                stability=0.75,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(opp_data),
                employment_type=EmploymentType.OPEN_CALL,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=None,
                time_to_first_work_hours=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.error("Error converting OnlyDust opportunity %s: %s", opp_data.get("id"), e)
            return None

    def _build_description(self, opp_data: dict[str, Any]) -> str:
        parts = []
        if opp_data.get("description"):
            parts.append(opp_data["description"][:500])
        if opp_data.get("repository"):
            parts.append(f"Repo: {opp_data['repository']}")
        if opp_data.get("labels"):
            parts.append(f"Labels: {', '.join(opp_data['labels'][:5])}")
        return " | ".join(parts)

    def _extract_tags(self, opp_data: dict[str, Any]) -> list[str]:
        tags = ["web3", "oss", "onlydust", "open_source", "funding"]
        if opp_data.get("labels"):
            tags.extend([l.lower() for l in opp_data["labels"][:5]])
        if opp_data.get("repository"):
            tags.append(opp_data["repository"].split("/")[-1].lower())
        return tags


def build_onlydust_adapter() -> OnlyDustDweAdapter:
    """Factory function for building the OnlyDust adapter."""
    return OnlyDustDweAdapter()
