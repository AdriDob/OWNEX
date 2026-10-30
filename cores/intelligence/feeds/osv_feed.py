"""
OSV (Open Source Vulnerabilities) client — keyless, 24h cache.
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

LOG = logging.getLogger("ownex.intelligence.osv")


@dataclass(frozen=True, slots=True)
class OSVVuln:
    id: str
    summary: str
    details: str
    aliases: list[str]
    affected: list[dict]
    references: list[dict]
    published: str
    modified: str
    severity: list[dict]
    ecosystem_specific: dict
    database_specific: dict


class OSVFeed(IntelligenceFeed):
    """OSV (Open Source Vulnerabilities) feed — keyless, 24h cache."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 86400):
        self._cache_dir = os.path.join(cache_dir or os.getcwd(), "data", "intelligence", "osv")
        self._ttl = ttl_seconds
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, "osv_cache.json")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._fetched_at: datetime | None = None

    @property
    def source(self) -> IntelligenceSource:
        return IntelligenceSource.OSV

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
        """Query OSV for vulnerabilities affecting given packages.

        OSV has no "list recent" endpoint (GET /v1/vulns/list answers 415),
        so this feed is query-driven: pass ``packages=[{ecosystem, name,
        version?}]``. With no packages given it scans this repo's own
        ``requirements.txt`` (self-scan: the hunter's own stack first).
        """
        packages = kwargs.get("packages") or self.default_packages()
        if not packages:
            return []

        items: list[IntelligenceItem] = []
        try:
            queries = [
                {
                    "package": {"name": p["name"], "ecosystem": p.get("ecosystem", "PyPI")},
                    **({"version": p["version"]} if p.get("version") else {}),
                }
                for p in packages[:50]
            ]
            resp = await self._client.post(
                "https://api.osv.dev/v1/querybatch",
                json={"queries": queries},
                timeout=30.0,
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
        except Exception as exc:
            LOG.warning("OSV fetch failed: %s", exc)
            return []

        for query, result in zip(queries, results):
            for v in result.get("vulns", []):
                items.append(self._to_item(v, query["package"]["name"]))
        return items

    @staticmethod
    def default_packages() -> list[dict[str, str]]:
        """Parse this repo's requirements.txt into OSV package queries."""
        req_file = os.path.join(os.getcwd(), "requirements.txt")
        packages: list[dict[str, str]] = []
        try:
            with open(req_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith(("#", "-", " ")):
                        continue
                    name = line.split("=")[0].split(">")[0].split("<")[0].split(";")[0].strip()
                    if name:
                        packages.append({"name": name, "ecosystem": "PyPI"})
        except OSError:
            pass
        return packages

    def _to_item(self, v: dict, package_name: str) -> IntelligenceItem:
        return IntelligenceItem(
            source=IntelligenceSource.OSV,
            intelligence_type=IntelligenceType.VULNERABILITY,
            external_id=v.get("id", ""),
            title=v.get("summary", v.get("id", "")),
            summary=v.get("details", "")[:500],
            url=f"https://osv.dev/vulnerability/{v.get('id', '')}",
            published_at=self._parse_date(v.get("published")),
            fetched_at=datetime.now(UTC),
            tags=("osv", "vulnerability", package_name),
            severity=self._severity_from_vuln(v),
            confidence=0.95,
        )

    async def health_check(self) -> dict[str, Any]:
        try:
            start = datetime.now(UTC)
            resp = await self._client.post(
                "https://api.osv.dev/v1/querybatch",
                json={"queries": [{"package": {"name": "requests", "ecosystem": "PyPI"}}]},
                timeout=10.0,
            )
            latency = (datetime.now(UTC) - start).total_seconds() * 1000
            if resp.status_code == 200:
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "last_fetch": datetime.now(UTC).isoformat(),
                }
            return {"status": "degraded", "error": f"HTTP {resp.status_code}", "latency_ms": latency}
        except Exception as exc:
            return {"status": "down", "error": str(exc)}

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            # OSV uses RFC3339 format
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _severity_from_vuln(self, vuln: dict) -> str | None:
        severity = vuln.get("severity", [])
        if not severity:
            return None
        # Take highest severity
        severities = [s.get("score", "").lower() for s in severity if isinstance(s, dict)]
        if "critical" in severities:
            return "critical"
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        if "low" in severities:
            return "low"
        return "info"


__all__ = ["OSVFeed"]
