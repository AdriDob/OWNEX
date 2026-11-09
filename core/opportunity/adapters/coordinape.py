"""Coordinape adapter — DAO peer-to-peer compensation (Forge cycle).

Source: https://coordinape.com
Payout: Variable (tokens)
Token: Multi-chain
Vetting: DAO membership
Recurrencia: ✅ Alta
Volumen: Peer-to-peer compensation. Attestation.
Estado: ✅ ACTIVO
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import get_auth_headers, load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class CoordinapeAdapter(OpportunityAdapter):
    """Coordinape adapter — DAO peer-to-peer compensation (Forge cycle)."""

    platform: str = "coordinape"
    cycle: str = "forge"

    def __init__(self, config: dict | None = None):
        merged_config = load_credentials("coordinape", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch peer-to-peer compensation from Coordinape."""
        try:
            headers = get_auth_headers("coordinape", self.config)
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.coordinape.com/v1/attestations",
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                attestations = data.get("attestations", data.get("data", []))

                raw_opps: list[RawOpportunity] = []
                for att in attestations[:25]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"coordinape_{att.get('id')}",
                            name=att.get("name") or "Coordinape Attestation",
                            description=att.get("description") or "",
                            platform="coordinape",
                            url=att.get("url"),
                            reward=float(att.get("amount", 0)),
                            effort_hours=float(att.get("estimated_hours", 4)),
                            tags=att.get("tokens", ["multi"]),
                            cycle="forge",
                            source_type="dev_bounty",
                            source_name="coordinape",
                            metadata={"original": att},
                            created_at=att.get("created_at") or "",
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.adapters").warning("CoordinapeAdapter fetch failed: %s", e)
            return []
