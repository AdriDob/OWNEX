"""Opire adapter — discover OSS issue bounties.

API pública verificada: GET https://api.opire.dev/rewards (sin auth).
Cada item es un reward sobre un GitHub issue; ``pendingPrice.value``
viene en centavos USD (``unit: "USD_CENT"``).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.opire")

API_BASE = "https://api.opire.dev"


def _reward_usd(item: dict[str, Any]) -> float:
    """Convert pendingPrice (USD_CENT) to dollars; 0 si ausente/inválido."""
    price = item.get("pendingPrice") or {}
    value = price.get("value")
    if value is None:
        return 0.0
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return 0.0


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch active bounties from Opire."""
    try:
        creds = get_platform_credentials("opire")
        headers: dict[str, str] = {}
        if creds.get("api_key"):
            headers["Authorization"] = f"Bearer {creds['api_key']}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                f"{API_BASE}/rewards",
                headers=headers,
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"Opire API returned {resp.status_code}")
                return []

            data = resp.json()
            rewards = data if isinstance(data, list) else data.get("data", [])

            results = []
            for reward in rewards[:20]:
                reward_id = reward.get("id", "")
                project = reward.get("project") or {}
                languages = [str(lang).lower() for lang in (reward.get("programmingLanguages") or []) if lang]
                results.append(
                    {
                        "id": f"opire_{reward_id}",
                        "name": reward.get("title", "Opire Bounty"),
                        "description": (
                            f"Opire reward on {project.get('name', 'GitHub issue')}: {reward.get('title', '')}"
                        ),
                        "platform": "opire",
                        "url": reward.get("url", ""),
                        "reward": _reward_usd(reward),
                        "effort_hours": float(reward.get("estimatedHours", 6)),
                        "tags": ["oss", "bounty", *languages],
                        "cycle": "forge",
                        "source_type": "dev_bounty",
                        "source_name": "opire",
                        "metadata": {"original": reward},
                        "created_at": str(reward.get("createdAt", "")),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Opire fetch failed: {e}")
        return []
