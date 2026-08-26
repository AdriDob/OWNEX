"""Sherlock Adapter — Security Work Cycle.

Web3 audit contest platform. Public REST API at audits.sherlock.xyz
(no auth required for listing contests).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from core.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.sherlock")

SHERLOCK_API = "https://audits.sherlock.xyz/api/contests"
_FINISHED_STATUSES = {"FINISHED"}


def _parse_reward(contest: dict[str, Any]) -> float:
    """Prefer prize_pool (guaranteed), fall back to rewards (pool + bonuses)."""
    for key in ("prize_pool", "rewards"):
        value = contest.get(key)
        if value is None:
            continue
        try:
            amount = float(value)
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount
    return 0.0


class SherlockAdapter(OpportunityAdapter):
    """Adapter for Sherlock web3 audit contests.

    Fetches the public contests listing; includes every contest whose
    end date is in the future (live, judging, upcoming) so downstream
    scoring can prioritize by deadline.
    """

    platform: str = "sherlock"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._base_url = self.config.get("api_url") or SHERLOCK_API

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        raw_opps: list[RawOpportunity] = []
        now = time.time()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self._base_url, params={"page": "1"})
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:
            logger.warning("[Sherlock] fetch error: %s", exc)
            return []

        contests = payload.get("items", []) if isinstance(payload, dict) else []
        for contest in contests:
            if not isinstance(contest, dict):
                continue
            status = str(contest.get("status", ""))
            if status.upper() in _FINISHED_STATUSES:
                continue
            ends_at = contest.get("ends_at")
            try:
                if ends_at is not None and float(ends_at) < now:
                    continue
            except (TypeError, ValueError):
                pass

            contest_id = contest.get("id")
            title = contest.get("title", "")
            reward = _parse_reward(contest)
            token = contest.get("token", "USDC")
            url = f"https://audits.sherlock.xyz/contests/{contest_id}" if contest_id else None

            raw_opps.append(
                RawOpportunity(
                    id=f"sherlock_{contest_id}",
                    name=title,
                    description=contest.get("short_description", "") or f"Sherlock audit contest: {title}",
                    platform="sherlock",
                    url=url,
                    reward=reward,
                    effort_hours=10.0,
                    tags=["web3", "smart-contracts", "audit-contest"],
                    cycle="security",
                    source_type="platform",
                    source_name="sherlock",
                    metadata={
                        "original": {
                            "status": status,
                            "type": contest.get("type_label"),
                            "token": token,
                            "prize_pool": contest.get("prize_pool"),
                            "rewards": contest.get("rewards"),
                            "starts_at": contest.get("starts_at"),
                            "ends_at": contest.get("ends_at"),
                        },
                        "personal": personal,
                    },
                )
            )

        logger.info("[Sherlock] %d contests fetched", len(raw_opps))
        return raw_opps
