"""Fiverr — real discovery adapter for the Direct Work Engine.

Converts the FiverrEngine gig catalog into DWE Opportunities.
"""

from __future__ import annotations

import logging
from typing import Any

from api.adapters.legacy import LegacyOpportunityDweAdapter
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.fiverr")


class FiverrDweAdapter(LegacyOpportunityDweAdapter):
    """Bridges the FiverrEngine gig catalog into DWE discovery."""

    def __init__(self, config: dict[str, Any] | None = None):
        from cores.fiverr.engine import get_fiverr_engine

        super().__init__(
            get_fiverr_engine(),
            name="fiverr",
            platform=WorkPlatform.FIVERR,
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.CONTRACT,
            payment_method=PaymentMethod.PLATFORM_CREDIT,
            registration_required=True,
            tier=1,
            analysis_cadence_hours=24,
        )

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Convert Fiverr gig catalog to DWE Opportunities."""
        gigs = self._legacy.catalog()
        out: list[Opportunity] = []

        for gig in gigs:
            # Map Fiverr gig to DWE Opportunity
            difficulty_map = {
                "low": "BEGINNER",
                "mid": "INTERMEDIATE",
                "high": "ADVANCED",
                "expert": "ADVANCED",
            }

            # Use gig pricing as estimated reward
            reward = gig.pricing.standard if gig.pricing.standard > 0 else gig.pricing.starter

            op = Opportunity(
                id=f"fiverr_{gig.key}",
                title=gig.title,
                platform=WorkPlatform.FIVERR,
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                url=f"https://www.fiverr.com/gigs/{gig.key}",
                description=gig.problem,
                remote=True,
                payment=float(reward),
                currency="USD",
                payment_method=PaymentMethod.PLATFORM_CREDIT,
                international_payment=True,
                difficulty=DifficultyLevel[difficulty_map.get(gig.difficulty, "INTERMEDIATE")],
                language_required="english",
                estimated_time_hours=gig.estimated_hours,
                experience_required=ExperienceLevel.NONE,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=14.0,  # Fiverr standard payout
                reputation=0.8,
                risk=0.2,
                payment_proven=True,
                stability=0.7,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=gig.tech_skills,
                employment_type=EmploymentType.CONTRACT,
                hourly_rate_usd=gig.pricing.standard / max(gig.estimated_hours, 1),
                time_to_first_work_hours=24.0,  # Can start next day
                rate_source="platform",
            )
            out.append(op)

        return out
