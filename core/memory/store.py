"""Unified Memory Store — namespaced, taggable, with priority and expiration."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_

from core.database.manager import get_db_manager
from core.memory.models import Base, MemoryEntry

logger = logging.getLogger("orion.core.memory")

DB_ID = "memory"


def _ensure_db() -> None:
    mgr = get_db_manager()
    if DB_ID not in mgr.list_databases():
        mgr.register(DB_ID, "memory.db")
    mgr.run_migrations(DB_ID, Base)


class UnifiedMemoryStore:
    """Namespaced, persistent memory for all ORION subsystems.

    Supports:
    - Namespace isolation (global, cateye, atlas, copilot, etc.)
    - Tags for filtering
    - Priority scoring
    - Optional expiration (auto-cleanup on query)
    - Text search across content + metadata
    - Embedding storage for future semantic search
    """

    # ── Write ───────────────────────────────────────────────

    def store(
        self,
        namespace: str,
        key: str,
        content: str = "",
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        priority: float = 0.0,
        expires_at: datetime | None = None,
        embedding: list[float] | None = None,
    ) -> int:
        """Store a memory entry. Returns the entry ID.

        If an entry with the same namespace + key exists, it is updated.
        """
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            existing = db.query(MemoryEntry).filter(MemoryEntry.namespace == namespace, MemoryEntry.key == key).first()
            if existing:
                existing.content = content
                existing.metadata_json = json.dumps(metadata or {})
                existing.tags = json.dumps(tags or [])
                existing.priority = priority
                existing.expires_at = expires_at
                if embedding is not None:
                    existing.embedding = json.dumps(embedding)
                existing.updated_at = datetime.now(UTC)
                entry_id = existing.id
            else:
                entry = MemoryEntry(
                    namespace=namespace,
                    key=key,
                    content=content,
                    metadata_json=json.dumps(metadata or {}),
                    tags=json.dumps(tags or []),
                    priority=priority,
                    expires_at=expires_at,
                    embedding=json.dumps(embedding) if embedding is not None else None,
                )
                db.add(entry)
                db.flush()
                entry_id = entry.id
            db.commit()
            logger.debug("Memory stored: %s/%s (id=%d)", namespace, key, entry_id)
            return entry_id
        except Exception as exc:
            db.rollback()
            logger.error("Failed to store memory: %s", exc)
            raise
        finally:
            db.close()

    def delete(self, namespace: str, key: str) -> bool:
        """Delete a memory entry by namespace + key."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            count = db.query(MemoryEntry).filter(MemoryEntry.namespace == namespace, MemoryEntry.key == key).delete()
            db.commit()
            return count > 0
        except Exception as exc:
            db.rollback()
            logger.error("Failed to delete memory: %s", exc)
            return False
        finally:
            db.close()

    # ── Read ─────────────────────────────────────────────────

    def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        """Get a single memory entry by namespace + key."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            entry = db.query(MemoryEntry).filter(MemoryEntry.namespace == namespace, MemoryEntry.key == key).first()
            if entry is None:
                return None
            self._prune_expired(db)
            return entry.to_dict()
        finally:
            db.close()

    def query(
        self,
        namespace: str | None = None,
        tags: list[str] | None = None,
        search: str = "",
        min_priority: float = 0.0,
        limit: int = 50,
        include_expired: bool = False,
    ) -> list[dict[str, Any]]:
        """Query memory entries with optional filters."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            q = db.query(MemoryEntry)

            if namespace:
                q = q.filter(MemoryEntry.namespace == namespace)

            if tags:
                for tag in tags:
                    q = q.filter(MemoryEntry.tags.contains(tag))

            if search:
                term = f"%{search}%"
                q = q.filter(
                    or_(
                        MemoryEntry.content.ilike(term),
                        MemoryEntry.key.ilike(term),
                    )
                )

            if min_priority > 0:
                q = q.filter(MemoryEntry.priority >= min_priority)

            if not include_expired:
                now = datetime.now(UTC)
                q = q.filter(or_(MemoryEntry.expires_at.is_(None), MemoryEntry.expires_at > now))

            q = q.order_by(MemoryEntry.priority.desc(), MemoryEntry.created_at.desc())
            q = q.limit(limit)

            if not include_expired:
                self._prune_expired(db)
            return [entry.to_dict() for entry in q.all()]
        finally:
            db.close()

    def list_namespaces(self) -> list[str]:
        """Return all namespaces that have entries."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            rows = db.query(MemoryEntry.namespace).distinct().all()
            return sorted(r[0] for r in rows)
        finally:
            db.close()

    def count(self, namespace: str | None = None) -> int:
        """Count entries, optionally filtered by namespace."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            q = db.query(MemoryEntry)
            if namespace:
                q = q.filter(MemoryEntry.namespace == namespace)
            return q.count()
        finally:
            db.close()

    # ── Embeddings (future) ─────────────────────────────────

    def store_embedding(self, entry_id: int, embedding: list[float]) -> bool:
        """Store or update an embedding vector for an existing entry."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            entry = db.query(MemoryEntry).filter(MemoryEntry.id == entry_id).first()
            if entry is None:
                return False
            entry.embedding = json.dumps(embedding)
            db.commit()
            return True
        except Exception as exc:
            db.rollback()
            logger.error("Failed to store embedding: %s", exc)
            return False
        finally:
            db.close()

    def get_without_embeddings(self, namespace: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Get entries that have no embedding yet (for batch processing)."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            q = db.query(MemoryEntry).filter(MemoryEntry.embedding.is_(None))
            if namespace:
                q = q.filter(MemoryEntry.namespace == namespace)
            q = q.limit(limit)
            return [entry.to_dict() for entry in q.all()]
        finally:
            db.close()

    # ── Maintenance ──────────────────────────────────────────

    def prune_expired(self) -> int:
        """Delete all expired entries. Returns count deleted."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            now = datetime.now(UTC)
            count = (
                db.query(MemoryEntry).filter(MemoryEntry.expires_at.isnot(None), MemoryEntry.expires_at <= now).delete()
            )
            db.commit()
            if count:
                logger.info("Pruned %d expired memory entries", count)
            return count
        except Exception as exc:
            db.rollback()
            logger.error("Failed to prune expired memory: %s", exc)
            return 0
        finally:
            db.close()

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics."""
        _ensure_db()
        db = get_db_manager().get_session(DB_ID)
        try:
            total = db.query(MemoryEntry).count()
            namespaces = db.query(MemoryEntry.namespace).distinct().count()
            now = datetime.now(UTC)
            expired_rows = (
                db.query(MemoryEntry).filter(MemoryEntry.expires_at.isnot(None), MemoryEntry.expires_at <= now).count()
            )
            return {
                "total_entries": total,
                "namespaces": namespaces,
                "expired_entries": expired_rows,
            }
        finally:
            db.close()

    @staticmethod
    def _prune_expired(db: Any) -> None:
        now = datetime.now(UTC)
        db.query(MemoryEntry).filter(MemoryEntry.expires_at.isnot(None), MemoryEntry.expires_at <= now).delete()
        db.commit()


_Singleton: UnifiedMemoryStore | None = None


def get_memory_store() -> UnifiedMemoryStore:
    global _Singleton
    if _Singleton is None:
        _Singleton = UnifiedMemoryStore()
    return _Singleton
