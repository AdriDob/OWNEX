"""TaskMarket Adapter — Bounties with USDC escrow on Base.

Platform: taskmarket.xyz (or similar)
Features: escrow USDC Base, agents & automation, auction/pitch/benchmark
Argentina: Crypto-compatible, USDC accessible
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class TaskMarketAdapter(OpportunityAdapter):
    """TaskMarket adapter — bounties with USDC escrow on Base."""

    platform: str = "taskmarket"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("taskmarket", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch TaskMarket opportunities."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.taskmarket.xyz/v1/tasks",
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
                            id=f"taskmarket_{task.get('id')}",
                            name=task.get("title") or "TaskMarket Task",
                            description=task.get("description") or "",
                            platform="taskmarket",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_hours", 4)),
                            tags=task.get("tags", ["bounty", "agent", "automation"]),
                            specialization=task.get("specialization", "backend"),
                            remote=task.get("remote", True),
                            reward_currency=task.get("currency", "USDC"),
                            reward_status=task.get("status", "open"),
                            source_type="bounty",
                            source_name="taskmarket",
                            metadata={"original": task},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("TaskMarketAdapter fetch failed: %s", e)
            return []
