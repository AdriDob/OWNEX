"""HackenProof Discovery Adapter for Direct Work Engine.

Fetches public bug bounty programs from HackenProof and converts them to
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

logger = logging.getLogger("ownex.api.direct_work.adapters.hackenproof")

HACKENPROOF_API_BASE = "https://api.hackenproof.com/v1"


class HackenProofDweAdapter(BaseDiscoveryAdapter):
    """Discovers HackenProof bug bounty programs via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="hackenproof",
            platform=WorkPlatform.HACKENPROOF,
            categories=[OpportunityCategory.BUG_BOUNTY, OpportunityCategory.SMART_CONTRACTS],
            tier=1,
            analysis_cadence_hours=6,
            requires_auth=False,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch public HackenProof programs and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                endpoints = [
                    f"{HACKENPROOF_API_BASE}/programs",
                    "https://hackenproof.com/api/v1/programs",
                ]

                programs = []
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, timeout=15)
                        if resp.status_code == 200:
                            programs = resp.json()
                            if isinstance(programs, list) and programs:
                                logger.info("HackenProof: successfully fetched from %s", endpoint)
                                break
                    except Exception as e:
                        logger.debug("HackenProof endpoint %s failed: %s", endpoint, e)
                        continue

                if not programs:
                    logger.warning("HackenProof: all endpoints failed")
                    return opportunities

                if not isinstance(programs, list):
                    return opportunities

                for program in programs:
                    opp = self._convert_program(program)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching HackenProof programs: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(f"{HACKENPROOF_API_BASE}/programs")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_program(self, program: dict[str, Any]) -> Opportunity | None:
        """Convert HackenProof program to Opportunity with web3 barrier assessment."""
        try:
            program_id = str(program.get("id", ""))
            name = str(program.get("name", ""))
            if not program_id or not name:
                return None

            max_bounty = 0.0
            for reward in program.get("rewards", []):
                asset = reward.get("asset", "").lower()
                if asset in ("usd", "usdc", "dai", "busd"):
                    amount = float(reward.get("max", 0) or 0)
                    if amount > max_bounty:
                        max_bounty = amount

            avg_bounty = max_bounty * 0.15  # Conservative estimate for web3

            scope = program.get("scope", [])
            in_scope = [s for s in scope if s.get("type") in ("smart_contract", "web3", "blockchain")]
            difficulty = DifficultyLevel.ADVANCED if in_scope else DifficultyLevel.INTERMEDIATE

            effort_hours = 20.0 if max_bounty > 100000 else 12.0

            return self._create_opportunity(
                external_id=program_id,
                title=f"{name} — HackenProof",
                category=OpportunityCategory.BUG_BOUNTY,
                url=f"https://hackenproof.com/bug-bounty/{program_id}/",
                description=self._build_description(program),
                company="HackenProof",
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
                hourly_rate_usd=None,
                time_to_first_work_hours=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.error("Error converting HackenProof program %s: %s", program.get("id"), e)
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
        tags = ["web3", "bug_bounty", "smart_contracts", "defi", "hackenproof"]
        for reward in program.get("rewards", []):
            asset = reward.get("asset", "").upper()
            if asset and asset not in tags:
                tags.append(asset)
        return tags


def build_hackenproof_adapter() -> HackenProofDweAdapter:
    """Factory function for building the HackenProof adapter."""
    return HackenProofDweAdapter()
