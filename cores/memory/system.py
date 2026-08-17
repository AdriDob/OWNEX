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

    def get(self, namespace: MemoryNamespace | str, key: str, default: Any = None) -> Any:
        """Return the stored value (deserialized) or default."""
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
                return default
            entry = MemoryEntry.from_dict(json.loads(record.details))
            if entry is None or self._is_expired(entry):
                return default
            self._deserialize_value(entry)
            self._cache[f"{ns}:{key}"] = entry
            return entry.value
        except Exception:
            return default

    def list(
        self,
        namespace: MemoryNamespace | str,
        tag: str | None = None,
    ) -> list[MemoryEntry]:
        """List entries in a namespace, optionally filtered by tag."""
        ns = self._namespace_value(namespace)
        results: list[MemoryEntry] = []
        try:
            from database.db import SessionLocal
            from database.models import MemoryRecord

            session = SessionLocal()
            try:
                records: list[Any] = session.query(MemoryRecord).filter_by(category=ns).all()
            finally:
                session.close()
            for record in records:
                if not record.details:
                    continue
                entry = MemoryEntry.from_dict(json.loads(record.details))
                if entry is None or self._is_expired(entry):
                    continue
                if tag and tag not in entry.tags:
                    continue
                self._deserialize_value(entry)
                results.append(entry)
        except Exception:
            logger.warning("memory list failed for %s", ns)
            return []
        return results

    def delete(self, namespace: MemoryNamespace | str, key: str) -> bool:
        """Delete an entry, returns True if it existed."""
        ns = self._namespace_value(namespace)
        self._cache.pop(f"{ns}:{key}", None)
        try:
            from database.db import SessionLocal
            from database.models import MemoryRecord

            session = SessionLocal()
            try:
                record: Any = session.query(MemoryRecord).filter_by(category=ns, key=key).first()
                if record is None:
                    return False
                session.delete(record)
                session.commit()
                return True
            finally:
                session.close()
        except Exception:
            logger.warning("memory delete failed for %s:%s", ns, key)
            return False

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
    LEARNINGS = "learnings"
    TOOL_USAGE = "tool_usage"
    USER_PATTERNS = "user_patterns"


# ── LearningEngine ──────────────────────────────────────────────────


