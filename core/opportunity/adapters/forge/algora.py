"""Algora adapter — discover open-source bounties on GitHub issues."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.algora")

API_BASE = "https://api.algora.xyz/v1"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch active bounties from Algora."""
    try:
        creds = get_platform_credentials("algora")
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
                logger.warning(f"Algora API returned {resp.status_code}")
                return []

            data = resp.json()
            bounties = data.get("bounties", data.get("data", []))

            results = []
            for bounty in bounties[:20]:
                results.append(
                    {
                        "id": f"algora_{bounty.get('id', bounty.get('number'))}",
                        "name": bounty.get("title") or "Algora Bounty",
                        "description": bounty.get("description") or bounty.get("body", ""),
                        "platform": "algora",
                        "url": bounty.get("url") or bounty.get("html_url", ""),
                        "reward": float(bounty.get("amount", bounty.get("reward", 0))),
                        "effort_hours": float(bounty.get("estimated_hours", 5)),
                        "tags": bounty.get("labels", bounty.get("tags", ["oss", "github"])),
                        "cycle": "forge",
                        "source_type": "dev_bounty",
                        "source_name": "algora",
                        "metadata": {"original": bounty},
                        "created_at": bounty.get("created_at", ""),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Algora fetch failed: {e}")
        return []
