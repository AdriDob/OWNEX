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

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/bounties",
                headers=headers,
                params={"limit": 20, "status": "open"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"Superteam API returned {resp.status_code}")
                return []

            data = resp.json()
            bounties = data.get("bounties", data.get("data", []))

            results = []
            for bounty in bounties[:20]:
                results.append(
                    {
                        "id": f"superteam_{bounty.get('id', bounty.get('slug'))}",
                        "name": bounty.get("title") or bounty.get("name", "Superteam Bounty"),
                        "description": bounty.get("description") or "",
                        "platform": "superteam",
                        "url": bounty.get("url") or bounty.get("applyUrl", ""),
                        "reward": float(bounty.get("rewardUsd", bounty.get("reward", 0))),
                        "effort_hours": float(bounty.get("estimatedHours", 8)),
                        "tags": bounty.get("tags", bounty.get("skills", ["web3", "solana"])),
                        "cycle": "forge",
                        "source_type": "dev_bounty",
                        "source_name": "superteam",
                        "metadata": {"original": bounty},
                        "created_at": bounty.get("createdAt", bounty.get("publishedAt", "")),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Superteam fetch failed: {e}")
        return []
