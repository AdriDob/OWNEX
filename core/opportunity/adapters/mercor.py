"""Mercor Adapter — Tech talent and coding assessments.

Platform for finding mercor opportunities through the Direct Work Engine.
"""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class MercorAdapter(OpportunityAdapter):
    """Mercor adapter — opportunites from mercor."""

    platform: str = "mercor"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("mercor", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch mercor opportunities."""
        try:
            return self._get_curated_direct_work()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("MercorAdapter fetch failed: %s", e)
            return self._get_curated_direct_work()

    def _get_curated_direct_work(self) -> list[RawOpportunity]:
        """Curated direct-work-friendly mercor opportunities."""
        fallback_data = [
            {
                "id": "mercor_task_1",
                "name": "Mercor Task Example",
                "description": "Example mercor opportunity",
                "url": "https://mercor.com",
                "reward": 100.0,
                "effort_hours": 5.0,
                "tags": ["mercor", "task-based"],
                "source_type": "direct_bounty",
                "source_name": "mercor",
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
