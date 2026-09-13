"""Polar.sh Adapter — GitHub funding and issue sponsorship.

Zero-barrier: GitHub OAuth → fund issues → get paid when resolved.
Polar integrates directly with GitHub for seamless funding.
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

logger = logging.getLogger("ownex.adapters.polar")


class PolarAdapter(LegacyOpportunityDweAdapter):
    """Polar.sh — GitHub funding and issue sponsorship.

    Real implementation requires:
    - GitHub OAuth token
    - Polar API access
    - For now: curated deep-links to active funded issues.
    """

    CURATED_BOUNTIES = [
        {
            "id": "polar_rust_analyzer",
            "name": "Rust Analyzer Performance Improvements",
            "description": "Improve Rust language server performance. Bounty: $500-1,000. No interview.",
            "url": "https://polar.sh/rust-analyzer/rust-analyzer",
            "reward": 1000.0,
            "effort_hours": 12.0,
            "tags": ["rust", "language-server", "performance", "open_source"],
            "difficulty": "hard",
            "language": "rust",
        },
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        # Polar doesn't have a legacy engine, so we pass None
        super().__init__(
            None,
            name="polar",
            platform=WorkPlatform.POLAR,
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.CONTRACT,
            payment_method=PaymentMethod.PLATFORM_CREDIT,
            registration_required=True,
            tier=1,
            analysis_cadence_hours=24,
        )

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch Polar funded issues (curated deep-links for now)."""
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
                reputation=0.9,
                risk=0.1,
                payment_proven=True,
                stability=0.85,
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

        logger.info("[POLAR] Fetched %d curated funded issues", len(out))
        return out


def build_polar_adapter() -> PolarAdapter:
    """Build Polar adapter."""
    return PolarAdapter()
