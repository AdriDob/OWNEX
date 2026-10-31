"""Tenstorrent adapter — Hardware/ML dev bounty platform (Forge cycle).

Source: https://tenstorrent.com
Payout: $500–$10,000/bounty
Token: Crypto
Vetting: GitHub PR
Recurrencia: ⚠️ 5% merge. 2-8 semanas.
Volumen: Hardware/ML. Pago lento.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_api_key, get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class TenstorrentAdapter(OpportunityAdapter):
    """Tenstorrent adapter — Hardware/ML dev bounty platform (Forge cycle)."""

    platform: str = "tenstorrent"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("tenstorrent", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch hardware/ML bounties from Tenstorrent."""
        try:
            headers = get_auth_headers("tenstorrent", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.tenstorrent.com/v1/bounties",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                bounties = data.get("bounties", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for bounty in bounties[:10]:  # Limited due to niche
                    raw_opps.append(
                        RawOpportunity(
                            id=f"tenstorrent_{bounty.get('id')}",
                            name=bounty.get("title") or "Tenstorrent Bounty",
                            description=bounty.get("description") or "",
                            platform="tenstorrent",
                            url=bounty.get("url"),
                            reward=float(bounty.get("reward", 0)),
                            effort_hours=float(bounty.get("estimated_hours", 20)),
                            tags=bounty.get("tags", ["hardware", "ml"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="tenstorrent",
                            metadata={"original": bounty},
                            created_at=bounty.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("TenstorrentAdapter fetch failed: %s", e)
            return []
