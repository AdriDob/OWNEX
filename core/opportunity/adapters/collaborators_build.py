"""Collaborators.build adapter — GitHub PR dev bounty platform (Forge cycle).

Source: https://collaborators.build
Payout: Variable (escrow)
Token: USDC (Base)
Vetting: GitHub PR
Cobro AR: ✅ Wallet
Recurrencia: ✅ Media
Volumen: GitHub issues con USDC. Pago automático on merge.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class CollaboratorsBuildAdapter(OpportunityAdapter):
    """Collaborators.build adapter — GitHub PR dev bounty platform (Forge cycle)."""

    platform: str = "collaborators_build"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("collaborators_build", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch GitHub PR bounties from Collaborators.build."""
        try:
            # Collaborators.build integrates with GitHub; fetch PR bounties
            headers = get_auth_headers("collaborators_build", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.collaborators.build/v1/pr-bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                prs = data.get("prs", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for pr in prs[:20]:  # Limit
                    raw_opps.append(
                        RawOpportunity(
                            id=f"collaborators_build_{pr.get('id')}",
                            name=pr.get("title") or "Collaborators.build PR Bounty",
                            description=pr.get("description") or "",
                            platform="collaborators_build",
                            url=pr.get("url"),
                            reward=float(pr.get("reward", 0)),
                            effort_hours=float(pr.get("estimated_hours", 4)),
                            tags=pr.get("tokens", ["usdc", "base"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="collaborators_build",
                            metadata={"original": pr},
                            created_at=pr.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("CollaboratorsBuildAdapter fetch failed: %s", e)
            return []
