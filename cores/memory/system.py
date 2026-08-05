"""
OWNEX Memory System — Persistent, structured memory with learning capabilities.

What it remembers:
- Conversation history (short-term + long-term)
- User preferences and patterns
- Task outcomes and learnings
- Tool usage patterns
- Opportunity evaluations
- System health snapshots

How it stores:
- SQLite (MemoryRecord) for persistence
- In-memory cache for hot data
- Namespaced categories for organization
- Embeddings for semantic search (future)

What's permanent:
- User preferences
- Learned patterns
- Task outcomes
- Tool configurations
- Opportunity evaluations

What's temporary:
- Current conversation context
- Active task state
- Session metadata
- Cache entries

How it learns:
- Feedback loops from task outcomes
- Preference inference from corrections
- Pattern detection in tool usage
- Success rate tracking per tool/category
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from database import db, models

logger = logging.getLogger("ownex.memory")


class MemoryNamespace:
    """Namespaces for organizing memory."""

    CONVERSATION = "conversation"
    PREFERENCES = "preferences"
    LEARNINGS = "learnings"
    TOOL_USAGE = "tool_usage"
    OPPORTUNITIES = "opportunities"
    TASK_OUTCOMES = "task_outcomes"
    SYSTEM_HEALTH = "system_health"
    USER_PATTERNS = "user_patterns"


class MemoryTier:
    """Memory tiers: permanent vs temporary."""

    PERMANENT = "permanent"  # Survives restarts, never auto-expires
    TEMPORARY = "temporary"  # Auto-expires, session-scoped
    CACHED = "cached"  # Short TTL, rebuildable


class MemoryEntry:
    """Single memory entry with metadata."""

    def __init__(
        self,
        namespace: str,
        key: str,
        value: Any,
        tier: str = MemoryTier.PERMANENT,
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

    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (datetime.now(UTC) - self.created_at).total_seconds() > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "key": self.key,
            "value": self.value,
            "tier": self.tier,
            "ttl_seconds": self.ttl_seconds,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEntry:
        entry = cls(
            namespace=data["namespace"],
            key=data["key"],
            value=data["value"],
            tier=data.get("tier", MemoryTier.PERMANENT),
            ttl_seconds=data.get("ttl_seconds"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
        entry.created_at = datetime.fromisoformat(data["created_at"])
        entry.updated_at = datetime.fromisoformat(data["updated_at"])
        entry.access_count = data.get("access_count", 0)
        entry.last_accessed = datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None
        return entry


class MemoryStore:
    """Main memory store with persistence and caching."""

    def __init__(self):
        self._cache: dict[str, MemoryEntry] = {}  # key = f"{namespace}:{key}"
        self._initialized = False

    def _make_key(self, namespace: str, key: str) -> str:
        return f"{namespace}:{key}"

    def initialize(self) -> None:
        """Load permanent memories from database."""
        if self._initialized:
            return
        session = db.SessionLocal()
        try:
            records = session.query(models.MemoryRecord).all()
            for record in records:
                try:
                    details = json.loads(record.details) if record.details else {}
                    entry = MemoryEntry.from_dict(details)
                    cache_key = self._make_key(entry.namespace, entry.key)
                    self._cache[cache_key] = entry
                except Exception as e:
                    logger.warning("Failed to load memory record %s: %s", record.key, e)
            self._initialized = True
            logger.info("Memory store initialized with %d entries", len(self._cache))
        finally:
            session.close()

    def _persist(self, entry: MemoryEntry) -> None:
        """Persist entry to database."""
        if entry.tier == MemoryTier.CACHED:
            return
        session = db.SessionLocal()
        try:
            # Check if exists
            existing = (
                session.query(models.MemoryRecord)
                .filter(
                    models.MemoryRecord.category == entry.namespace,
                    models.MemoryRecord.key == entry.key,
                )
                .first()
            )
            if existing:
                existing.details = json.dumps(entry.to_dict())
            else:
                record = models.MemoryRecord(
                    category=entry.namespace,
                    key=entry.key,
                    details=json.dumps(entry.to_dict()),
                )
                session.add(record)
            session.commit()
        except Exception as e:
            logger.error("Failed to persist memory %s:%s: %s", entry.namespace, entry.key, e)
            session.rollback()
        finally:
            session.close()

    def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        tier: str = MemoryTier.PERMANENT,
        ttl_seconds: int | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a memory entry."""
        entry = MemoryEntry(
            namespace=namespace,
            key=key,
            value=value,
            tier=tier,
            ttl_seconds=ttl_seconds,
            tags=tags,
            metadata=metadata,
        )
        cache_key = self._make_key(namespace, key)
        self._cache[cache_key] = entry
        self._persist(entry)
        return entry

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        """Retrieve a memory entry."""
        cache_key = self._make_key(namespace, key)
        entry = self._cache.get(cache_key)
        if entry is None:
            return default
        if entry.is_expired():
            self.delete(namespace, key)
            return default
        entry.access_count += 1
        entry.last_accessed = datetime.now(UTC)
        return entry.value

    def get_entry(self, namespace: str, key: str) -> MemoryEntry | None:
        """Get full entry with metadata."""
        cache_key = self._make_key(namespace, key)
        entry = self._cache.get(cache_key)
        if entry and entry.is_expired():
            self.delete(namespace, key)
            return None
        return entry

    def delete(self, namespace: str, key: str) -> bool:
        """Delete a memory entry."""
        cache_key = self._make_key(namespace, key)
        if cache_key in self._cache:
            del self._cache[cache_key]

        if namespace != MemoryNamespace.CONVERSATION:  # Don't delete conversation from DB
            session = db.SessionLocal()
            try:
                session.query(models.MemoryRecord).filter(
                    models.MemoryRecord.category == namespace,
                    models.MemoryRecord.key == key,
                ).delete()
                session.commit()
                return True
            except Exception as e:
                logger.error("Failed to delete memory %s:%s: %s", namespace, key, e)
                session.rollback()
                return False
            finally:
                session.close()
        return True

    def list(self, namespace: str, tag: str | None = None) -> list[MemoryEntry]:
        """List entries in namespace, optionally filtered by tag."""
        results = []
        prefix = f"{namespace}:"
        for key, entry in self._cache.items():
            if key.startswith(prefix):
                if tag is None or tag in entry.tags:
                    results.append(entry)
        return results

    def search(self, query: str, namespaces: list[str] | None = None) -> list[MemoryEntry]:
        """Simple text search in memory values."""
        results = []
        query_lower = query.lower()
        for entry in self._cache.values():
            if namespaces and entry.namespace not in namespaces:
                continue
            # Search in value (if string) and tags
            value_str = json.dumps(entry.value).lower() if not isinstance(entry.value, str) else entry.value.lower()
            if query_lower in value_str or any(query_lower in tag.lower() for tag in entry.tags):
                results.append(entry)
        return results

    def cleanup_expired(self) -> int:
        """Remove expired temporary entries."""
        removed = 0
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        for key in expired_keys:
            namespace, entry_key = key.split(":", 1)
            self.delete(namespace, entry_key)
            removed += 1
        return removed

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        stats = {"total": len(self._cache), "by_namespace": {}, "by_tier": {}}
        for entry in self._cache.values():
            stats["by_namespace"][entry.namespace] = stats["by_namespace"].get(entry.namespace, 0) + 1
            stats["by_tier"][entry.tier] = stats["by_tier"].get(entry.tier, 0) + 1
        return stats


