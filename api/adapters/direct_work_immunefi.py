"""Immunefi Discovery Adapter for Direct Work Engine.

Fetches public bug bounty programs from Immunefi and converts them to
DirectWorkEngine Opportunities with web3-specific barrier assessment.
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

logger = logging.getLogger("ownex.api.direct_work.adapters.immunefi")

IMMUNEFI_API_BASE = "https://api.immunefi.com/v1"


class ImmunefiDweAdapter(BaseDiscoveryAdapter):
    """Discovers Immunefi bug bounty programs via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="immunefi",
            platform=WorkPlatform.IMMUNEFI,
            categories=[OpportunityCategory.BUG_BOUNTY, OpportunityCategory.SMART_CONTRACTS],
            tier=1,
            analysis_cadence_hours=6,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch public Immunefi programs and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Fetch all programs
                resp = await client.get(f"{IMMUNEFI_API_BASE}/programs")
                if resp.status_code != 200:
                    logger.warning("Immunefi API returned %s", resp.status_code)
                    return opportunities

                programs = resp.json()
                if not isinstance(programs, list):
                    return opportunities

                for program in programs:
                    opp = self._convert_program(program)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching Immunefi programs: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{IMMUNEFI_API_BASE}/health")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_program(self, program: dict[str, Any]) -> Opportunity | None:
        """Convert Immunefi program to Opportunity with web3 barrier assessment."""
        try:
            program_id = str(program.get("id", ""))
            name = str(program.get("name", ""))
            if not program_id or not name:
                return None

            # Extract reward info
            max_bounty = 0.0
            min_bounty = 0.0
            avg_bounty = 0.0

            for reward in program.get("rewards", []):
                asset = reward.get("asset", "").lower()
                if asset in ("usd", "usdc", "dai", "busd"):
                    amount = float(reward.get("max", 0) or 0)
                    if amount > max_bounty:
                        max_bounty = amount
                    if min_bounty == 0 or amount < min_bounty:
                        min_bounty = amount

            avg_bounty = max_bounty * 0.15  # Conservative estimate for web3

            # Scope & difficulty
            scope = program.get("scope", [])
            in_scope = [s for s in scope if s.get("type") in ("smart_contract", "web3", "blockchain")]
            difficulty = DifficultyLevel.ADVANCED if in_scope else DifficultyLevel.INTERMEDIATE

            # Estimate effort based on complexity
            effort_hours = 20.0 if max_bounty > 100000 else 12.0

            # Web3-specific: assessment-based entry (not traditional funnel)
            # Immunefi: public programs, submit report via API, no interview/portfolio
            entry = self._get_entry_model()

            return self._create_opportunity(
                external_id=program_id,
                title=f"{name} — Immunefi",
                category=OpportunityCategory.BUG_BOUNTY,
                url=f"https://immunefi.com/bug-bounty/{program_id}/",
                description=self._build_description(program),
                company="Immunefi",
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
                time_to_payout_days=21.0,
                reputation=0.9,
                risk=0.3,
                payment_proven=True,
                stability=0.85,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=self._extract_tags(program),
                employment_type=EmploymentType.BOUNTY,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=entry.get("hourly_rate_usd") if entry else None,
                time_to_first_work_hours=entry.get("time_to_first_work_hours") if entry else None,
                rate_source="platform" if entry else "unknown",
            )
        except Exception as e:
            logger.error("Error converting Immunefi program %s: %s", program.get("id"), e)
            return None

    def _build_description(self, program: dict[str, Any]) -> str:
        parts = []
        if program.get("description"):
            parts.append(program["description"][:500])
        if program.get("assets"):
            assets = [a.get("name", "") for a in program["assets"] if a.get("name")]
            parts.append(f"Assets: {', '.join(assets[:5])}")
        if program.get("networks"):
            parts.append(f"Networks: {', '.join(program['networks'][:5])}")
        return " | ".join(parts)

    def _extract_tags(self, program: dict[str, Any]) -> list[str]:
        tags = ["web3", "bug_bounty", "smart_contracts", "defi", "immunefi"]
        for reward in program.get("rewards", []):
            asset = reward.get("asset", "").upper()
            if asset and asset not in tags:
                tags.append(asset)
        return tags

    def _get_entry_model(self) -> dict[str, Any] | None:
        """Get curated entry model for Immunefi from global sources."""
        try:
            from cores.opportunity.global_sources import find_curated_entry_model

            return find_curated_entry_model("immunefi")
        except Exception:
            return None


def build_immunefi_adapter() -> ImmunefiDweAdapter:
    """Factory function for building the Immunefi adapter."""
    return ImmunefiDweAdapter()
