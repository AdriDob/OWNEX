"""
Intelligence Sources — Unified abstraction for all external intelligence feeds.

Single Source of Truth for: vulnerability feeds, threat intel, scientific feeds,
engineering feeds, and any future intelligence sources. All consumers import
from here, never directly from feed implementations.

Design principles:
- $0 + keyless first + graceful degradation
- 24h cache standard (configurable per source)
- Every source implements INTELLIGENCE_SOURCE contract
- Cache with provenance (fetched_at, source, version, hash)
- Health endpoint per source + aggregate
- Provenance on every item: source, fetched_at, version, content_hash
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class IntelligenceType(StrEnum):
    """Canonical intelligence types for routing and UI grouping."""

    # Vulnerability / Threat Intel
    VULNERABILITY = "vulnerability"
    THREAT_INTEL = "threat_intel"
    EXPLOIT = "exploit"

    # Scientific / Engineering
    PAPER = "paper"
    RESEARCH = "research"
    TECHNOLOGY = "technology"

    # Engineering / Dev
    TOOL = "tool"
    LIBRARY = "library"
    FRAMEWORK = "framework"
    VULNERABILITY_PATCH = "vulnerability_patch"

    # General
    GENERAL = "general"
    UNKNOWN = "unknown"


class IntelligenceSource(StrEnum):
    """Canonical source identifiers. Each feed gets a unique code."""

    # Vuln / Threat
    CISA_KEV = "cisa_kev"
    OSV = "osv"
    EPSS = "epss"
    NVD = "nvd"
    GITHUB_ADVISORY = "github_advisory"
    THREATFOX = "threatfox"
    EXPLOIT_DB = "exploit_db"

    # Science / Engineering
    ARXIV = "arxiv"
    OPENALEX = "openalex"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PUBMED = "pubmed"

    # Engineering / Dev
    OSS_FUZZ = "oss_fuzz"
    PYPI = "pypi"
    NPM = "npm"
    CRATES_IO = "crates_io"

    # Engineering
    GITHUB = "github"
    GITLAB = "gitlab"
    DOCKER_HUB = "docker_hub"

    # General
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class IntelligenceItem:
    """
    Single intelligence item from any source.
    All sources MUST produce this shape (or a subclass).
    """

    # Required
    source: IntelligenceSource
    intelligence_type: IntelligenceType
    external_id: str  # source-specific unique ID (CVE-..., arXiv:..., DOI, etc.)

    # Content
    title: str
    summary: str
    url: str | None = None

    # Metadata
    published_at: datetime | None = None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Classification
    tags: tuple[str, ...] = ()
    severity: str | None = None  # critical, high, medium, low, info, unknown
    confidence: float = 1.0  # 0-1, source reliability × freshness

    # Provenance (auto-filled by cache layer)
    source_fetched_at: datetime | None = None
    raw_payload: dict | None = None  # full original payload for audit

    # Context
    related_ids: tuple[str, ...] = ()  # related external IDs (CVE, DOI, etc.)

    @property
    def content_hash(self) -> str:
        """Stable hash of content for deduplication."""
        import hashlib

        content = f"{self.source}|{self.external_id}|{self.title}|{self.summary}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class IntelligenceFeed(ABC):
    """
    Abstract base for all intelligence feeds.
    Every feed MUST implement this contract.
    """

    @property
    @abstractmethod
    def source(self) -> IntelligenceSource:
        """Unique source identifier."""

    @property
    @abstractmethod
    def intelligence_type(self) -> IntelligenceType:
        """Primary intelligence type this feed produces."""

    @property
    @abstractmethod
    def cache_ttl_seconds(self) -> int:
        """Cache TTL in seconds. Default 24h = 86400."""

    @property
    @abstractmethod
    def rate_limit_per_minute(self) -> int:
        """Max requests per minute. 0 = no limit (respectful default)."""

    @abstractmethod
    async def fetch_items(self, since: datetime | None = None, **kwargs) -> list[IntelligenceItem]:
        """
        Fetch new items since timestamp.
        since=None means full refresh (respects cache).
        Returns list of IntelligenceItem.
        """

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """
        Health check for this feed.
        Returns: {status: healthy|degraded|down, latency_ms, last_fetch, error?, rate_limit_remaining?}
        """

    def get_cache_key(self, **params) -> str:
        """Generate cache key for this feed + params."""
        import hashlib

        key = f"{self.source.value}:{sorted(params.items())}"
        return hashlib.sha256(key.encode()).hexdigest()[:32]


def _default_cache_dir() -> Path:
    """Data-dir aware default: frozen bundles honor OWNEX_DATA_DIR, dev keeps ./data."""
    import os

    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path.cwd() / "data"
    return root / "intelligence"


class IntelligenceCache:
    """
    Persistent cache for intelligence items with provenance.
    Stores items + provenance in JSONL format for durability.
    """

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = Path(cache_dir or _default_cache_dir())
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._items_file = self.cache_dir / "items.jsonl"
        self._index: dict[str, int] = {}  # "source|external_id" -> line_number
        self._load_index()

    def _load_index(self) -> None:
        if not self._items_file.exists():
            return
        try:
            with open(self._items_file, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if not line.strip():
                        continue
                    import json

                    item = json.loads(line)
                    eid = item.get("external_id") or item.get("external_id")
                    src = item.get("source")
                    if eid and src:
                        self._index[f"{src}|{eid}"] = i
        except Exception:
            pass

    def get(self, source: str, external_id: str) -> tuple[dict, dict] | None:
        """Get item + provenance. Returns None if not found."""
        key = f"{source}|{external_id}"
        if key not in self._index:
            return None
        try:
            with open(self._items_file, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if i == self._index.get(key):
                        import json

                        item = json.loads(line)
                        # For now return None provenance (simplified)
                        return item, {}
        except Exception:
            pass
        return None

    def upsert(self, item: IntelligenceItem, provenance: Any) -> bool:
        """Upsert item with provenance. Returns True if new/updated."""
        import json

        # Build item dict
        item_dict = {
            "source": item.source.value,
            "intelligence_type": item.intelligence_type.value,
            "external_id": item.external_id,
            "title": item.title,
            "summary": item.summary,
            "url": item.url,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "fetched_at": item.fetched_at.isoformat() if item.fetched_at else None,
            "tags": list(item.tags),
            "severity": item.severity,
            "confidence": item.confidence,
            "source_fetched_at": item.source_fetched_at.isoformat() if item.source_fetched_at else None,
            "content_hash": item.content_hash,
            "raw_payload": item.raw_payload,
            "related_ids": list(item.related_ids),
        }

        # Write to items file (append-only JSONL)

        with open(self._items_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(item_dict, ensure_ascii=False) + "\n")

        return True

    def iter_source(self, source: str, limit: int = 200) -> list[dict]:
        """Cached item dicts for one source (newest last). Best-effort, never raises."""
        out: list[dict] = []
        try:
            if not self._items_file.exists():
                return out
            import json

            with open(self._items_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except ValueError:
                        continue
                    if item.get("source") == source:
                        out.append(item)
                        if len(out) >= limit:
                            break
        except Exception:
            pass
        return out

    def stats(self) -> dict:
        """Return cache statistics."""
        try:
            count = 0
            if self._items_file.exists():
                with open(self._items_file, encoding="utf-8") as f:
                    count = sum(1 for _ in f)
            return {
                "items": count,
                "cache_dir": str(self.cache_dir),
            }
        except Exception:
            return {"items": 0, "cache_dir": str(self.cache_dir)}


class IntelligenceRegistry:
    """
    Registry of all available intelligence feeds.
    Provides unified access + health + cache management.
    """

    def __init__(self, cache_dir: Path | None = None):
        self._feeds: dict[str, IntelligenceFeed] = {}
        self._cache = IntelligenceCache(cache_dir or _default_cache_dir())
        self._last_fetch: dict[str, datetime] = {}

    def register(self, feed: IntelligenceFeed) -> None:
        if feed.source in self._feeds:
            raise ValueError(f"Source {feed.source} already registered")
        self._feeds[feed.source] = feed

    def get(self, source: IntelligenceSource) -> IntelligenceFeed | None:
        return self._feeds.get(source)

    def get_all(self) -> list[IntelligenceFeed]:
        return list(self._feeds.values())

    def get_by_type(self, intelligence_type: IntelligenceType) -> list[IntelligenceFeed]:
        return [f for f in self._feeds.values() if f.intelligence_type == intelligence_type]

    def is_fresh(self, source: IntelligenceSource) -> bool:
        """True when this source was fetched within its own TTL (no network needed)."""
        try:
            feed = self._feeds.get(source)
            last = self._last_fetch.get(source.value if hasattr(source, "value") else str(source))
            if feed is None or last is None:
                return False
            ttl = int(getattr(feed, "cache_ttl_seconds", 86400))
            return (datetime.now(UTC) - last).total_seconds() < ttl
        except Exception:
            return False

    async def fetch_all(
        self,
        since: datetime | None = None,
        types: list[IntelligenceType] | None = None,
        force: bool = False,
    ) -> dict[str, list]:
        """
        Fetch from all registered feeds (or filtered by type).
        Fresh feeds (within TTL) are skipped unless force=True.
        Returns dict of source -> items.
        """
        feeds = self._feeds.values()
        if types:
            feeds = [f for f in feeds if f.intelligence_type in types]

        results = {}
        for feed in feeds:
            try:
                if not force and self.is_fresh(feed.source):
                    results[feed.source.value] = []
                    continue
                items = await feed.fetch_items(since)
                results[feed.source.value] = items
                self._last_fetch[feed.source.value] = datetime.now(UTC)
            except Exception as e:
                import logging

                logging.getLogger("ownex.intelligence").warning(f"Feed {feed.source} failed: {e}")
                results[feed.source.value] = []
        return results

    async def health_check_all(self) -> dict[str, dict]:
        """Health check all registered feeds."""
        results = {}
        for source, feed in self._feeds.items():
            try:
                results[source.value] = await feed.health_check()
            except Exception as e:
                results[source.value] = {"status": "down", "error": str(e)}
        return results

    def get_cache_stats(self) -> dict:
        return self._cache.stats()


# Singleton
_registry: IntelligenceRegistry | None = None


def get_intelligence_registry(cache_dir: Path | None = None) -> IntelligenceRegistry:
    global _registry
    if _registry is None:
        _registry = IntelligenceRegistry(cache_dir or _default_cache_dir())
    return _registry


def reset_intelligence_registry() -> None:
    """For testing."""
    global _registry
    _registry = None


def build_default_intelligence_registry(cache_dir: Path | None = None) -> IntelligenceRegistry:
    """Build the default intelligence registry with all standard feeds (7: 5 vuln + 2 science)."""
    from cores.intelligence.feeds.arxiv_feed import ArxivFeed
    from cores.intelligence.feeds.epss_feed import EPSSFeed
    from cores.intelligence.feeds.github_advisory_feed import GitHubAdvisoryFeed
    from cores.intelligence.feeds.nvd_feed import NVDFeed
    from cores.intelligence.feeds.openalex_feed import OpenAlexFeed
    from cores.intelligence.feeds.osv_feed import OSVFeed
    from cores.intelligence.feeds.threatfox_feed import ThreatFoxFeed

    registry = IntelligenceRegistry(cache_dir)

    # Register vulnerability/threat intelligence feeds
    registry.register(OSVFeed())
    registry.register(EPSSFeed())
    registry.register(NVDFeed())
    registry.register(GitHubAdvisoryFeed())
    # ThreatFox needs a free Auth-Key (auth.abuse.ch); without it the feed
    # reports degraded and yields [] — never fake IoCs (wired 2026-09-12).
    registry.register(ThreatFoxFeed())
    # Science/engineering feeds (keyless, cs.CR/cs.AI/cs.CL/cs.LG default).
    registry.register(ArxivFeed())
    registry.register(OpenAlexFeed())

    return registry
