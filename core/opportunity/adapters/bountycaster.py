"""Bountycaster adapter — Multi-token dev bounty platform (Forge cycle).

Source: https://bountycaster.xyz
Payout: $20–$5,000/bounty
Token: USDC/ETH/DEGEN/OP (Base)
Vetting: Farcaster account
Cobro AR: ✅ Wallet
Recurrencia: ✅ Alta (social)
Volumen: Bajo pero constante. 0% fee.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class BountycasterAdapter(OpportunityAdapter):
    """Bountycaster adapter — Multi-token dev bounty platform (Forge cycle)."""

    platform: str = "bountycaster"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("bountycaster", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("bountycaster", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open bounties from Bountycaster API."""
        try:
            headers = get_auth_headers("bountycaster", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.bountycaster.xyz/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:10]:  # Limit
                    raw_opps.append(
                        RawOpportunity(
                            id=f"bountycaster_{bounty.get('id')}",
                            name=bounty.get("title") or "Bountycaster Bounty",
                            description=bounty.get("description") or "",
                            platform="bountycaster",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 6)),
                            tags=bounty.get("tokens", ["usdc", "eth", "degen", "op"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="bountycaster",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("BountycasterAdapter fetch failed: %s", e)
            return []
