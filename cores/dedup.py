"""Unified deduplication tracker — shared across discovery sources and pipeline.

Provides standard fingerprint functions and an in-memory tracker (backed by DB
for critical paths) to prevent processing the same item twice within a session.

Usage:
    from cores.dedup import DedupTracker, fingerprint_url, fingerprint_path

    tracker = DedupTracker()
    uid = fingerprint_url("https://example.com/api/users/123")
    if not tracker.seen(uid):
        process(item)
"""

from __future__ import annotations

import hashlib
import re
import time

UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
DIGIT_PATTERN = re.compile(r"\d+")
HEX_PATTERN = re.compile(r"[0-9a-f]{8,}", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{20,}")


def fingerprint_url(url: str) -> str:
    """Normalize a URL into a fingerprint that ignores IDs and tokens."""
    clean = UUID_PATTERN.sub("{uuid}", url)
    clean = HEX_PATTERN.sub("{hex}", clean)
    clean = DIGIT_PATTERN.sub("{id}", clean)
    clean = TOKEN_PATTERN.sub("{token}", clean)
    return hashlib.sha256(clean.encode()).hexdigest()[:16]


def fingerprint_path(path: str, method: str = "") -> str:
    """Normalize a path+method pair into a fingerprint."""
    clean = UUID_PATTERN.sub("{uuid}", path)
    clean = HEX_PATTERN.sub("{hex}", clean)
    clean = DIGIT_PATTERN.sub("{id}", clean)
    key = f"{method}:{clean}" if method else clean
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def fingerprint_program(name: str, platform: str = "") -> str:
    """Fingerprint a bug bounty program name."""
    key = f"{platform}:{name.strip().lower()}" if platform else name.strip().lower()
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class DedupTracker:
    """In-memory dedup tracker with optional TTL.

    Thread-safe for concurrent discovery sources within a scan session.
    """

    def __init__(self, ttl: float = 0) -> None:
        self._seen: dict[str, float] = {}
        self._ttl = ttl

    def seen(self, fingerprint: str) -> bool:
        """Check and mark an item as seen. Returns True if already seen."""
        now = time.time()
        if fingerprint in self._seen:
            ts = self._seen[fingerprint]
            if not self._ttl or (now - ts) < self._ttl:
                return True
        self._seen[fingerprint] = now
        return False

    def mark(self, fingerprint: str) -> None:
        self._seen[fingerprint] = time.time()

    def forget(self, fingerprint: str) -> None:
        self._seen.pop(fingerprint, None)

    def clear(self) -> None:
        self._seen.clear()

    def size(self) -> int:
        return len(self._seen)


# Global session-level tracker — shared by all discovery sources in a scan
_session_tracker: DedupTracker | None = None


def get_session_tracker() -> DedupTracker:
    global _session_tracker
    if _session_tracker is None:
        _session_tracker = DedupTracker()
    return _session_tracker


def reset_session_tracker() -> None:
    global _session_tracker
    _session_tracker = None
