"""Hats Finance Discovery Adapter for Direct Work Engine.

Fetches audit competitions from Hats Finance and converts them to
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

logger = logging.getLogger("ownex.api.direct_work.adapters.hatsfinance")

HATS_API_BASE = "https://api.hats.finance"


class HatsFinanceDweAdapter(BaseDiscoveryAdapter):
    """Discovers Hats Finance audit competitions via public API."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="hats_finance",
            platform=WorkPlatform.HATS_FINANCE,
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
        """Fetch active Hats Finance competitions and convert to Opportunities."""
        opportunities: list[Opportunity] = []

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                endpoints = [
                    "https://api.hats.finance/v1/competitions",
                    "https://hats.finance/api/competitions",
                ]

                competitions = []
                for endpoint in endpoints:
                    try:
                        resp = await client.get(endpoint, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            competitions = (
                                data if isinstance(data, list) else data.get("data", data.get("competitions", []))
                            )
                            if competitions:
                                logger.info("Hats Finance: successfully fetched from %s", endpoint)
                                break
                    except Exception as e:
                        logger.debug("Hats Finance endpoint %s failed: %s", endpoint, e)
                        continue

                if not competitions:
                    logger.warning("Hats Finance: all endpoints failed")
                    return opportunities

                for comp in competitions:
                    opp = self._convert_competition(comp)
                    if opp:
                        opportunities.append(opp)

        except Exception as e:
            logger.error("Error fetching Hats Finance competitions: %s", e)

        return opportunities

    async def validate_connection(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get("https://api.hats.finance/v1/competitions")
                return resp.status_code == 200
        except Exception:
            return False

    def _convert_competition(self, comp: dict[str, Any]) -> Opportunity | None:
        """Convert Hats Finance competition to Opportunity with audit-specific barrier assessment."""
        try:
            comp_id = str(comp.get("id", "") or comp.get("slug", ""))
            name = str(comp.get("name", "") or comp.get("title", ""))
            if not comp_id or not name:
                return None

            max_bounty = float(comp.get("maxReward", 0) or 0)
            total_prizes = float(comp.get("totalPrizes", 0) or 0)
            avg_bounty = total_prizes * 0.05 if total_prizes > 0 else max_bounty * 0.1

            effort_hours = 40.0 if max_bounty > 100000 else 25.0

            return self._create_opportunity(
                external_id=comp_id,
                title=f"{name} — Hats Finance Audit",
                category=OpportunityCategory.SECURITY_RESEARCH,
                url=f"https://hats.finance/competitions/{comp_id}",
                description=self._build_description(comp),
                company="Hats Finance",
                country="Global",
                payment=avg_bounty or max_bounty * 0.1,
                currency="USD",
                payment_method=PaymentMethod.CRYPTO,
                difficulty=DifficultyLevel.ADVANCED,
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
                technology_tags=self._extract_tags(comp),
                employment_type=EmploymentType.BOUNTY,
                entry_mechanism=EntryMechanism.ASSESSMENT,
                hourly_rate_usd=None,
                time_to_first_work_hours=None,
                rate_source="platform",
            )
        except Exception as e:
            logger.error("Error converting Hats Finance competition %s: %s", comp.get("id"), e)
            return None

    def _build_description(self, comp: dict[str, Any]) -> str:
        parts = []
        if comp.get("description"):
            parts.append(comp["description"][:500])
        if comp.get("language"):
            parts.append(f"Language: {comp['language']}")
        if comp.get("repo"):
            parts.append(f"Repo: {comp['repo']}")
        if comp.get("scope"):
            parts.append(f"Scope: {comp['scope'][:200]}")
        return " | ".join(parts)

    def _extract_tags(self, comp: dict[str, Any]) -> list[str]:
        tags = ["web3", "smart_contract_audit", "hats_finance", "security_research", "defi"]
        if comp.get("language"):
            tags.append(comp["language"].lower())
        if comp.get("category"):
            tags.append(comp["category"].lower())
        return tags


def build_hatsfinance_adapter() -> HatsFinanceDweAdapter:
    """Factory function for building the Hats Finance adapter."""
    return HatsFinanceDweAdapter()
