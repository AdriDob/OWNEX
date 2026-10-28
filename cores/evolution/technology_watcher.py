"""Technology Watcher — Monitor open-source ecosystem for relevant technologies."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("ownex.evolution.watcher")


class TechnologyWatcher:
    SOURCES = {
        "github_trending": "https://api.github.com/search/repositories?q=python+self-healing+monitoring&sort=stars&order=desc",
        "pypi_new": "https://pypi.org/simple/",
    }

    async def scan(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                for name, url in self.SOURCES.items():
                    try:
                        resp = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
                        if resp.status_code == 200:
                            data = resp.json()
                            for item in data.get("items", [])[:5]:
                                results.append(
                                    self._tool(
                                        item.get("full_name", "unknown"),
                                        item.get("description", ""),
                                        item.get("html_url", ""),
                                        item.get("stargazers_count", 0),
                                    )
                                )
                    except Exception as e:
                        logger.debug("Failed to fetch %s: %s", name, e)
        except Exception:
            pass
        return results

    def _tool(self, name: str, description: str, url: str, stars: int) -> dict[str, Any]:
        return {
            "name": name,
            "description": description,
            "url": url,
            "stars": stars,
            "evaluation": self._evaluate(name, description),
        }

    def _evaluate(self, name: str, description: str) -> dict[str, Any]:
        keywords = ["monitoring", "self-heal", "auto-fix", "observability", "lint"]
        score = sum(1 for kw in keywords if kw.lower() in description.lower())
        return {
            "score": score,
            "compatible": score >= 1,
            "recommendation": "review" if score >= 1 else "skip",
        }