class LearningEngine:
    """Learns from user interactions and task outcomes."""

    def __init__(self, memory: UnifiedMemoryStore):
        self.memory = memory

    def record_preference(self, category: str, preference: dict[str, Any]) -> None:
        existing = self.memory.get(MemoryNamespace.PREFERENCES, category, {})
        if isinstance(existing, dict):
            existing.update(preference)
        else:
            existing = preference
        self.memory.set(MemoryNamespace.PREFERENCES, category, existing, tier=MemoryTier.PERMANENT)

    def get_preference(self, category: str) -> dict[str, Any]:
        value = self.memory.get(MemoryNamespace.PREFERENCES, category, {})
        return value if isinstance(value, dict) else {}

    def record_tool_usage(
        self, tool_name: str, success: bool, duration_ms: float, context: dict[str, Any] | None = None
    ) -> None:
        key = f"tool_{tool_name}"
        stats = self.memory.get(MemoryNamespace.TOOL_USAGE, key, {})
        if not isinstance(stats, dict):
            stats = {}
        stats.setdefault("total_uses", 0)
        stats.setdefault("successful_uses", 0)
        stats.setdefault("total_duration_ms", 0.0)
        stats.setdefault("last_used", None)
        stats.setdefault("contexts", [])
        stats["total_uses"] += 1
        if success:
            stats["successful_uses"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["last_used"] = datetime.now(UTC).isoformat()
        if context:
            stats["contexts"].append(context)
            stats["contexts"] = stats["contexts"][-10:]
        self.memory.set(MemoryNamespace.TOOL_USAGE, key, stats, tier=MemoryTier.PERMANENT)

    def get_tool_stats(self, tool_name: str) -> dict[str, Any]:
        stats = self.memory.get(MemoryNamespace.TOOL_USAGE, f"tool_{tool_name}", {})
        return stats if isinstance(stats, dict) else {}

    def record_task_outcome(
        self,
        task_type: str,
        success: bool,
        duration_ms: float,
        tools_used: list[str],
        learnings: list[str] | None = None,
    ) -> None:
        key = f"task_{task_type}"
        stats = self.memory.get(MemoryNamespace.TASK_OUTCOMES, key, {})
        if not isinstance(stats, dict):
            stats = {}
        stats.setdefault("total", 0)
        stats.setdefault("successful", 0)
        stats.setdefault("avg_duration_ms", 0.0)
        stats.setdefault("tools_frequency", {})
        stats.setdefault("learnings", [])
        stats["total"] += 1
        if success:
            stats["successful"] += 1
        stats["avg_duration_ms"] = (stats["avg_duration_ms"] * (stats["total"] - 1) + duration_ms) / stats["total"]
        for tool in tools_used:
            stats["tools_frequency"][tool] = stats["tools_frequency"].get(tool, 0) + 1
        if learnings:
            stats["learnings"].extend(learnings)
            stats["learnings"] = stats["learnings"][-20:]
        self.memory.set(MemoryNamespace.TASK_OUTCOMES, key, stats, tier=MemoryTier.PERMANENT)

    def record_opportunity_evaluation(self, opportunity_id: str, evaluation: dict[str, Any]) -> None:
        self.memory.set(
            MemoryNamespace.OPPORTUNITIES,
            opportunity_id,
            evaluation,
            tier=MemoryTier.PERMANENT,
            tags=["evaluation", "opportunity"],
        )

    def infer_user_patterns(self) -> dict[str, Any]:
        patterns: dict[str, Any] = {}

        tool_stats: dict[str, Any] = {}
        for entry in self.memory.list(MemoryNamespace.TOOL_USAGE):
            tool_name = entry.key.replace("tool_", "")
            stats = entry.value if isinstance(entry.value, dict) else {}
            if stats.get("total_uses", 0) > 0:
                tool_stats[tool_name] = {
                    "uses": stats["total_uses"],
                    "success_rate": stats["successful_uses"] / stats["total_uses"],
                    "avg_duration_ms": stats["total_duration_ms"] / stats["total_uses"],
                }
        patterns["tool_preferences"] = tool_stats

        task_stats: dict[str, Any] = {}
        for entry in self.memory.list(MemoryNamespace.TASK_OUTCOMES):
            task_type = entry.key.replace("task_", "")
            stats = entry.value if isinstance(entry.value, dict) else {}
            if stats.get("total", 0) > 0:
                task_stats[task_type] = {
                    "total": stats["total"],
                    "success_rate": stats["successful"] / stats["total"],
                    "avg_duration_ms": stats["avg_duration_ms"],
                    "preferred_tools": sorted(
                        stats.get("tools_frequency", {}).items(), key=lambda x: x[1], reverse=True
                    )[:3],
                }
        patterns["task_patterns"] = task_stats

        return patterns


_learning_engine: LearningEngine | None = None


def get_learning_engine() -> LearningEngine:
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine(get_memory_store())
    return _learning_engine


# Convenience functions
def remember(namespace: str, key: str, value: Any, **kwargs: Any) -> None:
    get_memory_store().set(namespace, key, value, **kwargs)


def recall(namespace: str, key: str, default: Any = None) -> Any:
    return get_memory_store().get(namespace, key, default)


def forget(namespace: str, key: str) -> bool:
    return get_memory_store().delete(namespace, key)


def learn_preference(category: str, preference: dict[str, Any]) -> None:
    get_learning_engine().record_preference(category, preference)


def get_preference(category: str) -> dict[str, Any]:
    return get_learning_engine().get_preference(category)


def learn_tool_usage(tool: str, success: bool, duration_ms: float, context: dict | None = None) -> None:
    get_learning_engine().record_tool_usage(tool, success, duration_ms, context)


def learn_task_outcome(
    task_type: str, success: bool, duration_ms: float, tools_used: list[str], learnings: list[str] | None = None
) -> None:
    get_learning_engine().record_task_outcome(task_type, success, duration_ms, tools_used, learnings)


def get_user_patterns() -> dict[str, Any]:
    return get_learning_engine().infer_user_patterns()
