"""Algora.io adapter — OSS bounties on GitHub issues (Forge cycle).

Source: https://algora.io
Payout: $50–$500/bounty
Token: USDC/ETH (Stripe)
Vetting: Registro
Cobro AR: ✅
Recurrencia: ⚠️ Media
Volumen: 141 bounties abiertos, $66,425 total (sep 2026). PERO: $740 owed, $0 received. 15% merge.
Estado: ⚠️ PAGO EN RIESGO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class AlgoraAdapter(OpportunityAdapter):
    """Algora.io adapter — OSS bounties on GitHub issues (Forge cycle)."""

    platform: str = "algora"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("algora", config)
        super().__init__(merged_config)
        self.token = get_api_key("algora", merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties from Algora API."""
        try:
            headers = get_auth_headers("algora", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.algora.xyz/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:20]:  # Algora has 141 open
                    raw_opps.append(
                        RawOpportunity(
                            id=f"algora_{bounty.get('id')}",
                            name=bounty.get("title") or "Algora.io Bounty",
                            description=bounty.get("description") or "",
                            platform="algora",
                            url=bounty.get("url"),
                            reward=float(bounty.get("amount", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 5)),
                            tags=bounty.get("labels", ["oss", "github"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="algora",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("AlgoraAdapter fetch failed: %s", e)
            return []
