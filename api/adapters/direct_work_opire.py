"""Opire — real discovery adapter for the Direct Work Engine.

Wraps the legacy ``core/opportunity/adapters/opire.py`` (public Opire API, auth
optional). The conversion itself lives in the shared
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

logger = logging.getLogger("ownex.api.direct_work.adapters.opire")


class OpireDweAdapter(LegacyOpportunityDweAdapter):
    """Bridges the legacy Opire adapter into DWE discovery."""

    def __init__(self, config: dict[str, Any] | None = None):
        from core.opportunity.adapters.opire import OpireAdapter

        super().__init__(
            OpireAdapter(config),
            name="opire",
            platform=WorkPlatform.OPIRE,
            category=OpportunityCategory.DEV_BOUNTY,
            employment_type=EmploymentType.BOUNTY,
            tier=1,
            analysis_cadence_hours=6,
        )
