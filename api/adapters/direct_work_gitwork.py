"""GitWork Discovery Adapter for Direct Work Engine.

Fetches GitHub issue bounties from GitWork and converts them to
DirectWorkEngine Opportunities with web3/dev focus.
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

logger = logging.getLogger("ownex.api.direct_work.adapters.gitwork")

GITWORK_API_BASE = "https://api.gitwork.io"


class GitWorkDweAdapter(BaseDiscoveryAdapter):
    """Discovers GitWork issue bounties via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="gitwork",
            platform=WorkPlatform.GITWORK,
            categories=[
                OpportunityCategory.DEV_BOUNTY,
                OpportunityCategory.OPEN_SOURCE,
                OpportunityCategory.OPEN_CALL,
            ],
            tier=1,
            analysis_cadence_hours=12,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch active GitWork issue bounties and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                endpoints = [
                    "https://api.gitwork.io/v1/bounties",
                    "https://gitwork.io/api/bounties",
                ]

                bounties = []
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            bounties = data if isinstance(data, list) else data.get("data", data.get("bounties", []))
                            if bounties:
                                logger.info("GitWork: successfully fetched from %s", endpoint)
                                break
                    except Exception as e:
                        logger.debug("GitWork endpoint %s failed: %s", endpoint, e)
                        continue

                if not bounties:
                    logger.warning("GitWork: all endpoints failed")
                    return opportunities

                for bounty in bounties:
                    opp = self._convert_bounty(bounty)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching GitWork bounties: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get("https://api.gitwork.io/v1/bounties")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_bounty(self, bounty: dict[str, Any]) -> Opportunity | None:
        """Convert GitWork bounty to Opportunity with web3/dev barrier assessment."""
        try:
            bounty_id = str(bounty.get("id", "") or bounty.get("slug", ""))
            name = str(bounty.get("title", "") or bounty.get("name", ""))
            if not bounty_id or not name:
                return None

            max_bounty = float(bounty.get("reward", 0) or bounty.get("amount", 0) or bounty.get("reward_usd", 0) or 0)
            avg_bounty = max_bounty * 0.35

            effort_hours = 12.0 if max_bounty > 3000 else 6.0

            return self._create_opportunity(
                external_id=bounty_id,
                title=f"{name} — GitWork",
                category=OpportunityCategory.DEV_BOUNTY,
                url=f"https://gitwork.io/bounties/{bounty_id}",
                description=self._build_description(bounty),
                company="GitWork",
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
                time_to_payout_days=7.0,
                reputation=0.8,
                risk=0.15,
                payment_proven=True,
                stability=0.8,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(bounty),
                employment_type=EmploymentType.BOUNTY,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=None,
                time_to_first_work_hours=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.error("Error converting GitWork bounty %s: %s", bounty.get("id"), e)
            return None

    def _build_description(self, bounty: dict[str, Any]) -> str:
        parts = []
        if bounty.get("description"):
            parts.append(bounty["description"][:500])
        if bounty.get("repository"):
            parts.append(f"Repo: {bounty['repository']}")
        if bounty.get("labels"):
            parts.append(f"Labels: {', '.join(bounty['labels'][:5])}")
        return " | ".join(parts)

    def _extract_tags(self, bounty: dict[str, Any]) -> list[str]:
        tags = ["web3", "github", "gitwork", "dev_bounty", "bounty", "open_source"]
        if bounty.get("labels"):
            tags.extend([l.lower() for l in bounty["labels"][:5]])
        if bounty.get("repository"):
            tags.append(bounty["repository"].split("/")[-1].lower())
        return tags


def build_gitwork_adapter() -> GitWorkDweAdapter:
    """Factory function for building the GitWork adapter."""
    return GitWorkDweAdapter()
