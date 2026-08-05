"""Generic bridge for legacy OpportunityAdapters into the Direct Work Engine.

Any existing ``core/opportunity/adapters`` class that returns ``RawOpportunity``
can be wrapped with ``LegacyOpportunityDweAdapter`` — one conversion path, no
duplicated per-platform code. Lives in the API layer so the DWE stays decoupled
from ``core/``.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    DifficultyLevel,
    EmploymentType,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.legacy")


class LegacyOpportunityDweAdapter(BaseDiscoveryAdapter):
    """Wraps any legacy ``OpportunityAdapter`` that yields ``RawOpportunity``."""

    def __init__(
        self,
        legacy: Any,
        name: str,
        platform: WorkPlatform,
        category: OpportunityCategory,
        employment_type: EmploymentType,
        payment_method: PaymentMethod = PaymentMethod.PLATFORM_CREDIT,
        registration_required: bool = True,
        tier: int = 2,
        analysis_cadence_hours: int = 24,
    ) -> None:
        self._legacy = legacy
        self._category = category
        self._employment_type = employment_type
        self._payment_method = payment_method
        self._registration_required = registration_required
        source = DiscoverySource(
            name=name,
            platform=platform,
            categories=[category],
            tier=tier,
            analysis_cadence_hours=analysis_cadence_hours,
            requires_auth=(tier == 2),
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        raw_opps = await self._legacy.fetch_opportunities()
        return [self._convert(raw) for raw in raw_opps]

    async def validate_connection(self) -> bool:
        # Discovery isolates errors; keep the gate cheap and optimistic.
        return True

    def _convert(self, raw: Any) -> Opportunity:
        effort = float(getattr(raw, "effort_hours", 1.0) or 1.0)
        if effort <= 4:
            difficulty = DifficultyLevel.BEGINNER
        elif effort <= 8:
            difficulty = DifficultyLevel.INTERMEDIATE
        else:
            difficulty = DifficultyLevel.ADVANCED

        return Opportunity(
            id=str(getattr(raw, "id", "")),
            title=str(getattr(raw, "name", "") or self.source.name),
            platform=self.source.platform,
            category=self._category,
            url=getattr(raw, "url", "") or "",
            description=str(getattr(raw, "description", "") or ""),
            remote=True,
            payment=float(getattr(raw, "reward", 0.0) or 0.0),
            currency="USD",
            payment_method=self._payment_method,
            difficulty=difficulty,
            language_required="english",
            estimated_time_hours=effort,
            experience_required=ExperienceLevel.NONE,
            portfolio_required=False,
            interview_required=False,
            technical_test_required=False,
            registration_required=self._registration_required,
            time_to_payout_days=None,
            payment_proven=False,
            stability=0.5,
            accepts_beginner=True,
            accepts_freelancers=True,
            accepts_individuals=True,
            accepts_ai_tools=True,
            asynchronous=True,
            technology_tags=list(getattr(raw, "tags", []) or []),
            employment_type=self._employment_type,
        )


def build_default_adapters() -> list[BaseDiscoveryAdapter]:
    """Build the default real discovery adapters (idempotent registration list).

    Each entry is constructed lazily so an unavailable platform only logs and
    never blocks the engine. Freelancer is classified as the freelance model
    (selection world); bounties are outcome-based.
    """
    adapters: list[BaseDiscoveryAdapter] = []

    try:
        from api.adapters.direct_work_opire import OpireDweAdapter

        adapters.append(OpireDweAdapter())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build opire adapter: %s", exc)

    try:
        from api.adapters.direct_work_bugbounty import build_bugbounty_adapters

        adapters.extend(build_bugbounty_adapters())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build bugbounty adapters: %s", exc)

    try:
        from core.opportunity.adapters.issuehunt import IssueHuntAdapter

        adapters.append(
            LegacyOpportunityDweAdapter(
                IssueHuntAdapter(),
                name="issuehunt",
                platform=WorkPlatform.ISSUE_HUNT,
                category=OpportunityCategory.DEV_BOUNTY,
                employment_type=EmploymentType.BOUNTY,
                tier=1,
                analysis_cadence_hours=6,
            )
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build issuehunt adapter: %s", exc)

    try:
        from core.opportunity.adapters.freelancer import FreelancerAdapter

        adapters.append(
            LegacyOpportunityDweAdapter(
                FreelancerAdapter(),
                name="freelancer",
                platform=WorkPlatform.FREELANCER,
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.FREELANCE,
                registration_required=True,
                tier=3,
                analysis_cadence_hours=72,
            )
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build freelancer adapter: %s", exc)

    try:
        from core.opportunity.adapters.opencollective import OpenCollectiveAdapter

        adapters.append(
            LegacyOpportunityDweAdapter(
                OpenCollectiveAdapter(),
                name="opencollective",
                platform=WorkPlatform.OPEN_COLLECTIVE,
                category=OpportunityCategory.DEV_BOUNTY,
                employment_type=EmploymentType.CONTRACT,
                tier=3,
                analysis_cadence_hours=72,
            )
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build opencollective adapter: %s", exc)

    # Pulse cycle adapters (AI work / data annotation — speed 1.0, cobro en días)
    try:
        from core.opportunity.adapters.pulse import (
            DataAnnotationAdapter,
            FreelancerMicrotaskAdapter,
            LinkedInEasyApplyAdapter,
            MindriftAdapter,
            OpyreMicrotaskAdapter,
            OutlierAdapter,
            RemotasksAdapter,
        )

        adapters.append(
            LegacyOpportunityDweAdapter(
                OutlierAdapter(),
                name="outlier",
                platform=WorkPlatform.OUTLIER,
                category=OpportunityCategory.AI_EVALUATION,
                employment_type=EmploymentType.MICROTASK,
                tier=1,
                analysis_cadence_hours=6,
            )
        )
        adapters.append(
            LegacyOpportunityDweAdapter(
                DataAnnotationAdapter(),
                name="dataannotation",
                platform=WorkPlatform.DATA_ANNOTATION_PLATFORM,
                category=OpportunityCategory.DATA_ANNOTATION,
                employment_type=EmploymentType.MICROTASK,
                tier=1,
                analysis_cadence_hours=6,
            )
        )
        adapters.append(
            LegacyOpportunityDweAdapter(
                MindriftAdapter(),
                name="mindrift",
                platform=WorkPlatform.MINDRIFT,
                category=OpportunityCategory.AI_EVALUATION,
                employment_type=EmploymentType.MICROTASK,
                tier=1,
                analysis_cadence_hours=6,
            )
        )
        adapters.append(
            LegacyOpportunityDweAdapter(
                RemotasksAdapter(),
                name="remotasks",
                platform=WorkPlatform.REMOTASKS,
                category=OpportunityCategory.DATA_ANNOTATION,
                employment_type=EmploymentType.MICROTASK,
                tier=1,
                analysis_cadence_hours=6,
            )
        )
        adapters.append(
            LegacyOpportunityDweAdapter(
                OpyreMicrotaskAdapter(),
                name="opyre_microtask",
                platform=WorkPlatform.OPYRE_MICROTASK,
                category=OpportunityCategory.DATA_ANNOTATION,
                employment_type=EmploymentType.MICROTASK,
                tier=1,
                analysis_cadence_hours=6,
            )
        )
        adapters.append(
            LegacyOpportunityDweAdapter(
                LinkedInEasyApplyAdapter(),
                name="linkedin_easyapply",
                platform=WorkPlatform.LINKEDIN,
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.FULL_TIME,
                tier=2,
                analysis_cadence_hours=24,
            )
        )
        adapters.append(
            LegacyOpportunityDweAdapter(
                FreelancerMicrotaskAdapter(),
                name="freelancer_microtask",
                platform=WorkPlatform.FREELANCER_MICROTASK,
                category=OpportunityCategory.DEV_BOUNTY,
                employment_type=EmploymentType.MICROTASK,
                tier=2,
                analysis_cadence_hours=24,
            )
        )
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not build pulse adapters: %s", exc)

    return adapters
