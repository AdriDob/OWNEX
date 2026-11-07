"""GitHub Bounties adapter — discover funded bounties across platforms.

Uses the public GitHub Search API (no auth required at low rate) to find
open issues carrying bounty markers: Algora `/bounty` commands, Polar.sh
funding links, and IssueHunt references. This aggregates bounty volume
that platform-specific APIs miss.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.github_bounties")

SEARCH_API = "https://api.github.com/search/issues"
_QUERIES = [
    ('"/bounty" in:comments state:open', "algora"),
    ("polar.sh bounty state:open", "polar"),
    ("issuehunt state:open", "issuehunt"),
]
_AMOUNT_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)")


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "OWNEX-bounty-discovery/1.0",
    }
    creds = get_platform_credentials("github")
    token = creds.get("api_key") or creds.get("token") or os.environ.get("GITHUB_TOKEN", "")
    # Vault may hold placeholder/test tokens — only send plausible real ones
    if token and not any(bad in token.lower() for bad in ("test", "your_", "placeholder", "xxx")):
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch open GitHub issues that reference a bounty platform."""
    results: list[dict[str, Any]] = []
    try:
        headers = _github_headers()
        async with httpx.AsyncClient() as client:
            for query, source in _QUERIES:
                try:
                    resp = await client.get(
                        SEARCH_API,
                        headers=headers,
                        params={"q": query, "sort": "updated", "order": "desc", "per_page": 15},
                        timeout=15,
                    )
                    if resp.status_code != 200:
                        logger.warning("GitHub search '%s' returned %s", query, resp.status_code)
                        continue
                    items = resp.json().get("items", [])
                except Exception as exc:
                    logger.warning("GitHub search failed for '%s': %s", query, exc)
                    continue

                for item in items:
                    title = item.get("title", "")
                    body = f"{item.get('body') or ''} {title}"
                    amounts = []
                    for a in _AMOUNT_RE.findall(body):
                        try:
                            amounts.append(float(a.replace(",", "")))
                        except ValueError:
                            continue
                    reward = max(amounts) if amounts else 0.0
                    labels = [lb.get("name", "") for lb in item.get("labels", []) if isinstance(lb, dict)]
                    results.append(
                        {
                            "id": f"gh_{source}_{item.get('id')}",
                            "name": title,
                            "description": (item.get("body") or "")[:1000],
                            "platform": source,
                            "url": item.get("html_url", ""),
                            "reward": reward,
                            "effort_hours": 4.0,
                            "tags": labels[:8] + ["github", "bounty"],
                            "cycle": "forge",
                            "source_type": "dev_bounty",
                            "source_name": f"github_{source}",
                            "metadata": {
                                "original": {
                                    "repo": (item.get("repository_url") or "").rsplit("/", 2)[-2:],
                                    "comments": item.get("comments", 0),
                                    "created_at": item.get("created_at", ""),
                                }
                            },
                            "created_at": item.get("created_at", ""),
                        }
                    )
    except Exception as exc:
        logger.error("GitHub bounties fetch failed: %s", exc)
        return []

    # Dedup by URL
    seen: set[str] = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    logger.info("GitHub bounties: %d opportunities", len(unique))
    return unique[:40]
