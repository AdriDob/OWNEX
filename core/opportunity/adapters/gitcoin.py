"""GitCoin Adapter — Dev bounty platform for open source contributions.

Platform for finding gitcoin opportunities through the Direct Work Engine.
"""

from __future__ import annotations

from typing import Any

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class GitCoinAdapter(OpportunityAdapter):
    """GitCoin adapter — opportunites from gitcoin."""

    platform: str = "gitcoin"
    cycle: str = "forge"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("gitcoin", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch gitcoin opportunities."""
        try:
            return self._get_curated_direct_work()
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("GitCoinAdapter fetch failed: %s", e)
            return self._get_curated_direct_work()

    def _get_curated_direct_work(self) -> list[RawOpportunity]:
        """Curated direct-work-friendly gitcoin opportunities."""
        fallback_data = [
            {
                "id": "gitcoin_task_1",
                "name": "GitCoin Task Example",
                "description": "Example gitcoin opportunity",
                "url": "https://gitcoin.com",
                "reward": 100.0,
                "effort_hours": 5.0,
                "tags": ["gitcoin", "task-based"],
                "source_type": "direct_bounty",
                "source_name": "gitcoin",
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
