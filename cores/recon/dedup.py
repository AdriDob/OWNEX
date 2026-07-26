from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("cateye.recon.dedup")

_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_HEX_PATTERN = re.compile(r"(?<=/)[0-9a-fA-F]{8,}(?=/|$)")
_DIGIT_PATTERN = re.compile(r"(?<=/)\d+(?=/|$)")
_BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{20,}(?:=|==)?")
_JWT_PATTERN = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


def normalize_url(url: str) -> str:
    """Normalize a URL for dedup by replacing dynamic segments with placeholders."""
    result = _UUID_PATTERN.sub("{uuid}", url)
    result = _HEX_PATTERN.sub("{hex}", result)
    result = _DIGIT_PATTERN.sub("{id}", result)
    result = _BASE64_PATTERN.sub("{b64}", result)
    result = _JWT_PATTERN.sub("{jwt}", result)
    return result


def fingerprint_url(url: str) -> str:
    """Create a deterministic hash for a URL for dedup comparison."""
    normalized = normalize_url(url)
    return hashlib.sha256(normalized.encode()).hexdigest()


def fingerprint_endpoint(path: str, method: str = "GET") -> str:
    """Create a deterministic hash for an endpoint (path + method)."""
    normalized = normalize_url(path)
    key = f"{method.upper()}:{normalized}"
    return hashlib.sha256(key.encode()).hexdigest()


def dedup_urls(urls: list[str]) -> list[str]:
    """Remove duplicate URLs using normalized fingerprinting."""
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        fp = fingerprint_url(url)
        if fp not in seen:
            seen.add(fp)
            result.append(url)
    return result


def dedup_endpoints(endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate endpoints using path+method fingerprint.

    Each endpoint dict must have at least ``path`` and optionally ``method``.
    If multiple entries share the same fingerprint, the first is kept.
    """
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for ep in endpoints:
        path = ep.get("path", "/")
        method = ep.get("method", "GET")
        fp = fingerprint_endpoint(path, method)
        if fp not in seen:
            seen.add(fp)
            result.append(ep)
        else:
            logger.debug("Dedup skipped %s %s", method, path)
    return result


def dedup_naabu_ports(ports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate port entries by (host, port) key."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for entry in ports:
        host = entry.get("host", "")
        port = entry.get("port", 0)
        key = f"{host}:{port}"
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result


def load_and_dedup(path: Path, parser: Any) -> list[Any]:
    """Load items from a file and dedup them using the given parser function.

    The parser should return (items, dedup_key_fn) where items is a list and
    dedup_key_fn extracts a hashable key from each item.
    """
    if not path.exists():
        return []
    return dedup_urls(path.read_text().splitlines())


class SessionDedupTracker:
    """Per-session dedup tracker that persists seen fingerprints to a file.

    Allows cross-pipeline dedup within the same session.
    """

    def __init__(self, persist_path: Path | None = None):
        self._seen_urls: set[str] = set()
        self._seen_endpoints: set[str] = set()
        self._persist_path = persist_path
        if persist_path and persist_path.exists():
            self._load()

    def is_new_url(self, url: str) -> bool:
        fp = fingerprint_url(url)
        if fp in self._seen_urls:
            return False
        self._seen_urls.add(fp)
        return True

    def is_new_endpoint(self, path: str, method: str = "GET") -> bool:
        fp = fingerprint_endpoint(path, method)
        if fp in self._seen_endpoints:
            return False
        self._seen_endpoints.add(fp)
        return True

    def _load(self) -> None:
        if not self._persist_path:
            return
        for line in self._persist_path.read_text().splitlines():
            line = line.strip()
            if line:
                self._seen_urls.add(line)

    def save(self) -> None:
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._persist_path.write_text("\n".join(sorted(self._seen_urls)))
