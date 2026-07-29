"""Opire adapter — discover OSS issue bounties."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.opire")

API_BASE = "https://api.opire.com/v1"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch active bounties from Opire."""
    try:
        creds = get_platform_credentials("opire")
        headers = {}
        if creds.get("api_key"):
            headers["Authorization"] = f"Bearer {creds['api_key']}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/bounties",
                headers=headers,
                params={"status": "open", "limit": 20},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"Opire API returned {resp.status_code}")
                return []

            data = resp.json()
            bounties = data.get("bounties", data.get("data", []))

            results = []
            for bounty in bounties[:20]:
                results.append(
                    {
                        "id": f"opire_{bounty.get('id')}",
                        "name": bounty.get("title", "Opire Bounty"),
                        "description": bounty.get("description", ""),
                        "platform": "opire",
                        "url": bounty.get("url", ""),
                        "reward": float(bounty.get("amount", bounty.get("reward", 0))),
                        "effort_hours": float(bounty.get("estimatedHours", 6)),
                        "tags": bounty.get("labels", ["oss", "bounty"]),
                        "cycle": "forge",
                        "source_type": "dev_bounty",
                        "source_name": "opire",
                        "metadata": {"original": bounty},
                        "created_at": bounty.get("created_at", ""),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Opire fetch failed: {e}")
        return []
