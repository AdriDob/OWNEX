"""Alignerr Adapter — Platform for engineering freelance opportunities and coding tasks."""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class AlignerrAdapter(OpportunityAdapter):
    """Alignerr adapter - engineering and coding freelance opportunities.

    Platform for finding freelance engineering gigs, coding tasks,
    and project-based work with direct-work-friendly formats.
    """

    platform: str = "alignerr"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("alignerr", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch engineering/freelance opportunities from Alignerr."""
        try:
            return self._get_curated_direct_work()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("AlignerrAdapter fetch failed: %s", e)
            return self._get_curated_direct_work()

    def _get_curated_direct_work(self) -> list[RawOpportunity]:
        """Curated direct-work-friendly Alignerr opportunities."""
        fallback_data = [
            {
                "id": "alignerr_engineer_task",
                "name": "Senior Engineer - Alignerr Task",
                "description": "High-quality engineering task from Alignerr platform",
                "url": "https://alignerr.com/tasks",
                "reward": 200.0,
                "effort_hours": 10.0,
                "tags": ["engineering", "freelance", "task-based"],
                "source_type": "direct_bounty",
                "source_name": "alignerr",
            },
            {
                "id": "alignerr_coding_task",
                "name": "Code Review Task - Alignerr",
                "description": "Code review and feedback task from Alignerr",
                "url": "https://alignerr.com/reviews",
                "reward": 75.0,
                "effort_hours": 2.0,
                "tags": ["code-review", "freelance", "quick-task"],
                "source_type": "direct_bounty",
                "source_name": "alignerr",
            },
        ]

        raw_opps: list[RawOpportunity] = []
        for item in fallback_data:
            raw_opps.append(
                RawOpportunity(
                    id=item["id"],
                    name=item["name"],
                    description=item["description"],
                    platform=self.platform,
                    url=item["url"],
                    reward=item["reward"],
                    effort_hours=item["effort_hours"],
                    category="dev_bounty",
                    specialization="backend",
                    remote=True,
                )
            )

        return raw_opps
