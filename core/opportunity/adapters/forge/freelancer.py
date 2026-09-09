"""Freelancer adapter — discover freelance dev projects."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from core.credentials.vault import get_platform_credentials

logger = logging.getLogger("ownex.adapters.forge.freelancer")

API_BASE = "https://www.freelancer.com/api/projects/0.1"


async def fetch_opportunities() -> list[dict[str, Any]]:
    """Fetch active software dev projects from Freelancer."""
    try:
        creds = get_platform_credentials("freelancer")
        headers = {"Content-Type": "application/json"}
        if creds.get("api_key"):
            headers["Freelancer-OAuth-Access-Token"] = creds["api_key"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{API_BASE}/projects/active",
                headers=headers,
                params={
                    "limit": 20,
                    "job_names[]": ["Software Development", "Web Development", "Python", "JavaScript"],
                    "sort": "bid_count",
                    "order": "asc",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning(f"Freelancer API returned {resp.status_code}")
                return []

            data = resp.json()
            projects = data.get("result", data.get("projects", []))

            results = []
            for project in projects[:20]:
                results.append(
                    {
                        "id": f"freelancer_{project.get('id')}",
                        "name": project.get("title", "Freelancer Project"),
                        "description": project.get("description", project.get("preview_description", "")),
                        "platform": "freelancer",
                        "url": project.get("url", f"https://www.freelancer.com/projects/{project.get('id')}"),
                        "reward": float(project.get("budget", {}).get("maximum", project.get("budget", 0))),
                        "effort_hours": float(project.get("estimated_delivery_time", 0)) * 8,
                        "tags": project.get("jobs", []),
                        "cycle": "forge",
                        "source_type": "freelance",
                        "source_name": "freelancer",
                        "metadata": {"original": project},
                        "created_at": project.get("time_created", project.get("createdAt", "")),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"Freelancer fetch failed: {e}")
        return []
