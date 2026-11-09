"""DoraHacks adapter — Bounties + hackathons platform (Forge cycle).

Source: https://dorahacks.io
Payout: Variable
Token: Crypto
Vetting: Apply
Recurrencia: ✅ Media
Volumen: Bounties + hackathons.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class DoraHacksAdapter(OpportunityAdapter):
    """DoraHacks adapter — Bounties + hackathons platform (Forge cycle)."""

    platform: str = "dorahacks"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("dorahacks", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch bounties and hackathons from DoraHacks."""
        try:
            headers = get_auth_headers("dorahacks", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.dorahacks.io/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:25]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"dorahacks_{bounty.get('id')}",
                            name=bounty.get("title") or "DoraHacks Bounty",
                            description=bounty.get("description") or "",
                            platform="dorahacks",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 8)),
                            tags=bounty.get("tokens", ["crypto"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="dorahacks",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("DoraHacksAdapter fetch failed: %s", e)
            return []