class LearningEngine:
    """Learns from user interactions and task outcomes."""

    def __init__(self, memory: MemoryStore):
        self.memory = memory

    def record_preference(self, category: str, preference: dict[str, Any]) -> None:
        """Record or update user preference."""
        existing = self.memory.get(MemoryNamespace.PREFERENCES, category, {})
        existing.update(preference)
        self.memory.set(MemoryNamespace.PREFERENCES, category, existing, tier=MemoryTier.PERMANENT)

    def get_preference(self, category: str) -> dict[str, Any]:
        """Get user preference."""
        return self.memory.get(MemoryNamespace.PREFERENCES, category, {})

    def record_tool_usage(
        self, tool_name: str, success: bool, duration_ms: float, context: dict[str, Any] | None = None
    ) -> None:
        """Record tool usage for learning."""
        key = f"tool_{tool_name}"
        stats = self.memory.get(
            MemoryNamespace.TOOL_USAGE,
            key,
            {
                "total_uses": 0,
                "successful_uses": 0,
                "total_duration_ms": 0.0,
                "last_used": None,
                "contexts": [],
            },
        )
        stats["total_uses"] += 1
        if success:
            stats["successful_uses"] += 1
        stats["total_duration_ms"] += duration_ms
        stats["last_used"] = datetime.now(UTC).isoformat()
        if context:
            stats["contexts"].append(context)
            # Keep only last 10 contexts
            stats["contexts"] = stats["contexts"][-10:]
        self.memory.set(MemoryNamespace.TOOL_USAGE, key, stats, tier=MemoryTier.PERMANENT)

    def get_tool_stats(self, tool_name: str) -> dict[str, Any]:
        """Get tool usage statistics."""
        return self.memory.get(MemoryNamespace.TOOL_USAGE, f"tool_{tool_name}", {})

    def record_task_outcome(
        self,
        task_type: str,
        success: bool,
        duration_ms: float,
        tools_used: list[str],
        learnings: list[str] | None = None,
    ) -> None:
        """Record task outcome for learning patterns."""
        key = f"task_{task_type}"
        stats = self.memory.get(
            MemoryNamespace.TASK_OUTCOMES,
            key,
            {
                "total": 0,
                "successful": 0,
                "avg_duration_ms": 0.0,
                "tools_frequency": {},
                "learnings": [],
            },
        )
        stats["total"] += 1
        if success:
            stats["successful"] += 1
        # Update rolling average
        stats["avg_duration_ms"] = (stats["avg_duration_ms"] * (stats["total"] - 1) + duration_ms) / stats["total"]
        for tool in tools_used:
            stats["tools_frequency"][tool] = stats["tools_frequency"].get(tool, 0) + 1
        if learnings:
            stats["learnings"].extend(learnings)
            stats["learnings"] = stats["learnings"][-20:]  # Keep last 20
        self.memory.set(MemoryNamespace.TASK_OUTCOMES, key, stats, tier=MemoryTier.PERMANENT)

    def record_opportunity_evaluation(self, opportunity_id: str, evaluation: dict[str, Any]) -> None:
        """Record opportunity evaluation."""
        self.memory.set(
            MemoryNamespace.OPPORTUNITIES,
            opportunity_id,
            evaluation,
            tier=MemoryTier.PERMANENT,
            tags=["evaluation", "opportunity"],
        )

    def infer_user_patterns(self) -> dict[str, Any]:
        """Infer patterns from accumulated data."""
        patterns = {}

        # Tool preferences
        tool_stats = {}
        for entry in self.memory.list(MemoryNamespace.TOOL_USAGE):
            tool_name = entry.key.replace("tool_", "")
            stats = entry.value
            if stats.get("total_uses", 0) > 0:
                success_rate = stats["successful_uses"] / stats["total_uses"]
                tool_stats[tool_name] = {
                    "uses": stats["total_uses"],
                    "success_rate": success_rate,
                    "avg_duration_ms": stats["total_duration_ms"] / stats["total_uses"],
                }
        patterns["tool_preferences"] = tool_stats

        # Task patterns
        task_stats = {}
        for entry in self.memory.list(MemoryNamespace.TASK_OUTCOMES):
            task_type = entry.key.replace("task_", "")
            stats = entry.value
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


# Global memory instance
_memory_store: MemoryStore | None = None
_learning_engine: LearningEngine | None = None


def get_memory_store() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
        _memory_store.initialize()
    return _memory_store


def get_learning_engine() -> LearningEngine:
    global _learning_engine
    if _learning_engine is None:
        _learning_engine = LearningEngine(get_memory_store())
    return _learning_engine


# Convenience functions
def remember(namespace: str, key: str, value: Any, **kwargs) -> None:
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
    task_type: str, success: bool, duration_ms: float, tools: list[str], learnings: list[str] | None = None
) -> None:
    get_learning_engine().record_task_outcome(task_type, success, duration_ms, tools, learnings)


def get_user_patterns() -> dict[str, Any]:
    return get_learning_engine().infer_user_patterns()
