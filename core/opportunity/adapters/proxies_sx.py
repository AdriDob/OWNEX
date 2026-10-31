"""Proxies.sx adapter — Solana dev bounty platform (Forge cycle).

Source: https://proxies.sx
Payout: $50–$200/bounty
Token: $SX (Solana)
Vetting: Registro
Cobro AR: ✅ Wallet
Recurrencia: ✅ Waves cada 1-2 sem
Volumen: 14 bounties, $1,150 pool
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class ProxiesSXAdapter(OpportunityAdapter):
    """Proxies.sx adapter — Solana dev bounty platform (Forge cycle)."""

    platform: str = "proxies_sx"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("proxies_sx", config)
        super().__init__(merged_config)
        self.api_key = get_api_key("proxies_sx", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch open bounties from Proxies.sx API."""
        try:
            headers = get_auth_headers("proxies_sx", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.proxies.sx/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:14]:  # Limit to ~14 bounties
                    raw_opps.append(
                        RawOpportunity(
                            id=f"proxies_sx_{bounty.get('id')}",
                            name=bounty.get("title") or "Proxies.sx Bounty",
                            description=bounty.get("description") or "",
                            platform="proxies_sx",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 4)),
                            tags=bounty.get("tags", ["solana", "SX"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="proxies_sx",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ProxiesSXAdapter fetch failed: %s", e)
            return []
