"""BasedAgents Adapter — Agent task marketplace with USDC escrow.

Platform: basedagents.xyz
Features: escrow USDC, 7-day auto-accept, API/CLI/MCP, reputation system
Argentina: Experimental, small volume
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class BasedAgentsAdapter(OpportunityAdapter):
    """BasedAgents adapter — agent task marketplace with USDC escrow."""

    platform: str = "basedagents"
    cycle: str = "pulse"
    reward_currency: str = "USDC"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("basedagents", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch BasedAgents opportunities."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.basedagents.xyz/v1/tasks",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"basedagents_{task.get('id')}",
                            name=task.get("title") or "BasedAgents Task",
                            description=task.get("description") or "",
                            platform="basedagents",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_hours", 4)),
                            tags=task.get("tags", ["agent", "task", "usdc"]),
                            specialization=task.get("specialization", "backend"),
                            remote=task.get("remote", True),
                            reward_currency=task.get("currency", "USDC"),
                            reward_status=task.get("status", "open"),
                            source_type="agent_task",
                            source_name="basedagents",
                            metadata={"original": task},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("BasedAgentsAdapter fetch failed: %s", e)
            return []
