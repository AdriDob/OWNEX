"""
OpenAlex client — keyless, scholarly works API.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from cores.intelligence import (
    IntelligenceFeed,
    IntelligenceItem,
    IntelligenceSource,
    IntelligenceType,
)

LOG = logging.getLogger("ownex.intelligence.openalex")


class OpenAlexFeed(IntelligenceFeed):
    """OpenAlex client — keyless, scholarly works API."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 86400):
        self._cache_dir = os.path.join(os.getcwd(), "data", "intelligence", "openalex")
        self._ttl = 86400
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, "openalex_cache.json")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._fetched_at: datetime | None = None

    @property
    def source(self) -> IntelligenceSource:
        return IntelligenceSource.OPENALEX

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.PAPER

    @property
    def cache_ttl_seconds(self) -> int:
        return 86400  # 24h

    @property
    def rate_limit_per_minute(self) -> int:
        return 60

    async def fetch_items(self, since: datetime | None = None, **kwargs) -> list:
        """Fetch recent works from OpenAlex."""
        params = {
            "per-page": 100,
            "sort": "publication_date:desc",
            "filter": "type:article",
        }
        if since:
            params["filter"] = f"from_publication_date:{since.strftime('%Y-%m-%d')}"

        try:
            resp = await self._client.get(
                "https://api.openalex.org/works",
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            works = data.get("results", [])
        except Exception as exc:
            LOG.warning("OpenAlex fetch failed: %s", exc)
            return []

        items = []
        for work in works:
            doi = work.get("doi", "")
            title = work.get("title", "")
            # OpenAlex has no plain "abstract" field: it ships an inverted
            # index {word: [positions]}. Reconstruct readable text (first ~80
            # words) instead of str()-ing a dict (fixed 2026-09-12).
            abstract = self._abstract_from_index(work.get("abstract_inverted_index"))
            publication_date = work.get("publication_date", "")

            item = IntelligenceItem(
                source=IntelligenceSource.OPENALEX,
                intelligence_type=IntelligenceType.PAPER,
                external_id=f"openalex:{doi or work.get('id', '')}",
                title=title[:200],
                summary=(abstract or "")[:500],
                url=f"https://openalex.org/works/{work.get('id', '').split('/')[-1]}",
                published_at=self._parse_date(publication_date),
                fetched_at=datetime.now(UTC),
                tags=("openalex", "paper", "scholarly"),
                confidence=0.85,
            )
            items.append(item)
        return items

    async def health_check(self) -> dict[str, Any]:
        try:
            start = datetime.now(UTC)
            resp = await self._client.get(
                "https://api.openalex.org/works",
                params={"per-page": 1},
                timeout=10.0,
            )
            latency = (datetime.now(UTC) - start).total_seconds() * 1000
            if resp.status_code == 200:
                return {"status": "healthy", "latency_ms": latency, "last_fetch": datetime.now(UTC).isoformat()}
            return {"status": "degraded", "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"status": "down", "error": str(exc)}

    @staticmethod
    def _abstract_from_index(index: Any, max_words: int = 80) -> str:
        """Rebuild readable text from OpenAlex's inverted index {word: [pos]}."""
        if not isinstance(index, dict) or not index:
            return ""
        try:
            ordered = sorted(((pos, word) for word, positions in index.items() for pos in positions))
            return " ".join(word for _, word in ordered[:max_words])
        except Exception:
            return ""

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None


__all__ = ["OpenAlexFeed"]
