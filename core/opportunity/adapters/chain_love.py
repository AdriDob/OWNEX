"""Chain.Love adapter — Algorand USDC bounty (Forge cycle)."""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class ChainLoveAdapter(OpportunityAdapter):
    """Chain.Love adapter — Algorand USDC bounty (Forge cycle)."""

    platform: str = "chain_love"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("chain_love", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Chain.Love bounties."""
        try:
            headers = get_auth_headers("chain_love", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.chain.love/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"chain_love_{bounty.get('id')}",
                            name=bounty.get("title") or "Chain.Love Bounty",
                            description=bounty.get("description") or "",
                            platform="chain_love",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 3)),
                            tags=bounty.get("tags", ["usdc", "algorand"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="chain_love",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ChainLoveAdapter fetch failed: %s", e)
            return []
