"""OnlyDust adapter — open-source contribution funding (Starknet ecosystem).

OnlyDust's public API lives at api.onlydust.com. It was returning Cloudflare
530 (origin DNS error) at implementation time — the adapter degrades
gracefully to an empty list and will pick up automatically when the API
recovers. No credentials required for public project listings.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("ownex.adapters.forge.onlydust")

API_BASE = "https://api.onlydust.com/v1"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch funded open-source projects/bounties from OnlyDust."""
    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{API_BASE}/projects",
                params={"limit": 20},
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                logger.warning("OnlyDust API returned %s (infra may be down)", resp.status_code)
                return []
            data = resp.json()
    except Exception as exc:
        logger.warning("OnlyDust fetch failed: %s", exc)
        return []

    projects = data.get("projects", data.get("data", [])) if isinstance(data, dict) else data
    for proj in projects[:20]:
        if not isinstance(proj, dict):
            continue
        proj_id = proj.get("id", "")
        name = proj.get("name") or proj.get("title") or "OnlyDust project"
        reward = 0.0
        for key in ("reward", "amount", "bounty", "funding"):
            try:
                reward = max(reward, float(proj.get(key) or 0))
            except (TypeError, ValueError):
                continue
        results.append(
            {
                "id": f"onlydust_{proj_id}",
                "name": name,
                "description": (proj.get("description") or proj.get("summary") or "")[:1000],
                "platform": "onlydust",
                "url": proj.get("url") or proj.get("link") or f"https://www.onlydust.com/projects/{proj_id}",
                "reward": reward,
                "effort_hours": 8.0,
                "tags": ["open-source", "starknet", "funding"] + (proj.get("tags") or [])[:4],
                "cycle": "forge",
                "source_type": "open_source",
                "source_name": "onlydust",
                "metadata": {"original": proj},
                "created_at": proj.get("created_at", ""),
            }
        )

    logger.info("OnlyDust: %d opportunities", len(results))
    return results
