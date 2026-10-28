"""Workana — discovery adapter for the Direct Work Engine.

Workana is a LATAM-focused freelance marketplace. No public API for
opportunity search, so this adapter is a thin, honest bridge:

- Returns [] when no cached/manual opportunities exist (never invents).
- Exposes the platform guide URL and access requirement via source metadata.
- Lets the Opportunity Scoring Engine evaluate manually-added Workana
  leads alongside the three primary engines (AI Training, Dev Bounties,
  Bug Bounties) when the channel is ACTIVE.

Channel status (ACTIVE/PAUSED/DISABLED/EXCLUDED) is managed by
``cores.freelance.channel_status`` — this adapter only discovers.
"""

from __future__ import annotations

import logging

from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource
from cores.direct_work_engine.models import (
    Opportunity,
    OpportunityCategory,
    WorkPlatform,
)

logger = logging.getLogger("ownex.api.direct_work.adapters.workana")


class WorkanaDweAdapter(BaseDiscoveryAdapter):
    """Manual-lead discovery for Workana (no public search API)."""

    def __init__(self) -> None:
        source = DiscoverySource(
            name="workana",
            platform=WorkPlatform.WORKANA,
            categories=[OpportunityCategory.SOFTWARE_ENGINEERING],
            tier=3,
            analysis_cadence_hours=72,
            requires_auth=True,
        )
        super().__init__(source)

    async def fetch_opportunities(self) -> list[Opportunity]:
        # No public API — return [] honestly. Manual leads are added
        # via WorkBank /analysis-card/ or /workbank/cycle with explicit payloads.
        # Never fabricate freelance gigs.
        return []

    async def validate_connection(self) -> bool:
        return True
