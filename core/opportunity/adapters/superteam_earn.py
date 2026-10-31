"""Superteam Earn adapter — USDC/SOL dev bounty platform (Forge cycle).

Source: https://superteam.fun/earn
Payout: $500–$6,000/bounty
Token: USDC/SOL
Vetting: Twitter OAuth + KYC al payout
Recurrencia: ✅ Alta
Volumen: $200-$2K bounties semanales. Agent API.
Estado: ⚠️ KYC
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class SuperteamEarnAdapter(OpportunityAdapter):
    """Superteam Earn adapter — USDC/SOL dev bounty platform (Forge cycle)."""

    platform: str = "superteam_earn"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("superteam_earn", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("superteam_earn", merged_config)
        self.requires_kyc = True  # KYC required at payout

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from Superteam Earn."""
        try:
            headers = get_auth_headers("superteam_earn", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.superteam.fun/earn/v1/bounties",
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
                            id=f"superteam_earn_{bounty.get('id')}",
                            name=bounty.get("title") or "Superteam Earn Bounty",
                            description=bounty.get("description") or "",
                            platform="superteam_earn",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward_usd", bounty.get("reward", 0))),
                            effort_hours=float(bounty.get("estimated_hours", 8)),
                            tags=bounty.get("tags", ["usdc", "sol"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="superteam_earn",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("SuperteamEarnAdapter fetch failed: %s", e)
            return []
