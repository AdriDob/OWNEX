"""Commonwealth adapter — DAO governance + bounties platform (Forge cycle).

Source: https://commonwealth.io
Payout: Variable (DAO treasury)
Token: Multi-chain
Vetting: Forum participation
Recurrencia: ✅ Media
Volumen: Governance + bounties.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class CommonwealthAdapter(OpportunityAdapter):
    """Commonwealth adapter — DAO governance + bounties platform (Forge cycle)."""

    platform: str = "commonwealth"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("commonwealth", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch DAO governance bounties from Commonwealth."""
        try:
            headers = get_auth_headers("commonwealth", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.commonwealth.io/v1/dao-bounties",
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
                            id=f"commonwealth_{bounty.get('id')}",
                            name=bounty.get("title") or "Commonwealth DAO Bounty",
                            description=bounty.get("description") or "",
                            platform="commonwealth",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 6)),
                            tags=bounty.get("tokens", ["multi"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="commonwealth",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("CommonwealthAdapter fetch failed: %s", e)
            return []
