"""ClawHunt Adapter — Programming tasks for agents.

Platform: clawhunt.xyz
Features: retained budgets, code tasks, CLI/MCP access
Argentina: Experimental, USD 35 medium budget (declarations, not verified)
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class ClawHuntAdapter(OpportunityAdapter):
    """ClawHunt adapter — programming tasks for agents."""

    platform: str = "clawhunt"
    cycle: str = "pulse"
    reward_currency: str = "USD"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("clawhunt", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch ClawHunt opportunities."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.clawhunt.xyz/v1/tasks",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:30]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"clawhunt_{task.get('id')}",
                            name=task.get("title") or "ClawHunt Task",
                            description=task.get("description") or "",
                            platform="clawhunt",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_hours", 4)),
                            tags=task.get("tags", ["programming", "agent", "task"]),
                            specialization=task.get("specialization", "backend"),
                            remote=task.get("remote", True),
                            reward_currency=task.get("currency", "USD"),
                            reward_status=task.get("status", "open"),
                            source_type="dev_task",
                            source_name="clawhunt",
                            metadata={"original": task},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("ClawHuntAdapter fetch failed: %s", e)
            return []
