"""BountyBoard.dev Adapter — GitHub bounties across many projects.

Zero-barrier: GitHub login → browse bounties → claim → submit PR → get paid.
No interview, no portfolio required.
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

logger = logging.getLogger("ownex.adapters.bountyboard")


class BountyBoardAdapter(LegacyOpportunityDweAdapter):
    """BountyBoard.dev — GitHub bounties aggregator.

    Real implementation requires:
    - GitHub OAuth token
    - BountyBoard API access
    - For now: curated deep-links to representative bounties.
    """

    # Curated seeds vaciados 2026-09-16 (verificado: bountyboard.dev caído
    # entero). Sin URL 200 verificada por probe no hay seed.
    CURATED_BOUNTIES: list[dict] = []

    def __init__(self, config: dict[str, Any] | None = None):
        # BountyBoard doesn't have a legacy engine, so we pass None
        super().__init__(
            None,
            name="bountyboard",
            platform=WorkPlatform.BOUNTYBOARD,
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.CONTRACT,
            payment_method=PaymentMethod.PLATFORM_CREDIT,
            registration_required=True,
            tier=1,
            analysis_cadence_hours=24,
        )

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch BountyBoard bounties (curated deep-links for now)."""
        out: list[Opportunity] = []

        for bounty in self.CURATED_BOUNTIES:
            difficulty_map = {
                "easy": "BEGINNER",
                "medium": "INTERMEDIATE",
                "hard": "ADVANCED",
            }

            op = Opportunity(
                id=bounty["id"],
                title=bounty["name"],
                platform=WorkPlatform.OPEN_SOURCE,
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                url=bounty["url"],
                description=bounty["description"],
                remote=True,
                payment=float(bounty["reward"]),
                currency="USD",
                payment_method=PaymentMethod.PLATFORM_CREDIT,
                international_payment=True,
                difficulty=DifficultyLevel[difficulty_map.get(bounty["difficulty"], "INTERMEDIATE")],
                language_required="english",
                estimated_time_hours=bounty["effort_hours"],
                experience_required=ExperienceLevel.NONE,
                portfolio_required=False,
                interview_required=False,
                technical_test_required=False,
                registration_required=True,
                time_to_payout_days=7.0,
                reputation=0.85,
                risk=0.15,
                payment_proven=True,
                stability=0.75,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=bounty["tags"],
                employment_type=EmploymentType.CONTRACT,
                hourly_rate_usd=bounty["reward"] / max(bounty["effort_hours"], 1),
                time_to_first_work_hours=24.0,
                rate_source="platform",
            )
            out.append(op)

        logger.info("[BOUNTYBOARD] Fetched %d curated bounties", len(out))
        return out


def build_bountyboard_adapter() -> BountyBoardAdapter:
    """Build BountyBoard adapter."""
    return BountyBoardAdapter()
