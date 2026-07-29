"""GitHub Sponsors adapter — discover sponsored OSS opportunities."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.github_sponsors")

API_BASE = "https://api.github.com"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch trending/featured sponsored OSS repos via GitHub API."""
    try:
        creds = get_platform_credentials("github")
        headers = {"Accept": "application/vnd.github.v3+json"}
        if creds.get("token"):
            headers["Authorization"] = f"Bearer {creds['token']}"

        async with httpx.AsyncClient() as client:
            # Search for repos with funding links
            resp = await client.get(
                f"{API_BASE}/search/repositories",
                headers=headers,
                params={"q": "sponsor:true OR github-sponsors:true", "sort": "stars", "per_page": 20, "order": "desc"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"GitHub API returned {resp.status_code}")
                return []

            data = resp.json()
            repos = data.get("items", [])

            results = []
            for repo in repos[:20]:
                results.append(
                    {
                        "id": f"github_sponsor_{repo.get('id')}",
                        "name": repo.get("full_name", repo.get("name", "OSS Repo")),
                        "description": repo.get("description") or "",
                        "platform": "github_sponsors",
                        "url": repo.get("html_url", ""),
                        "reward": 0.0,
                        "effort_hours": 0.0,
                        "tags": repo.get("topics", ["open-source", "sponsor"]),
                        "cycle": "forge",
                        "source_type": "oss_sponsor",
                        "source_name": "github_sponsors",
                        "metadata": {"original": repo},
                        "created_at": repo.get("created_at", ""),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"GitHub Sponsors fetch failed: {e}")
        return []
