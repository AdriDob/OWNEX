"""CodeHawks Discovery Adapter for Direct Work Engine.

Fetches active audit contests from CodeHawks and converts them to
DirectWorkEngine Opportunities with smart contract audit barrier assessment.
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

logger = logging.getLogger("ownex.api.direct_work.adapters.codehawks")

CODEHAWKS_API_BASE = "https://api.codehawks.cyfrin.io"


class CodeHawksDweAdapter(BaseDiscoveryAdapter):
    """Discovers CodeHawks audit contests via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="codehawks",
            platform=WorkPlatform.CODEHAWKS,
            categories=[
                OpportunityCategory.BUG_BOUNTY,
                OpportunityCategory.SMART_CONTRACTS,
                OpportunityCategory.SECURITY_RESEARCH,
            ],
            tier=1,
            analysis_cadence_hours=12,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch active CodeHawks contests and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                endpoints = [
                    "https://api.codehawks.cyfrin.io/v1/contests",
                    "https://codehawks.cyfrin.io/api/contests",
                ]

                contests = []
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            contests = data if isinstance(data, list) else data.get("data", data.get("contests", []))
                            if contests:
                                logger.info("CodeHawks: successfully fetched from %s", endpoint)
                                break
                    except Exception as e:
                        logger.debug("CodeHawks endpoint %s failed: %s", endpoint, e)
                        continue

                if not contests:
                    logger.warning("CodeHawks: all endpoints failed")
                    return opportunities

                for contest in contests:
                    opp = self._convert_contest(contest)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching CodeHawks contests: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get("https://api.codehawks.cyfrin.io/v1/contests")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_contest(self, contest: dict[str, Any]) -> Opportunity | None:
        """Convert CodeHawks contest to Opportunity with audit-specific barrier assessment."""
        try:
            contest_id = str(contest.get("id", "") or contest.get("slug", ""))
            name = str(contest.get("name", "") or contest.get("title", ""))
            if not contest_id or not name:
                return None

            max_bounty = float(contest.get("maxReward", 0) or 0)
            total_prizes = float(contest.get("totalPrizes", 0) or 0)
            avg_bounty = total_prizes * 0.05 if total_prizes > 0 else max_bounty * 0.1

            difficulty = DifficultyLevel.ADVANCED

            effort_hours = 40.0 if max_bounty > 100000 else 25.0

            return self._create_opportunity(
                external_id=contest_id,
                title=f"{name} — CodeHawks Audit",
                category=OpportunityCategory.SECURITY_RESEARCH,
                url=f"https://codehawks.cyfrin.io/contests/{contest_id}",
                description=self._build_description(contest),
                company="CodeHawks",
                country="Global",
                payment=avg_bounty or max_bounty * 0.1,
                currency="USD",
                payment_method=PaymentMethod.CRYPTO,
                difficulty=difficulty,
                language_required="english",
                estimated_time_hours=effort_hours,
                experience_required=ExperienceLevel.MID,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=30.0,
                reputation=0.9,
                risk=0.25,
                payment_proven=True,
                stability=0.85,
                accepts_beginner=False,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(contest),
                employment_type=EmploymentType.BOUNTY,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=None,
                time_to_first_work_hours=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.error("Error converting CodeHawks contest %s: %s", contest.get("id"), e)
            return None

    def _build_description(self, contest: dict[str, Any]) -> str:
        parts = []
        if contest.get("description"):
            parts.append(contest["description"][:500])
        if contest.get("language"):
            parts.append(f"Language: {contest['language']}")
        if contest.get("repo"):
            parts.append(f"Repo: {contest['repo']}")
        if contest.get("scope"):
            parts.append(f"Scope: {contest['scope'][:200]}")
        return " | ".join(parts)

    def _extract_tags(self, contest: dict[str, Any]) -> list[str]:
        tags = ["web3", "smart_contract_audit", "codehawks", "security_research", "defi"]
        if contest.get("language"):
            tags.append(contest["language"].lower())
        if contest.get("category"):
            tags.append(contest["category"].lower())
        return tags


def build_codehawks_adapter() -> CodeHawksDweAdapter:
    """Factory function for building the CodeHawks adapter."""
    return CodeHawksDweAdapter()
