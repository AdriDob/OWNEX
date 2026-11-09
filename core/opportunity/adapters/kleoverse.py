"""Kleoverse adapter — Web3 talent marketplace (Forge cycle)."""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class KleoverseAdapter(OpportunityAdapter):
    """Kleoverse adapter — Web3 talent marketplace (Forge cycle)."""

    platform: str = "kleoverse"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("kleoverse", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch Web3 talent bounties from Kleoverse."""
        try:
            headers = get_auth_headers("kleoverse", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.kleoverse.xyz/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:15]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"kleoverse_{bounty.get('id')}",
                            name=bounty.get("title") or "Kleoverse Bounty",
                            description=bounty.get("description") or "",
                            platform="kleoverse",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 6)),
                            tags=bounty.get("tags", ["crypto"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="kleoverse",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("KleoverseAdapter fetch failed: %s", e)
            return []
