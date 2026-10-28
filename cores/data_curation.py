"""Data Curation Pipeline — raw text -> clean sellable dataset ($0, local CPU).

Sources: GitHub/StackOverflow/ArXiv exports fed by human/job (no scraping here).
Steps (pure, deterministic): normalize -> dedupe (sha256) -> quality filter
-> annotate (lang/domain/severity) -> package (JSONL + datasheet).
Sell: $500-5000 per niche dataset. License decided by human at export.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.data_curation")

_MIN_LEN = 40
_MAX_LEN = 8000


@dataclass(slots=True)
class CuratedRecord:
    id: str
    text: str
    lang: str = "unknown"  # es | en | code | unknown
    domain: str = "general"  # security | code | general
    quality: float = 0.0  # 0-1 heuristic
    source: str = "manual"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8", "ignore")).hexdigest()[:16]


def _detect_lang(text: str) -> str:
    code_hints = ("def ", "import ", "function(", "const ", "SELECT ", "curl ", "```")
    if any(h in text for h in code_hints):
        return "code"
    es_hits = len(re.findall(r"\b(el|la|los|las|una|para|con|está|vulnerabilidad)\b", text.lower()))
    en_hits = len(re.findall(r"\b(the|and|with|vulnerability|endpoint|request)\b", text.lower()))
    if es_hits == 0 and en_hits == 0:
        return "unknown"
    return "es" if es_hits >= en_hits else "en"


def _detect_domain(text: str) -> str:
    sec = ("vulnerab", "exploit", "CVE", "XSS", "SQLi", "IDOR", "SSRF", "payload", "PoC")
    code = ("def ", "class ", "import ", "function", "npm ", "pip ", "docker")
    low = text.lower()
    if any(h.lower() in low for h in sec):
        return "security"
    if any(h in text for h in code):
        return "code"
    return "general"


def _quality(text: str) -> float:
    score = 0.5
    n = len(text)
    if n > 200:
        score += 0.15
    if n > 800:
        score += 0.10
    if "```" in text or "curl" in text.lower():
        score += 0.10
    if len(re.findall(r"\d+\.", text)) >= 3:
        score += 0.05
    if len(set(text.split())) < 20:
        score -= 0.20
    return round(max(0.0, min(1.0, score)), 2)


class DataCurationPipeline:
    """In-memory curate -> package (persist via caller)."""

    def __init__(self) -> None:
        self._records: dict[str, CuratedRecord] = {}
        self._seen: set[str] = set()

    def curate(self, raw_items: list[dict[str, Any]], source: str = "manual") -> dict[str, int]:
        added = dupes = rejected = 0
        for raw in raw_items or []:
            text = str((raw or {}).get("text", "") or "").strip()
            if len(text) < _MIN_LEN or len(text) > _MAX_LEN:
                rejected += 1
                continue
            fp = _fingerprint(text)
            if fp in self._seen:
                dupes += 1
                continue
            self._seen.add(fp)
            rec = CuratedRecord(
                id=f"rec_{fp}",
                text=text,
                lang=_detect_lang(text),
                domain=_detect_domain(text),
                quality=_quality(text),
                source=source,
            )
            if rec.quality < 0.4:
                rejected += 1
                continue
            self._records[rec.id] = rec
            added += 1
        logger.info("Curated: +%d dupes=%d rejected=%d", added, dupes, rejected)
        return {"added": added, "dupes": dupes, "rejected": rejected, "total": len(self._records)}

    def package(self, min_quality: float = 0.6) -> dict[str, Any]:
        rows = [r for r in self._records.values() if r.quality >= min_quality]
        rows.sort(key=lambda r: r.quality, reverse=True)
        by_domain: dict[str, int] = {}
        by_lang: dict[str, int] = {}
        for r in rows:
            by_domain[r.domain] = by_domain.get(r.domain, 0) + 1
            by_lang[r.lang] = by_lang.get(r.lang, 0) + 1
        return {
            "total": len(rows),
            "min_quality": min_quality,
            "by_domain": by_domain,
            "by_lang": by_lang,
            "records": [
                {"id": r.id, "text": r.text[:2000], "lang": r.lang, "domain": r.domain, "quality": r.quality}
                for r in rows[:2000]
            ],
            "datasheet": "Niche dataset curado localmente. Licencia y precio los define el humano al vender.",
        }

    def count(self) -> int:
        return len(self._records)


_pipeline: DataCurationPipeline | None = None


def get_curation_pipeline() -> DataCurationPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = DataCurationPipeline()
    return _pipeline
