"""
GitHub Advisory Database client — keyless (via GitHub REST API).
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

LOG = logging.getLogger("ownex.intelligence.github_advisory")


class GitHubAdvisoryFeed(IntelligenceFeed):
    """GitHub Advisory Database feed — keyless (via GitHub REST API)."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 86400):
        self._cache_dir = os.path.join(os.getcwd(), "data", "intelligence", "github_advisory")
        self._ttl = 86400
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, "github_advisory_cache.json")
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Accept": "application/vnd.github+json"},
        )
        self._fetched_at: datetime | None = None

    @property
    def source(self) -> IntelligenceSource:
        return IntelligenceSource.GITHUB_ADVISORY

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.VULNERABILITY

    @property
    def cache_ttl_seconds(self) -> int:
        return 86400  # 24h

    @property
    def rate_limit_per_minute(self) -> int:
        return 60

    async def fetch_items(self, since: datetime | None = None, **kwargs) -> list[IntelligenceItem]:
        """Fetch GitHub Security Advisories as IntelligenceItems (contract).

        Fixed 2026-09-12: previously returned plain dicts, violating the
        IntelligenceFeed contract (consumers expect .source/.content_hash).
        """

        # Using GitHub REST API
        params = {"per_page": 100, "sort": "published", "direction": "desc"}
        if since:
            params["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            resp = await self._client.get(
                "https://api.github.com/advisories",
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            advisories = resp.json()
        except Exception as exc:
            LOG.warning("GitHub Advisory fetch failed: %s", exc)
            return []

        items = []
        for adv in advisories:
            severity = (adv.get("severity") or "").lower()
            ecosystem = adv.get("vulnerabilities", [{}])[0].get("package", {}).get("ecosystem", "")
            cve_id = next((i["value"] for i in adv.get("identifiers", []) if i.get("type") == "CVE"), "")

            item = IntelligenceItem(
                source=IntelligenceSource.GITHUB_ADVISORY,
                intelligence_type=IntelligenceType.VULNERABILITY,
                external_id=f"github:{adv.get('ghsa_id', '') or cve_id}",
                title=(adv.get("summary", "") or "")[:100],
                summary=(adv.get("description") or "")[:500],
                url=f"https://github.com/advisories/{adv.get('ghsa_id', '')}",
                published_at=self._parse_date(adv.get("published_at")),
                fetched_at=datetime.now(UTC),
                tags=("github", "vulnerability", ecosystem),
                severity=severity,
                confidence=0.95,
            )
            items.append(item)
        return items

    async def health_check(self) -> dict[str, Any]:
        try:
            start = datetime.now(UTC)
            resp = await self._client.get("https://api.github.com/advisories", params={"per_page": 1}, timeout=10.0)
            latency = (datetime.now(UTC) - start).total_seconds() * 1000
            if resp.status_code == 200:
                return {"status": "healthy", "latency_ms": latency, "last_fetch": datetime.now(UTC).isoformat()}
            return {"status": "degraded", "error": f"HTTP {resp.status_code}"}
        except Exception as exc:
            return {"status": "down", "error": str(exc)}

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None
