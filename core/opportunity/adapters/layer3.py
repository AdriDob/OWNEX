"""Layer3 adapter — Multi-chain dev bounty platform (Forge cycle).

Source: https://layer3.xyz
Payout: Variable (tokens)
Token: Multi-chain
Vetting: Registro
Recurrencia: ✅ Alta
Volumen: Ecosystem quests. Learning + earning.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class Layer3Adapter(OpportunityAdapter):
    """Layer3 adapter — Multi-chain dev bounty platform (Forge cycle)."""

    platform: str = "layer3"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("layer3", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch ecosystem quests from Layer3."""
        try:
            headers = get_auth_headers("layer3", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.layer3.xyz/v1/quests",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                quests = data.get("quests", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for quest in quests[:30]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"layer3_{quest.get('id')}",
                            name=quest.get("title") or "Layer3 Quest",
                            description=quest.get("description") or "",
                            platform="layer3",
                            url=quest.get("url"),
                            reward=float(quest.get("reward", 0)),
                            effort_hours=float(quest.get("estimated_hours", 4)),
                            tags=quest.get("tokens", ["multi"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="layer3",
                            metadata={"original": quest},
                            created_at=quest.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("Layer3Adapter fetch failed: %s", e)
            return []
