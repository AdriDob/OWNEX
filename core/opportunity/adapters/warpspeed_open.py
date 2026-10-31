"""WarpSpeed OPEN adapter — USDC bounty platform on Base (Forge cycle).

Source: https://warpspeed.xyz/op
Payout: $330–$960/bounty
Token: USDC (Base)
Vetting: Signup + approval
Cobro AR: ✅ Wallet
Recurrencia: ✅ Media
Volumen: 12+ bounties, 20% merge, 30h con AI
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class WarpSpeedOpenAdapter(OpportunityAdapter):
    """WarpSpeed OPEN adapter — USDC bounty platform on Base (Forge cycle)."""

    platform: str = "warpspeed_open"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("warpspeed_open", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("warpspeed_open", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open bounties from WarpSpeed OPEN API."""
        try:
            headers = get_auth_headers("warpspeed_open", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.warpspeed.xyz/v1/op/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:12]:  # Limit to 12+
                    raw_opps.append(
                        RawOpportunity(
                            id=f"warpspeed_open_{bounty.get('id')}",
                            name=bounty.get("title") or "WarpSpeed OPEN Bounty",
                            description=bounty.get("description") or "",
                            platform="warpspeed_open",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 30)),
                            tags=bounty.get("tokens", ["usdc", "base"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="warpspeed_open",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("WarpSpeedOpenAdapter fetch failed: %s", e)
            return []
