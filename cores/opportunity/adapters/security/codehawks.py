"""CodeHawks Adapter — Security Work Cycle (Cyfrin competitive audits).

www.codehawks.com exposes a JSON API that requires an API key
("No API Key" 400 response without one). The adapter reads credentials
from the vault (platform keys: ``codehawks`` / ``cyfrin``) and degrades
to an empty list when no valid key is configured — it never fabricates
contests.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from cores.credentials.vault import get_platform_credentials
from cores.opportunity.adapters import OpportunityAdapter, RawOpportunity

logger = logging.getLogger("ownex.adapters.security.codehawks")

CODEHAWKS_API = "https://www.codehawks.com/api/contests"


def _api_key() -> str | None:
    for platform in ("codehawks", "cyfrin"):
        creds = get_platform_credentials(platform)
        key = creds.get("api_key") or creds.get("token")
        if key and not any(bad in str(key).lower() for bad in ("test", "your_", "placeholder", "xxx")):
            return str(key)
    env_key = os.environ.get("CODEHAWKS_API_KEY", "")
    return env_key or None


class CodeHawksAdapter(OpportunityAdapter):
    """Adapter for Cyfrin CodeHawks audit competitions.

    Requires a CodeHawks API key; returns [] (with a warning) when the
    key is missing or rejected so discovery stays honest.
    """

    platform: str = "codehawks"
    cycle: str = "security"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self._base_url = self.config.get("api_url") or CODEHAWKS_API

    async def fetch_opportunities(self, personal: Any | None = None) -> list[RawOpportunity]:
        api_key = _api_key()
        if not api_key:
            logger.info("[CodeHawks] no API key configured — skipping")
            return []

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    self._base_url,
                    params={"apiKey": api_key},
                    headers={"Accept": "application/json", "X-API-Key": api_key},
                )
                if resp.status_code != 200:
                    logger.warning("[CodeHawks] API returned %s", resp.status_code)
                    return []
                payload = resp.json()
        except Exception as exc:
            logger.warning("[CodeHawks] fetch error: %s", exc)
            return []

        contests = payload if isinstance(payload, list) else payload.get("contests", payload.get("data", []))
        raw_opps: list[RawOpportunity] = []
        for contest in contests:
            if not isinstance(contest, dict):
                continue
            status = str(contest.get("status", "")).lower()
            if status in {"finished", "ended", "complete", "judging", "archived"}:
                continue
            contest_id = contest.get("id") or contest.get("slug") or contest.get("name", "")
            prize = contest.get("prize_pool") or contest.get("reward") or contest.get("total_reward") or 0
            try:
                reward = float(prize)
            except (TypeError, ValueError):
                reward = 0.0
            raw_opps.append(
                RawOpportunity(
                    id=f"codehawks_{contest_id}",
                    name=contest.get("name") or contest.get("title") or f"CodeHawks {contest_id}",
                    description=str(contest.get("description") or "")[:500],
                    platform="codehawks",
                    url=contest.get("url") or f"https://www.codehawks.com/contests/{contest_id}",
                    reward=reward,
                    effort_hours=24.0,
                    tags=["web3", "smart-contracts", "audit-contest", "codehawks"],
                    cycle="security",
                    source_type="platform",
                    source_name="codehawks",
                    metadata={"original": {"status": status, "contest": contest}},
                )
            )

        logger.info("[CodeHawks] %d contests fetched", len(raw_opps))
        return raw_opps
