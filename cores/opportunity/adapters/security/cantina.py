"""Cantina Adapter — Security Work Cycle (Web3 audit competitions).

Public REST API at cantina.xyz — no auth required for the competitions
listing. Returns live/judging/upcoming competitions with real prize pools.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from cores.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.cantina")

CANTINA_API = "https://cantina.xyz/api/v0/competitions"
_FINISHED_STATUSES = {"complete", "completed", "cancelled", "canceled", "archived", "ended"}


class CantinaAdapter(OpportunityAdapter):
    """Adapter for Cantina (cantina.xyz) audit competitions.

    Public API, no credentials needed. Filters out finished competitions
    and those whose timeframe already ended.
    """

    platform: str = "cantina"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._base_url = self.config.get("api_url") or CANTINA_API

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        raw_opps: list[RawOpportunity] = []
        now = datetime.now(UTC)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(self._base_url, headers={"Accept": "application/json"})
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:
            logger.warning("[Cantina] fetch error: %s", exc)
            return []

        competitions = payload if isinstance(payload, list) else payload.get("items", [])
        for comp in competitions:
            if not isinstance(comp, dict):
                continue
            status = str(comp.get("status", "")).lower()
            if status in _FINISHED_STATUSES:
                continue

            timeframe = comp.get("timeframe") or {}
            end_raw = timeframe.get("end") or ""
            try:
                end_dt = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00"))
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=UTC)
                if end_dt < now:
                    continue
            except (TypeError, ValueError):
                pass

            comp_id = comp.get("id", "")
            name = comp.get("name", "")
            company = (comp.get("company") or {}).get("name", "")
            pot = comp.get("totalRewardPot")
            try:
                reward = float(pot) if pot not in (None, "") else 0.0
            except (TypeError, ValueError):
                reward = 0.0
            currency = comp.get("currencyCode", "USDC")

            tags = ["web3", "smart-contracts", "audit-contest"]
            if company:
                tags.append(str(company).lower().replace(" ", "-"))

            raw_opps.append(
                RawOpportunity(
                    id=f"cantina_{comp_id}",
                    name=name,
                    description=comp.get("instructions", "")[:500] or f"Cantina audit competition: {name}",
                    platform="cantina",
                    url=comp.get("url") or f"https://cantina.xyz/competitions/{comp_id}",
                    reward=reward,
                    effort_hours=16.0,
                    tags=tags,
                    cycle="security",
                    source_type="platform",
                    source_name="cantina",
                    metadata={
                        "original": {
                            "status": status,
                            "company": company,
                            "currency": currency,
                            "total_reward_pot": pot,
                            "timeframe": timeframe,
                        },
                        "personal": personal,
                    },
                )
            )

        logger.info("[Cantina] %d competitions fetched", len(raw_opps))
        return raw_opps
