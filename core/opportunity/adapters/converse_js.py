"""converse.js adapter — GitHub PR crypto bounty platform (Forge cycle).

Source: https://conversejs.org
Payout: $100/bounty
Token: Crypto (variable)
Vetting: GitHub PR
Cobro AR: ✅ Wallet
Recurrencia: ✅ Media
Volumen: 30% merge rate. 1-2 semanas.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class ConverseJSAdapter(OpportunityAdapter):
    """converse.js adapter — GitHub PR crypto bounty platform (Forge cycle)."""

    platform: str = "converse_js"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("converse_js", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch GitHub PR crypto bounties from converse.js."""
        try:
            # converse.js integrates with GitHub; fetch PR bounties
            headers = get_auth_headers("converse_js", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.conversejs.org/v1/pr-bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                prs = data.get("prs", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for pr in prs[:15]:  # Limit
                    raw_opps.append(
                        RawOpportunity(
                            id=f"converse_js_{pr.get('id')}",
                            name=pr.get("title") or "converse.js PR Bounty",
                            description=pr.get("description") or "",
                            platform="converse_js",
                            url=pr.get("url"),
                            reward=float(pr.get("reward", 100)),
                            effort_hours=float(pr.get("estimated_hours", 8)),
                            tags=pr.get("tokens", ["crypto"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="converse_js",
                            metadata={"original": pr},
                            created_at=pr.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("ConverseJSAdapter fetch failed: %s", e)
            return []
