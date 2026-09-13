"""
ThreatFox feed client — malware IoCs (Auth-Key required, free at auth.abuse.ch).
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

LOG = logging.getLogger("ownex.intelligence.threatfox")


class ThreatFoxFeed(IntelligenceFeed):
    """ThreatFox malware IoC feed — Auth-Key gated (free at auth.abuse.ch)."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = 86400):
        self._cache_dir = os.path.join(os.getcwd(), "data", "intelligence", "threatfox")
        self._ttl = 86400
        os.makedirs(self._cache_dir, exist_ok=True)
        self._cache_file = os.path.join(self._cache_dir, "threatfox_cache.json")
        # ThreatFox requires a free Auth-Key (https://auth.abuse.ch) since
        # 2024/2025: keyless get_iocs answers 401. Key comes from env or
        # vault; without it the feed reports degraded, never fake data.
        self._auth_key = os.getenv("THREATFOX_AUTH_KEY") or self._vault_key()
        headers = {"Auth-Key": self._auth_key} if self._auth_key else {}
        self._client = httpx.AsyncClient(timeout=30.0, headers=headers)
        self._fetched_at: datetime | None = None

    @staticmethod
    def _vault_key() -> str | None:
        try:
            from cores.credentials.adapter_helpers import get_api_key

            return get_api_key("threatfox", {})
        except Exception:
            return None

    @property
    def source(self) -> IntelligenceSource:
        return IntelligenceSource.THREATFOX

    @property
    def intelligence_type(self) -> IntelligenceType:
        return IntelligenceType.THREAT_INTEL

    @property
    def cache_ttl_seconds(self) -> int:
        return 86400  # 24h

    @property
    def rate_limit_per_minute(self) -> int:
        return 60

    async def fetch_items(self, since: datetime | None = None, **kwargs) -> list:
        """Fetch recent IoCs from ThreatFox (needs Auth-Key; [] without it)."""
        if not self._auth_key:
            LOG.debug("ThreatFox skipped: no Auth-Key configured")
            return []
        try:
            resp = await self._client.post(
                "https://threatfox-api.abuse.ch/api/v1/",
                json={"query": "get_iocs", "days": int(kwargs.get("days", 3))},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            iocs = data.get("data", [])
        except Exception as exc:
            LOG.warning("ThreatFox fetch failed: %s", exc)
            return []

        items = []
        for ioc in iocs:
            ioc_type = ioc.get("ioc_type", "")
            ioc_value = ioc.get("ioc", "")
            malware = ioc.get("malware", "")
            threat_type = ioc.get("threat_type", "")
            confidence = ioc.get("confidence_level", 0)

            item = IntelligenceItem(
                source=IntelligenceSource.THREATFOX,
                intelligence_type=IntelligenceType.THREAT_INTEL,
                external_id=f"threatfox:{ioc_type}:{ioc_value}",
                title=f"ThreatFox IoC: {ioc_type} = {ioc_value}",
                summary=f"Malware: {malware}, Type: {threat_type}, Confidence: {confidence}%",
                url=f"https://threatfox.abuse.ch/ioc/{ioc_value}",
                published_at=self._parse_date(ioc.get("first_seen_utc")),
                fetched_at=datetime.now(UTC),
                tags=("threatfox", "ioc", threat_type.lower() if threat_type else "unknown"),
                severity=self._confidence_to_severity(confidence),
                confidence=min(confidence / 100.0, 1.0),
            )
            items.append(item)
        return items

    async def health_check(self) -> dict[str, Any]:
        if not self._auth_key:
            return {
                "status": "degraded",
                "error": "Auth-Key required (free at https://auth.abuse.ch; set THREATFOX_AUTH_KEY or vault key 'threatfox')",
            }
        try:
            start = datetime.now(UTC)
            resp = await self._client.post(
                "https://threatfox-api.abuse.ch/api/v1/",
                json={"query": "get_iocs", "days": 1},
                timeout=10.0,
            )
            latency = (datetime.now(UTC) - start).total_seconds() * 1000
            if resp.status_code == 200:
                return {"status": "healthy", "latency_ms": latency, "last_fetch": datetime.now(UTC).isoformat()}
            return {"status": "degraded", "error": f"HTTP {resp.status_code}", "latency_ms": latency}
        except Exception as exc:
            return {"status": "down", "error": str(exc)}

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _confidence_to_severity(self, confidence: int) -> str:
        if confidence >= 90:
            return "critical"
        if confidence >= 70:
            return "high"
        if confidence >= 50:
            return "medium"
        return "low"


__all__ = ["ThreatFoxFeed"]
