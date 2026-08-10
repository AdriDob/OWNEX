"""
threat_intel — Ingesta de Threat Intelligence → Vulnerability Hypotheses (capa extra de OWNEX).

Este módulo cierra el gap entre el discovery reactivo (endpoint signals + Nuclei matches) y
fuentes externas de amenazas conocidas. Correlaciona el tech stack del target contra el
catálogo CISA KEV (Known Exploited Vulnerabilities) y genera hipótesis proactivas con
likelihood proporcional a active exploitation + ransomware campaign.

Cierre del "capa extra" diagnosticada por el usuario: el sistema era estrictamente reactivo
(scan → match → hipótesis). Esta capa añade generación proactiva a partir de threat intel.

Diseño:
- ThreatIntelFeed: fetch CISA KEV JSON + cache 24h (data/threat_intel/kev_cache.json).
  Fetch vía urllib (stdlib; tolera ausencia de red: cache viejo o vacío no rompe runtime).
- generate_from_threat_intel: correlaciona tech_stack vs vendor_project del KEV;
  produce Hypothesis(source=THREAT_INTEL) con likelihood = active_exploitation_weight.

Revenue Rule: +detección (proactive known-exploited CVE), +calidad de evidencia
(KEV = evidencia de explotación real en producción). Nunca inventa CVE.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from cores.engine.hypothesis.models import (
    Hypothesis,
    HypothesisSource,
    VulnerabilityType,
)

LOG = logging.getLogger("ownex.hypothesis.threat_intel")

_KEV_FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known-exploited-vulnerabilities.json"
_CACHE_DIR = os.path.join(os.getcwd(), "data", "threat_intel")
_CACHE_FILE = os.path.join(_CACHE_DIR, "kev_cache.json")
_CACHE_TTL_SECONDS = 86400  # 24 hours


@dataclass
class _KevEntry:
    cve_id: str
    vendor_project: str
    product: str
    short_description: str
    technical_alert: bool
    severity: str
    date_added: str
    required_action: str
    days_since_added: int


@dataclass
class ThreatIntelFeed:
    """CISA KEV feed with 24h local cache. Network failure degrades to cache/empty."""

    def __init__(self, cache_dir: str | None = None, ttl_seconds: int = _CACHE_TTL_SECONDS):
        if cache_dir is not None:
            global _CACHE_DIR, _CACHE_FILE
            _CACHE_DIR = cache_dir
            _CACHE_FILE = os.path.join(_CACHE_DIR, "kev_cache.json")
        self._cache_dir = cache_dir or _CACHE_DIR
        self._ttl = ttl_seconds

    def load(self) -> list[_KevEntry]:
        raw = self._load_raw()
        if not raw:
            return []
        vulns = raw.get("vulnerabilities", [])
        entries: list[_KevEntry] = []
        today = datetime.now(UTC)
        for v in vulns:
            try:
                added = datetime.strptime(v.get("dateAdded", ""), "%Y-%m-%d").replace(tzinfo=UTC)
                days = max((today - added).days, 0)
            except (ValueError, TypeError):
                days = 0
            entries.append(
                _KevEntry(
                    cve_id=v.get("cveID", ""),
                    vendor_project=v.get("vendorProject", "").lower(),
                    product=v.get("product", "").lower(),
                    short_description=v.get("shortDescription", ""),
                    technical_alert=bool(v.get("technicalAlerts", False)),
                    severity=(v.get("severity", "") or "").lower(),
                    date_added=v.get("dateAdded", ""),
                    required_action=v.get("requiredAction", ""),
                    days_since_added=days,
                )
            )
        return entries

    def _load_raw(self) -> dict[str, Any] | None:
        cached = self._read_cache()
        if cached and self._cache_valid(cached):
            return cached
        fetched = self._fetch_feed()
        if fetched:
            self._write_cache(fetched)
            return fetched
        if cached:
            return cached
        LOG.warning("KEV feed unavailable and no cache; threat-intel hypotheses disabled")
        return None

    def _read_cache(self) -> dict[str, Any] | None:
        if not os.path.exists(_CACHE_FILE):
            return None
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def _cache_valid(self, cached: dict[str, Any]) -> bool:
        ts = cached.get("_fetched_at")
        if not ts:
            return False
        try:
            fetched = datetime.fromisoformat(ts)
        except ValueError:
            return False
        return (datetime.now(UTC) - fetched).total_seconds() < self._ttl

    @staticmethod
    def _fetch_feed() -> dict[str, Any] | None:
        try:
            req = urllib.request.Request(
                _KEV_FEED_URL,
                headers={"User-Agent": "OWNEX-ThreatIntel/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    return None
                data = json.loads(resp.read().decode("utf-8"))
                data["_fetched_at"] = datetime.now(UTC).isoformat()
                return data
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            LOG.info("KEV fetch failed (ok, degrades to cache): %s", exc)
            return None

    @staticmethod
    def _write_cache(data: dict[str, Any]) -> None:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        tmp = _CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, _CACHE_FILE)


def _normalize_tech(tokens: list[Any] | None) -> list[str]:
    keywords: list[str] = []
    if not tokens:
        return keywords
    for t in tokens:
        if isinstance(t, str):
            keywords.append(t.lower())
        elif isinstance(t, dict):
            keywords.append(str(t.get("name", "")).lower())
            keywords.append(str(t.get("vendor", "")).lower())
    return keywords


def _matches(entry: _KevEntry, tech: list[str]) -> bool:
    if not tech:
        return False
    kev_blob = f"{entry.vendor_project} {entry.product} {entry.short_description}".lower()
    for kw in tech:
        kw_s = kw.strip()
        if kw_s and kw_s in kev_blob:
            return True
    return False


def _likelihood(entry: _KevEntry) -> float:
    score = 0.50  # KEV = actively exploited, baseline moderate-high
    if entry.technical_alert:
        score += 0.15
    if entry.severity in ("critical", "high"):
        score += 0.10
    # reciente + days_since_added → frescura del exploit en la wild
    if entry.days_since_added <= 30:
        score += 0.10
    elif entry.days_since_added <= 90:
        score += 0.05
    return min(score, 0.95)


def _cve_references(cve_id: str) -> list[str]:
    base = cve_id.lower()
    if base.startswith("cve-"):
        num = base[4:]
        return [
            f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            f"https://github.com/CVEProject/nvdcve-data-feed/blob/v0.2.0/data/{num}.json",
        ]
    return []


def generate_from_threat_intel(
    target_id: int,
    target_name: str,
    technologies: list[Any] | None = None,
    endpoint: dict[str, Any] | None = None,
    feed: ThreatIntelFeed | None = None,
) -> list[Hypothesis]:
    """Correlaciona threat intel (CISA KEV) con el tech stack del target.

    No hace red en tests (feed se inyecta o degrada). Cada match KEV → 1 hipótesis
    con source=THREAT_INTEL, prioritized by likelihood × recency.
    """
    tech = _normalize_tech(technologies or [])
    if not tech:
        return []

    f = feed or ThreatIntelFeed()
    entries = [e for e in f.load() if _matches(e, tech)]
    if not entries:
        return []

    ep = endpoint or {"url": "", "method": "GET", "path": "/"}

    hypotheses: list[Hypothesis] = []
    for e in entries:
        hid = f"ti:{e.cve_id}:{hashlib.sha256(ep.get('path', '').encode()).hexdigest()[:6]}"
        vuln_type = _map_cve_to_vuln_type(e.cve_id, e.short_description)
        hyp = Hypothesis(
            id=hid,
            vulnerability_type=vuln_type,
            target_id=target_id,
            target_name=target_name,
            endpoint=ep,
            likelihood=_likelihood(e),
            impact=0.9,
            exploitability=0.85 if e.technical_alert else 0.7,
            confidence=0.6,
            priority_score=_likelihood(e) * 0.6 + 0.9 * 0.4,
            evidence=[
                f"KEV entry {e.cve_id} present in CISA catalog (active exploitation in wild)",
                f"Known ransomware campaign: {'yes' if e.technical_alert else 'no'}",
                f"Added to KEV {e.days_since_added} days ago (recency bonus applied)",
            ],
            reasoning=(
                f"CISA KEV {e.cve_id}: {e.short_description[:200]}. "
                f"Vendor/product '{e.vendor_project}/{e.product}' matches target tech stack "
                f"({', '.join(tech[:5])}). This vulnerability is actively exploited — "
                f"prioritize validation over scan-based hypotheses."
            ),
            suggested_actions=[
                f"Verify {e.cve_id} presence via version fingerprinting of '{e.vendor_project}'",
                f"Check {e.required_action}",
                "If matched, craft PoC leveraging the known exploit technique",
            ],
            source=HypothesisSource.THREAT_INTEL,
            vector=f"kev/{e.cve_id.lower()}/known-exploited",
            roi_score=round(_likelihood(e) * 80.0, 1),
            attack_surface_labels=[e.vendor_project, "threat-intel"],
            estimated_reward_range=e.severity,
            estimated_time_minutes=30,
            estimated_difficulty="alta" if _likelihood(e) > 0.75 else "media",
            what_is_this="Vulnerabilidad conocida y explotada en producción (CISA KEV).",
            why_suspected=f"Coincidencia de tecnología ({e.vendor_project}) con catálogo KEV.",
            real_world_impact=f"Exploitación activa confirmada por CISA; {e.severity} severity.",
            how_to_verify=(f"Fingerprint version de {e.vendor_project} en el target, comparar contra {e.cve_id}.",),
        )
        hypotheses.append(hyp)
    hypotheses.sort(key=lambda h: h.priority_score, reverse=True)
    LOG.info("Threat intel generated %d hypotheses for target %s (tech=%s)", len(hypotheses), target_name, tech)
    return hypotheses


def _map_cve_to_vuln_type(cve_id: str, description: str) -> VulnerabilityType:
    desc = description.lower()
    if "remote code execution" in desc or "rce" in desc:
        return VulnerabilityType.KNOWN_VULNERABILITY
    if "privilege escalation" in desc:
        return VulnerabilityType.PRIVILEGE_ESCALATION
    if "authentication bypass" in desc or "auth bypass" in desc:
        return VulnerabilityType.AUTH_BYPASS
    if "information disclosure" in desc or "information exposure" in desc:
        return VulnerabilityType.DATA_EXPOSURE
    if "sql injection" in desc:
        return VulnerabilityType.SQLI
    if "cross-site scripting" in desc or "xss" in desc:
        return VulnerabilityType.XSS
    if "ssrf" in desc:
        return VulnerabilityType.SSRF
    return VulnerabilityType.KNOWN_VULNERABILITY


__all__ = ["ThreatIntelFeed", "generate_from_threat_intel"]
