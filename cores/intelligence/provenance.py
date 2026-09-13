"""
Provenance tracking for intelligence items.
Records: source, fetched_at, version, content_hash, raw_payload hash.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cores.intelligence import IntelligenceItem


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """
    Immutable record of an item's origin and processing.
    Stored alongside the intelligence item in cache.
    """

    source: str  # IntelligenceSource.value
    item_external_id: str
    content_hash: str
    raw_payload_hash: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    feed_version: str = "1.0"
    fetch_duration_ms: int | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "item_external_id": self.item_external_id,
            "fetched_at": self.fetched_at.isoformat(),
            "content_hash": self.content_hash,
            "raw_payload_hash": self.raw_payload_hash,
            "feed_version": self.feed_version,
            "fetch_duration_ms": self.fetch_duration_ms,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProvenanceRecord":
        return cls(
            source=data["source"],
            item_external_id=data["item_external_id"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            content_hash=data["content_hash"],
            raw_payload_hash=data["raw_payload_hash"],
            feed_version=data.get("feed_version", "1.0"),
            fetch_duration_ms=data.get("fetch_duration_ms"),
            error=data.get("error"),
        )


class ContentHasher:
    """Utility for computing stable content hashes."""

    @staticmethod
    def hash_content(item_external_id: str, title: str, summary: str, source: str) -> str:
        """Stable hash for deduplication."""
        content = f"{item_external_id}|{title}|{summary}|{source}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    def hash_payload(payload: dict) -> str:
        """Hash of the raw payload for change detection."""
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode()).hexdigest()[:32]

    @staticmethod
    def compute_item_hash(item: "IntelligenceItem") -> str:
        """Compute hash from an IntelligenceItem."""
        content = f"{item.source}|{item.external_id}|{item.title}|{item.summary}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
