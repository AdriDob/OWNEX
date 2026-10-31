"""Taskmarket adapter — CLI micro-bounty platform (Forge cycle).

Source: https://taskmarket.xyz
Payout: $2–$100/bounty
Token: USDC (Base) + OUSD (Tempo)
Vetting: CLI
Cobro AR: ✅ Wallet
Recurrencia: ✅ Media
Volumen: $7.40/win. 150-320 submissions/task.
Estado: ✅ ACTIVO (lotería)
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class TaskmarketAdapter(OpportunityAdapter):
    """Taskmarket adapter — CLI micro-bounty platform (Forge cycle)."""

    platform: str = "taskmarket"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("taskmarket", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch micro-bounties from Taskmarket CLI/API."""
        try:
            # Taskmarket operates via CLI; fetch via its HTTP endpoint or task list
            headers = get_auth_headers("taskmarket", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.taskmarket.xyz/v1/tasks",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                tasks = data.get("tasks", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for task in tasks[:30]:  # Limit - high volume
                    raw_opps.append(
                        RawOpportunity(
                            id=f"taskmarket_{task.get('id')}",
                            name=task.get("title") or "Taskmarket Task",
                            description=task.get("description") or "",
                            platform="taskmarket",
                            url=task.get("url"),
                            reward=float(task.get("reward", 0)),
                            effort_hours=float(task.get("estimated_hours", 2)),
                            tags=task.get("tokens", ["usdc", "ousd"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="taskmarket",
                            metadata={"original": task},
                            created_at=task.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("TaskmarketAdapter fetch failed: %s", e)
            return []
