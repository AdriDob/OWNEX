"""Algora — real discovery adapter for the Direct Work Engine.

Wraps the legacy ``core/opportunity/adapters/forge/algora.py`` (public Algora API,
auth optional). The conversion itself lives in the shared
``LegacyOpportunityDweAdapter`` so every platform uses one path.
"""

from __future__ import annotations

import logging
from typing import Any

from api.adapters.legacy import LegacyOpportunityDweAdapter
from cores.direct_work_engine.models import (
    EmploymentType,
    OpportunityCategory,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.algora")


class AlgoraDweAdapter(LegacyOpportunityDweAdapter):
    """Bridges the legacy Algora adapter into DWE discovery."""

    def __init__(self, config: dict[str, Any] | None = None):
        from core.opportunity.adapters.forge.algora import fetch_opportunities

        # Create a minimal adapter object with fetch_opportunities method
        class _AlgoraAdapter:
            async def fetch_opportunities(self) -> list[dict[str, Any]]:
                return await fetch_opportunities()

        super().__init__(
            _AlgoraAdapter(),
            name="algora",
            platform=WorkPlatform.ALGORA,
            category=OpportunityCategory.DEV_BOUNTY,
            employment_type=EmploymentType.BOUNTY,
            tier=1,
            analysis_cadence_hours=6,
        )
