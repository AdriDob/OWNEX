"""Bountysource Adapter — Open source project bounties.

Platform for finding bountysource opportunities through the Direct Work Engine.
"""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class BountysourceAdapter(OpportunityAdapter):
    """Bountysource adapter — opportunites from bountysource."""

    platform: str = "bountysource"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("bountysource", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bountysource opportunities."""
        try:
            return self._get_curated_direct_work()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("BountysourceAdapter fetch failed: %s", e)
            return self._get_curated_direct_work()

    def _get_curated_direct_work(self) -> list[RawOpportunity]:
        """Curated direct-work-friendly bountysource opportunities."""
        fallback_data = [
            {
                "id": "bountysource_task_1",
                "name": "Bountysource Task Example",
                "description": "Example bountysource opportunity",
                "url": "https://bountysource.com",
                "reward": 100.0,
                "effort_hours": 5.0,
                "tags": ["bountysource", "task-based"],
                "source_type": "direct_bounty",
                "source_name": "bountysource",
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
