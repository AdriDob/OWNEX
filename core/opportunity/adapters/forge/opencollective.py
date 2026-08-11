"""OpenCollective adapter — discover grants and collectives."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.opencollective")

API_BASE = "https://api.opencollective.com/v3"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch grant/collective opportunities from OpenCollective."""
    try:
        creds = get_platform_credentials("opencollective")
        headers = {}
        if creds.get("api_key"):
            headers["Api-Key"] = creds["api_key"]
            headers["Personal-Token"] = creds["api_key"]

        async with httpx.AsyncClient() as client:
            # Discover collectives with active budgets
            resp = await client.get(
                f"{API_BASE}/collectives",
                headers=headers,
                params={"limit": 20, "type": "COLLECTIVE", "status": "ACTIVE"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"OpenCollective API returned {resp.status_code}")
                return []

            data = resp.json()
            collectives = data if isinstance(data, list) else data.get("collectives", data.get("data", []))

            results = []
            for collective in collectives[:20]:
                results.append(
                    {
                        "id": f"opencollective_{collective.get('id', collective.get('slug'))}",
                        "name": collective.get("name") or collective.get("slug", ""),
                        "description": collective.get("description") or collective.get("longDescription", ""),
                        "platform": "opencollective",
                        "url": collective.get("website") or f"https://opencollective.com/{collective.get('slug', '')}",
                        "reward": 0.0,
                        "effort_hours": 0.0,
                        "tags": collective.get("tags", ["opensource", "collective"]),
                        "cycle": "forge",
                        "source_type": "grant",
                        "source_name": "opencollective",
                        "metadata": {"original": collective},
                        "created_at": collective.get("createdAt", ""),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"OpenCollective fetch failed: {e}")
        return []
