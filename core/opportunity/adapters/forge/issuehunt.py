"""IssueHunt adapter — discover bounty issues on GitHub."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.issuehunt")

API_BASE = "https://issuehunt.io/api"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch active funded issues from IssueHunt."""
    try:
        creds = get_platform_credentials("issuehunt")
        headers = {}
        if creds.get("api_key"):
            headers["Authorization"] = f"Bearer {creds['api_key']}"

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/issues",
                headers=headers,
                params={"status": "open", "limit": 20, "sort": "reward", "order": "desc"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"IssueHunt API returned {resp.status_code}")
                return []

            data = resp.json()
            issues = data.get("issues", data.get("data", []))

            results = []
            for issue in issues[:20]:
                results.append(
                    {
                        "id": f"issuehunt_{issue.get('id', issue.get('number'))}",
                        "name": issue.get("title", "IssueHunt Issue"),
                        "description": issue.get("body", issue.get("description", "")),
                        "platform": "issuehunt",
                        "url": issue.get("url", issue.get("htmlUrl", "")),
                        "reward": float(issue.get("reward", issue.get("amount", 0))),
                        "effort_hours": float(issue.get("estimatedHours", 4)),
                        "tags": issue.get("labels", ["bounty", "github"]),
                        "cycle": "forge",
                        "source_type": "dev_bounty",
                        "source_name": "issuehunt",
                        "metadata": {"original": issue},
                        "created_at": issue.get("created_at", issue.get("createdAt", "")),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"IssueHunt fetch failed: {e}")
        return []
