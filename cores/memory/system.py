"""Unified Memory — ORION Persistent Memory Subsystem"""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import create_engine

from database.db import SessionLocal

logger = logging.getLogger("catseye.memory")

MAX_LOAD_WARNINGS = 10
_warning_keys: set[str] = set()

# ── MemoryTier ────────────────────────────────────────────────────


class MemoryTier:
    """Memory tiers: permanent vs temporary."""

    PERMANENT = "permanent"  # Survives restarts, never auto-expires
    TEMPORARY = "temporary"  # Auto-expires, session-scoped
    CACHED = "cached"  # Short TTL, rebuildable


# ── MemoryEntry ────────────────────────────────────────────────────


def _parse_dt(value: Any) -> datetime:
    """Parse an ISO datetime string back to an aware datetime (fallback: now)."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return datetime.now(UTC)


class MemoryEntry:
    """Single memory entry with metadata."""

    def __init__(
        self,
        namespace: str,
        key: str,
        value: Any,
        tier: str = "permanent",
        ttl_seconds: int | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.namespace = namespace
        self.key = key
        self.value = value
        self.tier = tier
        self.ttl_seconds = ttl_seconds
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now(UTC)
        self.updated_at = self.created_at
        self.access_count = 0
        self.last_accessed = self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "key": self.key,
            "value": json.dumps(self.value) if not isinstance(self.value, str) else self.value,
            "tier": self.tier,
            "ttl_seconds": self.ttl_seconds,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry | None:
        """Crear MemoryEntry desde un dict.

        Returns None si los datos son inválidos (en lugar de lanzar excepción).
        """
        try:
            namespace = data.get("namespace", "")
            key = data.get("key", "")
            value = data.get("value", "")
            if not namespace or not key:
                return None
            tier = data.get("tier", "permanent")
            ttl_seconds = data.get("ttl_seconds")
            tags = data.get("tags", [])
            metadata = data.get("metadata", {})
            entry = MemoryEntry(
                namespace=namespace,
                key=key,
                value=value,
                tier=tier,
                ttl_seconds=ttl_seconds,
                tags=tags,
                metadata=metadata,
            )
            entry.created_at = _parse_dt(data.get("created_at"))
            entry.updated_at = _parse_dt(data.get("updated_at"))
            return entry
        except (TypeError, KeyError, ValueError) as e:
            logger.debug("Invalid memory entry data: %s", e)
            return None


# ── UnifiedMemoryStore ────────────────────────────────────────────


class UnifiedMemoryStore:
    """Unified namespaced memory store with persistence in SQLite."""

    def __init__(self, namespace: str | None = None):
        self._namespace = namespace  # None = global / all namespaces
        self._cache: dict[str, MemoryEntry] = {}  # key = f"{namespace}:{key}"
        self._initialized = False
        self._load_warnings = 0

    def _make_key(self, namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def _is_loaded(self) -> bool:
        return self._initialized

    def _increment_load_warning(self) -> int:
        self._load_warnings += 1
        return self._load_warnings

    def _should_suppress_warning(self, key: str) -> bool:
        """Determinar si debemos suprimir el warning para este key."""
        if key not in _warning_keys:
            _warning_keys.add(key)
            return False
        return True

    def initialize(self) -> None:
        """Load permanent memories from database."""
        if self._initialized:
            return
        create_engine("sqlite:///./database/catseye.db")
        session = SessionLocal(bind=create_engine("sqlite:///./database/catseye.db"))
        try:
            from sqlalchemy import MetaData, Table

            metadata = MetaData()
            memory_table = Table(
                "memory_records", metadata, autoload_with=create_engine("sqlite:///./database/catseye.db")
            )
            records = session.query(memory_table).all()
            loaded = 0
            skipped = 0
            for record in records:
                try:
                    details = json.loads(record.details) if record.details else {}
                    entry = MemoryEntry.from_dict(details)
                    if entry is None:
                        skipped += 1
                        continue
                    cache_key = f"{entry.namespace}:{entry.key}"
                    self._cache[cache_key] = entry
                    loaded += 1
                except Exception as e:
                    skipped += 1
                    # Control de warnings: mostrar los primeros MAX_LOAD_WARNINGS
                    # y luego silenciarlos
                    self._load_warnings += 1
                    if self._load_warnings <= MAX_LOAD_WARNINGS:
                        logger.warning(
                            "Failed to load memory record %s: %s",
                            record.key,
                            e,
                        )
                    # Marcar este key para suprimir warnings futuros
                    _warning_keys.add(f"memory_load:{record.key}")
            self._initialized = True
            logger.info(
                "Memory store initialized with %d entries (skipped %d)",
                loaded,
                skipped,
            )
        finally:
            session.close()

    def _is_expired(self, entry: MemoryEntry) -> bool:
        """Temporary entries expire after ttl_seconds."""
        if entry.tier != MemoryTier.TEMPORARY or entry.ttl_seconds is None:
            return False
        updated = entry.updated_at
        if isinstance(updated, str):
            try:
                updated = datetime.fromisoformat(updated)
            except (TypeError, ValueError):
                return False
        try:
            age = (datetime.now(UTC) - updated).total_seconds()
        except (TypeError, ValueError):
            return False
        return age > entry.ttl_seconds

    @staticmethod
    def _deserialize_value(entry: MemoryEntry) -> None:
        """Restore dict/list values serialized as JSON strings by to_dict()."""
        if isinstance(entry.value, str):
            stripped = entry.value.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                with contextlib.suppress(TypeError, ValueError):
                    entry.value = json.loads(stripped)

    @staticmethod
    def _namespace_value(namespace: MemoryNamespace | str) -> str:
        return namespace.value if isinstance(namespace, MemoryNamespace) else str(namespace)

    def set(
        self,
        namespace: MemoryNamespace | str,
        key: str,
        value: Any,
        tier: str = "permanent",
        ttl_seconds: int | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a value (upsert) in memory_records, keyed by namespace + key."""
        ns = self._namespace_value(namespace)
        entry = MemoryEntry(
            namespace=ns,
            key=key,
            value=value,
            tier=tier,
            ttl_seconds=ttl_seconds,
            tags=tags,
            metadata=metadata,
        )
        details = json.dumps(entry.to_dict(), default=str)
        try:
            from database.db import SessionLocal
            from database.models import MemoryRecord

            session = SessionLocal()
            try:
                record: Any = session.query(MemoryRecord).filter_by(category=ns, key=key).first()
                if record is None:
                    record = MemoryRecord(category=ns, key=key, details=details)
                    session.add(record)
                else:
                    record.details = details
                session.commit()
            finally:
                session.close()
        except Exception:
            logger.warning("memory set failed for %s:%s", ns, key)
        self._cache[f"{ns}:{key}"] = entry

    def get(self, namespace: MemoryNamespace | str, key: str) -> Any:
        """Return the stored value (deserialized) or None."""
        ns = self._namespace_value(namespace)
        cached = self._cache.get(f"{ns}:{key}")
        if cached is not None and not self._is_expired(cached):
            self._deserialize_value(cached)
            return cached.value
        try:
            from database.db import SessionLocal
            from database.models import MemoryRecord

            session = SessionLocal()
            try:
                record: Any = session.query(MemoryRecord).filter_by(category=ns, key=key).first()
            finally:
                session.close()
            if record is None or not record.details:
                return None
            entry = MemoryEntry.from_dict(json.loads(record.details))
            if entry is None or self._is_expired(entry):
                return None
            self._deserialize_value(entry)
            self._cache[f"{ns}:{key}"] = entry
            return entry.value
        except Exception:
            return None

    def search(
        self,
        query: str = "",
        namespaces: list[MemoryNamespace | str] | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Search entries by substring in key/value, optionally filtered by namespace."""
        ns_values = [self._namespace_value(ns) for ns in namespaces] if namespaces else None
        results: list[MemoryEntry] = []
        try:
            from database.db import SessionLocal
            from database.models import MemoryRecord

            session = SessionLocal()
            try:
                record_query = session.query(MemoryRecord)
                if ns_values:
                    record_query = record_query.filter(MemoryRecord.category.in_(ns_values))
                records: list[Any] = record_query.limit(limit * 4).all()
                for record in records:
                    if not record.details:
                        continue
                    entry = MemoryEntry.from_dict(json.loads(record.details))
                    if entry is None or self._is_expired(entry):
                        continue
                    if ns_values and entry.namespace not in ns_values:
                        continue
                    if query:
                        haystack = f"{entry.key} {entry.value} {entry.namespace} {' '.join(entry.tags)}".lower()
                        if query.lower() not in haystack:
                            continue
                    self._deserialize_value(entry)
                    results.append(entry)
                    if len(results) >= limit:
                        break
            finally:
                session.close()
        except Exception:
            logger.warning("memory search failed")
            return []
        return results

    def get_stats(self) -> dict[str, Any]:
        """Aggregate stats across namespaces."""
        try:
            from database.db import SessionLocal
            from database.models import MemoryRecord

            session = SessionLocal()
            try:
                rows: list[Any] = session.query(MemoryRecord).all()
            finally:
                session.close()
            namespaces: dict[str, int] = {}
            expired = 0
            for record in rows:
                namespaces[record.category] = namespaces.get(record.category, 0) + 1
                if not record.details:
                    continue
                entry = MemoryEntry.from_dict(json.loads(record.details))
                if entry is not None and self._is_expired(entry):
                    expired += 1
            return {"total": len(rows), "namespaces": namespaces, "expired_entries": expired}
        except Exception:
            return {"total": 0, "namespaces": {}, "expired_entries": 0}


# Memory namespaces for UnifiedMemoryStore


# ── Global singleton helper ──────────────────────────────────────────────
_Singleton: UnifiedMemoryStore | None = None


def get_memory_store() -> UnifiedMemoryStore:
    global _Singleton
    if _Singleton is None:
        _Singleton = UnifiedMemoryStore()
    return _Singleton


class MemoryNamespace(StrEnum):
    """Namespaces for memory store organization."""

    CONVERSATION = "conversation"
    PREFERENCES = "preferences"
    STRATEGY = "strategy"
    SYSTEM_HEALTH = "system_health"
    TASK_CONTEXT = "task_context"
    TASK_OUTCOMES = "task_outcomes"
    OPPORTUNITIES = "opportunities"
    RESEARCH = "research"
    EVIDENCE = "evidence"
    SUCCESS_FRAMEWORK = "success_framework"
