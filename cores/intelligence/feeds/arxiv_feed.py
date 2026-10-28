"""
arXiv client — keyless, scientific papers from arXiv.org.
"""

from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

import httpx

from cores.intelligence import (
    IntelligenceFeed,
    IntelligenceItem,
    IntelligenceSource,
    IntelligenceType,
)

LOG = logging.getLogger("ownex.intelligence.arxiv")


class ArxivFeed(IntelligenceFeed):
    """arXiv client — keyless, scientific papers from arXiv.org."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 86400):
        self._cache_dir = os.path.join(os.getcwd(), "data", "intelligence", "arxiv")
        self._ttl = 86400
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, "arxiv_cache.json")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._fetched_at: datetime | None = None

        # arXiv categories we're interested in
        self.categories = [
            "cs.CR",  # Cryptography and Security
            "cs.AI",  # Artificial Intelligence
            "cs.CL",  # Computation and Language
            "cs.LG",  # Machine Learning
        ]

    @property
    def source(self) -> IntelligenceSource:
        return IntelligenceSource.ARXIV

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.PAPER

    @property
    def cache_ttl_seconds(self) -> int:
        return 86400  # 24h

    @property
    def rate_limit_per_minute(self) -> int:
        return 30  # arXiv allows 1 request per 3 seconds = 20/min, be respectful

    async def fetch_items(self, since: datetime | None = None, **kwargs) -> list:
        """Fetch recent papers from arXiv for our categories."""
        items = []
        for category in self.categories:
            try:
                params = {
                    "search_query": f"cat:{category}",
                    "start": 0,
                    "max_results": 50,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                }

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.get(
                        "http://export.arxiv.org/api/query",
                        params=params,
                        timeout=30.0,
                    )
                    resp.raise_for_status()
                    entries = self._parse_atom(resp.text)

                    for entry in entries:
                        published = self._parse_date(entry.get("published"))

                        # Check if we should include based on since
                        if since and published and published < since:
                            continue

                        raw_id = entry.get("id", "")
                        item = IntelligenceItem(
                            source=IntelligenceSource.ARXIV,
                            intelligence_type=IntelligenceType.PAPER,
                            external_id=f"arxiv:{raw_id.split('/')[-1]}",
                            title=" ".join(entry.get("title", "").split()),
                            summary=" ".join(entry.get("summary", "").split())[:500],
                            url=entry.get("link", ""),
                            published_at=self._parse_date(entry.get("published")),
                            fetched_at=datetime.now(UTC),
                            tags=("arxiv", "paper", category),
                            confidence=0.9,
                        )
                        items.append(item)
            except Exception as exc:
                LOG.warning("arXiv fetch failed for %s: %s", category, exc)
                continue

        return items

    async def health_check(self) -> dict[str, Any]:
        try:
            start = datetime.now(UTC)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "http://export.arxiv.org/api/query",
                    params={"search_query": "cat:cs.CR", "max_results": 1},
                    timeout=10.0,
                )
                latency = (datetime.now(UTC) - start).total_seconds() * 1000
                if resp.status_code == 200:
                    return {"status": "healthy", "latency_ms": latency, "last_fetch": datetime.now(UTC).isoformat()}
                return {"status": "degraded", "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"status": "down", "error": str(exc)}

    @staticmethod
    def _parse_atom(xml_text: str) -> list[dict[str, str]]:
        """Parse arXiv Atom XML with stdlib (no feedparser dependency)."""
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []
        entries: list[dict[str, str]] = []
        for node in root.findall("atom:entry", ns):
            link = ""
            for link_node in node.findall("atom:link", ns):
                if link_node.get("rel", "alternate") == "alternate" or not link:
                    link = link_node.get("href", "") or link
            entries.append(
                {
                    "id": (node.findtext("atom:id", default="", namespaces=ns) or ""),
                    "title": (node.findtext("atom:title", default="", namespaces=ns) or ""),
                    "summary": (node.findtext("atom:summary", default="", namespaces=ns) or ""),
                    "published": (node.findtext("atom:published", default="", namespaces=ns) or ""),
                    "link": link,
                }
            )
        return entries

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            # arXiv uses format like "2024-01-15T12:34:56Z"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None


__all__ = ["ArxivFeed"]
