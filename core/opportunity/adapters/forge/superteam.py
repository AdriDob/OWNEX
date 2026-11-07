"""Superteam adapter — discover Solana/web3 dev bounties."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
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
            bounties = data if isinstance(data, list) else data.get("bounties", data.get("data", []))

            results = []
            now = datetime.now(UTC)
            for bounty in bounties[:50]:
                if not isinstance(bounty, dict):
                    continue
                status = str(bounty.get("status") or "").upper()
                if status in ("CLOSED", "EXPIRED", "COMPLETED", "FILLED"):
                    continue
                btype = str(bounty.get("type") or "").lower()
                if btype and btype != "bounty":
                    continue
                # Skip expired listings
                deadline = bounty.get("deadline")
                if deadline:
                    try:
                        dl = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
                        if dl.tzinfo is None:
                            dl = dl.replace(tzinfo=UTC)
                        if dl < now:
                            continue
                    except (TypeError, ValueError):
                        pass
                reward = bounty.get("rewardAmount") or bounty.get("rewardUsd") or bounty.get("reward") or 0
                try:
                    reward = float(reward)
                except (TypeError, ValueError):
                    reward = 0.0
                slug = bounty.get("slug") or bounty.get("id", "")
                oid = bounty.get("id") or slug
                results.append(
                    {
                        "id": f"superteam_{oid}",
                        "name": bounty.get("title") or bounty.get("name", "Superteam Bounty"),
                        "description": bounty.get("description") or bounty.get("summary") or "",
                        "platform": "superteam",
                        "url": bounty.get("url") or bounty.get("applyUrl") or f"https://earn.superteam.fun/listings/{slug or oid}",
                        "reward": reward,
                        "effort_hours": float(bounty.get("estimatedHours") or 8),
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
