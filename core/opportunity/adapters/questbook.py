"""Questbook adapter — Grant & bounty management platform (Forge cycle).

Source: https://questbook.xyz
Payout: Variable
Token: USDC/ETH
Vetting: Apply
Recurrencia: ✅ Media
Volumen: Grant & bounty management.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class QuestbookAdapter(OpportunityAdapter):
    """Questbook adapter — Grant & bounty management platform (Forge cycle)."""

    platform: str = "questbook"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("questbook", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch grants and bounties from Questbook."""
        try:
            headers = get_auth_headers("questbook", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.questbook.xyz/v1/grants",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                grants = data.get("grants", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for grant in grants[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"questbook_{grant.get('id')}",
                            name=grant.get("title") or "Questbook Grant",
                            description=grant.get("description") or "",
                            platform="questbook",
                            url=grant.get("url"),
                            reward=float(grant.get("reward", 0)),
                            effort_hours=float(grant.get("estimated_hours", 8)),
                            tags=grant.get("tokens", ["usdc", "eth"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="questbook",
                            metadata={"original": grant},
                            created_at=grant.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("QuestbookAdapter fetch failed: %s", e)
            return []
