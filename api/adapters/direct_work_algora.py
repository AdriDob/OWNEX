"""Algora.io Adapter — GitHub bounties with automatic payment.

Zero-barrier: GitHub login → claim issue → submit PR → automatic payment.
No interview, no portfolio, no CV required.
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

logger = logging.getLogger("ownex.adapters.algora")


class AlgoraAdapter(LegacyOpportunityDweAdapter):
    """Algora.io — GitHub bounties with automatic payment.

    Real implementation requires:
    - GitHub OAuth token
    - Algora API access
    - For now: curated deep-links to active bounties.
    """

    CURATED_BOUNTIES = [
        {
            "id": "algora_rudderstack_go",
            "name": "RudderStack Go SDK Improvements",
            "description": "Improve Go SDK for event streaming. Bounty: $2,000. No interview, PR-based.",
            "url": "https://algora.io/issues/rudderstack/rudderstack-go-sdk",
            "reward": 2000.0,
            "effort_hours": 8.0,
            "tags": ["go", "golang", "sdk", "backend", "open_source"],
            "difficulty": "medium",
            "language": "go",
        },
        {
            "id": "algora_appflowy_flutter",
            "name": "AppFlowy Flutter Bug Fixes",
            "description": "Fix critical bugs in Flutter productivity app. Bounty: $500. No interview.",
            "url": "https://algora.io/issues/AppFlowy/AppFlowy",
            "reward": 500.0,
            "effort_hours": 6.0,
            "tags": ["flutter", "dart", "mobile", "ui", "open_source"],
            "difficulty": "easy",
            "language": "dart",
        },
        {
            "id": "algora_trigger_dev",
            "name": "Trigger.dev TypeScript Improvements",
            "description": "Improve Next.js/TypeScript background job system. Bounty: $200. No interview.",
            "url": "https://algora.io/issues/triggerdotdev/trigger.dev",
            "reward": 200.0,
            "effort_hours": 4.0,
            "tags": ["typescript", "nextjs", "backend", "api", "open_source"],
            "difficulty": "easy",
            "language": "typescript",
        },
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        # Algora doesn't have a legacy engine, so we pass None
        super().__init__(
            None,
            name="algora",
            platform=WorkPlatform.ALGORA,
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.CONTRACT,
            payment_method=PaymentMethod.PLATFORM_CREDIT,
            registration_required=True,
            tier=1,
            analysis_cadence_hours=24,
        )

    async def fetch_opportunities(self) -> list[Opportunity]:
        """Fetch Algora bounties (curated deep-links for now)."""
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
                platform=WorkPlatform.ALGORA,
                category=OpportunityCategory.DEV_BOUNTY,
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
                time_to_payout_days=7.0,  # Algora typically pays faster
                reputation=0.9,
                risk=0.1,
                payment_proven=True,
                stability=0.8,
                accepts_beginner=True,
                accepts_freelancers=True,
                accepts_individuals=True,
                accepts_ai_tools=True,
                asynchronous=True,
                technology_tags=bounty["tags"],
                employment_type=EmploymentType.BOUNTY,
                hourly_rate_usd=bounty["reward"] / max(bounty["effort_hours"], 1),
                time_to_first_work_hours=24.0,
                rate_source="platform",
            )
            out.append(op)

        logger.info("[ALGORA] Fetched %d curated bounties", len(out))
        return out


def build_algora_adapter() -> AlgoraAdapter:
    """Build Algora adapter."""
    return AlgoraAdapter()
