"""
NVD (National Vulnerability Database) client — API 2.0, keyless (generous limits).
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

LOG = logging.getLogger("ownex.intelligence.nvd")


@dataclass(frozen=True, slots=True)
class NVDCVE:
    id: str
    description: str
    metrics: dict
    published: str
    last_modified: str
    references: list[dict]
    configurations: list[dict]


class NVDFeed(IntelligenceFeed):
    """NVD (National Vulnerability Database) feed — API 2.0, keyless, generous limits."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 86400):
        self._cache_dir = os.path.join(os.getcwd(), "data", "intelligence", "nvd")
        self._ttl = 86400
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, "nvd_cache.json")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._fetched_at: datetime | None = None

    @property
    def source(self) -> IntelligenceSource:
        return IntelligenceSource.NVD

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.VULNERABILITY

    @property
    def cache_ttl_seconds(self) -> int:
        return 86400  # 24h

    @property
    def rate_limit_per_minute(self) -> int:
        return 60  # NVD API 2.0 allows 50 req/30s without key

    async def fetch_items(self, since: datetime | None = None, **kwargs) -> list[IntelligenceItem]:
        """Fetch recent CVEs from NVD."""
        params: dict[str, str | int] = {"resultsPerPage": 100}
        if since:
            params["pubStartDate"] = since.strftime("%Y-%m-%dT%H:%M:%S.000")

        try:
            resp = await self._client.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            vulns = data.get("vulnerabilities", [])
        except Exception as exc:
            LOG.warning("NVD fetch failed: %s", exc)
            return []

        items = []
        for vuln in vulns:
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "")
            descriptions = cve.get("descriptions", [])
            desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")
            cvss_v3 = (
                cve.get("metrics", {}).get("cvssMetricV31", [{}])[0].get("cvssData", {})
                if cve.get("metrics", {}).get("cvssMetricV31")
                else {}
            )
            cvss_v2 = (
                cve.get("metrics", {}).get("cvssMetricV2", [{}])[0].get("cvssData", {})
                if cve.get("metrics", {}).get("cvssMetricV2")
                else {}
            )
            cvss = cvss_v3 or cvss_v2
            severity = (cvss.get("baseSeverity") or "").lower() or "info"

            item = IntelligenceItem(
                source=IntelligenceSource.NVD,
                intelligence_type=IntelligenceType.VULNERABILITY,
                external_id=cve_id,
                title=cve_id,
                summary=desc[:500],
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                published_at=self._parse_date(cve.get("published")),
                fetched_at=datetime.now(UTC),
                tags=("nvd", "vulnerability"),
                severity=severity,
                confidence=0.95,
            )
            items.append(item)
        return items

    async def health_check(self) -> dict[str, Any]:
        try:
            start = datetime.now(UTC)
            resp = await self._client.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={"resultsPerPage": 1},
                timeout=10.0,
            )
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


__all__ = ["NVDFeed"]
