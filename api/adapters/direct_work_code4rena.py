"""Code4rena Discovery Adapter for Direct Work Engine.

Fetches active audit contests from Code4rena and converts them to
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

logger = logging.getLogger("ownex.api.direct_work.adapters.code4rena")

CODE4RENA_API_BASE = "https://api.code4rena.com/api"


class Code4renaDweAdapter(BaseDiscoveryAdapter):
    """Discovers Code4rena audit contests via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="code4rena",
            platform=WorkPlatform.CODE4RENA,
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
        """Fetch active Code4rena contests and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Fetch active contests
                resp = await client.get(f"{CODE4RENA_API_BASE}/contests/active")
                if resp.status_code != 200:
                    logger.warning("Code4rena API returned %s", resp.status_code)
                    return opportunities

                data = resp.json()
                contests = data if isinstance(data, list) else data.get("data", [])

                for contest in contests:
                    opp = self._convert_contest(contest)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching Code4rena contests: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{CODE4RENA_API_BASE}/health")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_contest(self, contest: dict[str, Any]) -> Opportunity | None:
        """Convert Code4rena contest to Opportunity with audit-specific barrier assessment."""
        try:
            contest_id = str(contest.get("id", "") or contest.get("slug", ""))
            name = str(contest.get("name", "") or contest.get("title", ""))
            if not contest_id or not name:
                return None

            # Extract reward info
            max_bounty = float(contest.get("maxReward", 0) or 0)
            min_bounty = float(contest.get("minReward", 0) or 0)
            total_prizes = float(contest.get("totalPrizes", 0) or 0)
            avg_bounty = total_prizes * 0.05 if total_prizes > 0 else max_bounty * 0.1  # Conservative

            # Difficulty based on scope complexity
            difficulty = DifficultyLevel.ADVANCED  # Smart contract audits are advanced

            # Estimate effort - audits are time-intensive
            effort_hours = 40.0 if max_bounty > 100000 else 25.0

            # Code4rena: outcome-based (submit findings via GitHub), no interview
            # but requires proven audit skill (assessment-based)
            entry = self._get_entry_model()

            return self._create_opportunity(
                external_id=contest_id,
                title=f"{name} — Code4rena Audit",
                category=OpportunityCategory.SECURITY_RESEARCH,
                url=f"https://code4rena.com/contests/{contest_id}",
                description=self._build_description(contest),
                company="Code4rena",
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
                technical_test_required=False,  # Audit skill is the "test"
                registration_required=True,
                time_to_payout_days=30.0,
                reputation=0.9,
                risk=0.25,
                payment_proven=True,
                stability=0.85,
                accepts_beginner=False,  # Audits require skill
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(contest),
                employment_type=EmploymentType.BOUNTY,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=entry.get("hourly_rate_usd") if entry else None,
                time_to_first_work_hours=entry.get("time_to_first_work_hours") if entry else None,
                rate_source="platform" if entry else "unknown",
            )
        except Exception as e:
            logger.error("Error converting Code4rena contest %s: %s", contest.get("id"), e)
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
        tags = ["web3", "smart_contract_audit", "code4rena", "security_research", "defi"]
        if contest.get("language"):
            tags.append(contest["language"].lower())
        if contest.get("category"):
            tags.append(contest["category"].lower())
        return tags

    def _get_entry_model(self) -> dict[str, Any] | None:
        """Get curated entry model for Code4rena from global sources."""
        try:
            from cores.opportunity.global_sources import find_curated_entry_model

            return find_curated_entry_model("code4rena")
        except Exception:
            return None


def build_code4rena_adapter() -> Code4renaDweAdapter:
    """Factory function for building the Code4rena adapter."""
    return Code4renaDweAdapter()
