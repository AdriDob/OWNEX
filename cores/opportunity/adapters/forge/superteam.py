"""Superteam adapter — discover Solana/web3 dev bounties."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.superteam")

API_BASE = "https://earn.superteam.fun/api"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch active bounties from Superteam Earn."""
    try:
        creds = get_platform_credentials("superteam")
        headers = {}
        if creds.get("api_key"):
            headers["Authorization"] = f"Bearer {creds['api_key']}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                f"{API_BASE}/listings",
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"Superteam API returned {resp.status_code}")
                return []

            data = resp.json()
            bounties = data if isinstance(data, list) else data.get("data", data.get("listings", []))

            results = []
            for bounty in bounties[:20]:
                if str(bounty.get("status", "")).upper() != "OPEN":
                    continue
                slug = bounty.get("slug") or bounty.get("id", "")
                results.append(
                    {
                        "id": f"superteam_{bounty.get('id', bounty.get('slug'))}",
                        "name": bounty.get("title") or bounty.get("name", "Superteam Bounty"),
                        "description": bounty.get("description") or "",
                        "platform": "superteam",
                        "url": f"https://earn.superteam.fun/listings/{slug}" if slug else "",
                        "reward": float(bounty.get("rewardAmount", bounty.get("maxRewardAsk", 0)) or 0),
                        "effort_hours": float(bounty.get("estimatedHours", 8)),
                        "tags": bounty.get("skills", ["web3", "solana"]),
                        "cycle": "forge",
                        "source_type": "dev_bounty",
                        "source_name": "superteam",
                        "metadata": {"original": bounty},
                        "created_at": bounty.get("createdAt", bounty.get("deadline", "")),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Superteam fetch failed: {e}")
        return []
