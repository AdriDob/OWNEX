"""Dework adapter — DAO dev bounty platform (Forge cycle).

Source: https://dework.xyz
Payout: $50–$5,000+ (any token on-chain)
Vetting: Discord + wallet
Recurrencia: ✅ Alta (500+ DAOs)
Volumen: $1.2M en payouts (2025). 10,000+ usuarios.
Docs: $50-200, features $2K-5K.
Pago: Cualquier token on-chain (Gnosis Safe, MetaMask, Phantom, WalletConnect).
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class DeworkAdapter(OpportunityAdapter):
    """Dework adapter — DAO dev bounty platform (Forge cycle)."""

    platform: str = "dework"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("dework", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch DAO bounties from Dework."""
        try:
            headers = get_auth_headers("dework", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.dework.xyz/v1/dao-bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:50]:  # High volume
                    raw_opps.append(
                        RawOpportunity(
                            id=f"dework_{bounty.get('id')}",
                            name=bounty.get("title") or "Dework DAO Bounty",
                            description=bounty.get("description") or "",
                            platform="dework",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 6)),
                            tags=bounty.get("tokens", ["any"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="dework",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("DeworkAdapter fetch failed: %s", e)
            return []
