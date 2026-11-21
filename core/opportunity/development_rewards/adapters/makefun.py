"""make.fun Adapter — AI coding competitions with USDC rewards.

Platform: make.fun
Features: AI-agent-friendly, USDC rewards, sandbox verification,
public transcripts and repos as delivery evidence.
Argentina: Accepts participants, USDC payouts available
"""

from __future__ import annotations

from typing import Any

import httpx

from core.credentials.adapter_helpers import load_credentials
from core.opportunity.adapters import OpportunityAdapter, RawOpportunity


class MakefunAdapter(OpportunityAdapter):
    """make.fun adapter — AI coding competitions with USDC rewards."""

    platform: str = "make.fun"
    cycle: str = "forge"
    reward_currency: str = "USDC"

    def __init__(self, config: dict[str, Any] | None = None):
        merged_config = load_credentials("make.fun", config)
        super().__init__(merged_config)

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        """Fetch AI coding competitions from make.fun."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.make.fun/v1/competitions",
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                competitions = data.get("competitions", data)

                raw_opps: list[RawOpportunity] = []
                for comp in competitions[:20]:
                    raw_opps.append(
                        RawOpportunity(
                            id=f"makefun_{comp.get('id')}",
                            name=comp.get("title") or "make.fun Competition",
                            description=comp.get("description") or "",
                            platform="make.fun",
                            url=comp.get("url"),
                            reward=float(comp.get("reward", 0)),
                            effort_hours=float(comp.get("estimated_hours", 10)),
                            tags=comp.get("tags", ["ai", "coding", "competition"]),
                            specialization=comp.get("specialization", "backend"),
                            remote=comp.get("remote", True),
                            reward_currency=comp.get("currency", "USDC"),
                            reward_status=comp.get("status", "upcoming"),
                            source_type="competition",
                            source_name="make.fun",
                            metadata={"original": comp},
                        )
                    )

                return raw_opps
        except Exception as e:
            from logging import getLogger

            getLogger("ownex.opportunity.development_rewards").warning("MakefunAdapter fetch failed: %s", e)
            return []
