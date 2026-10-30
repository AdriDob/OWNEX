"""
EPSS (Exploit Prediction Scoring System) client — FIRST API, keyless.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from cores.intelligence import (
    IntelligenceFeed,
    IntelligenceItem,
    IntelligenceSource,
    IntelligenceType,
)

LOG = logging.getLogger("ownex.intelligence.epss")


@dataclass(frozen=True, slots=True)
class EPSSEntry:
    cve: str
    epss: float
    percentile: float
    date: str


class EPSSFeed(IntelligenceFeed):
    """EPSS (Exploit Prediction Scoring System) feed — FIRST API, keyless."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 86400):
        self._cache_dir = os.path.join(os.getcwd(), "data", "intelligence", "epss")
        self._ttl = 86400
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, "epss_cache.json")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._fetched_at: datetime | None = None

    @property
    def source(self) -> IntelligenceSource:
        return IntelligenceSource.EPSS

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.THREAT_INTEL

    @property
    def cache_ttl_seconds(self) -> int:
        return 86400  # 24h

    @property
    def rate_limit_per_minute(self) -> int:
        return 60

    async def fetch_items(self, since: datetime | None = None, **kwargs) -> list[IntelligenceItem]:
        """Fetch EPSS scores. Since is ignored (full sync of current scores)."""
        try:
            resp = await self._client.get(
                "https://api.first.org/data/v1/epss",
                params={"limit": 1000},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            entries = data.get("data", [])
        except Exception as exc:
            LOG.warning("EPSS fetch failed: %s", exc)
            return []

        items = []
        for entry in entries:
            cve = entry.get("cve", "")
            epss = float(entry.get("epss", 0))
            percentile = float(entry.get("percentile", 0))
            date = entry.get("date", "")

            item = IntelligenceItem(
                source=IntelligenceSource.EPSS,
                intelligence_type=IntelligenceType.THREAT_INTEL,
                external_id=f"epss:{cve}",
                title=f"EPSS score for {cve}: {epss:.4f}",
                summary=f"EPSS: {epss:.4f} (percentile: {percentile:.2f}) — exploitation probability in next 30 days",
                url=f"https://www.first.org/epss",
                published_at=self._parse_date(date),
                fetched_at=datetime.now(UTC),
                tags=("epss", "exploit_probability"),
                severity=self._severity_from_epss(epss),
                confidence=0.9,
            )
            items.append(item)
        return items

    async def health_check(self) -> dict[str, Any]:
        try:
            start = datetime.now(UTC)
            resp = await self._client.get("https://api.first.org/data/v1/epss", params={"limit": 1}, timeout=5.0)
            latency = (datetime.now(UTC) - start).total_seconds() * 1000
            if resp.status_code == 200:
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "last_fetch": datetime.now(UTC).isoformat(),
                }
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

    def _severity_from_epss(self, epss: float) -> str | None:
        if epss >= 0.9:
            return "critical"
        if epss >= 0.5:
            return "high"
        if epss >= 0.1:
            return "medium"
        if epss > 0:
            return "low"
        return "info"


__all__ = ["EPSSFeed"]
