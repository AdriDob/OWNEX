"""Event Store — persistent SQLite-backed event store with replay capability.

Stores every event envelope with correlation_id for full traceability.
Supports replay by time range, correlation_id, or event type.

Schema:

    event_store:
        id              INTEGER PRIMARY KEY
        correlation_id  TEXT NOT NULL (indexed)
        event_type      TEXT NOT NULL (indexed)
        source          TEXT NOT NULL
        payload         TEXT (JSON)
        timestamp       REAL NOT NULL (indexed)
        duration_ms     REAL (nullable)
        user            TEXT (nullable)

Usage:

    from cores.events.store import get_event_store

    store = get_event_store()
    store.store(envelope)

    # Replay all events for a correlation ID
    events = store.get_by_correlation_id("abc123")

    # Replay events in a time window
    events = store.replay(from_ts=1000.0, to_ts=2000.0)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any

from cores.events.types import EventEnvelope

logger = logging.getLogger("orion.core.events.store")

DATA_DIR = Path.home() / ".orion" / "database"
STORE_PATH = DATA_DIR / "event_store.db"


class EventStore:
    """Persistent event store with SQLite backend.

    Thread-safe via per-write locking.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else STORE_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    # ── Public API ──────────────────────────────────────────────

    def store(self, envelope: EventEnvelope) -> int:
        """Persist an event envelope. Returns row id."""
        with self._lock:
            return self._insert(envelope)

    def store_dict(
        self,
        event_type: str,
        correlation_id: str,
        source: str,
        payload: dict[str, Any] | None = None,
        duration_ms: float | None = None,
        user: str | None = None,
    ) -> int:
        """Create and store an envelope from raw fields. Returns row id."""
        envelope = EventEnvelope.create(
            event_type=event_type,
            correlation_id=correlation_id,
            source=source,
            payload=payload,
            duration_ms=duration_ms,
            user=user,
        )
        return self.store(envelope)

    def get_by_correlation_id(self, correlation_id: str) -> list[dict[str, Any]]:
        """Return all events for a given correlation ID (chronological)."""
        with self._lock:
            rows = self._fetchall(
                "SELECT * FROM event_store WHERE correlation_id = ? ORDER BY timestamp ASC",
                (correlation_id,),
            )
        return [self._row_to_dict(r) for r in rows]

    def get_by_event_type(self, event_type: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent events of a given type."""
        with self._lock:
            rows = self._fetchall(
                "SELECT * FROM event_store WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
                (event_type, limit),
            )
        return [self._row_to_dict(r) for r in rows]

    def replay(
        self, from_ts: float | None = None, to_ts: float | None = None, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Replay events in a time window (chronological)."""
        query = "SELECT * FROM event_store WHERE 1=1"
        params: list[Any] = []

        if from_ts is not None:
            query += " AND timestamp >= ?"
            params.append(from_ts)
        if to_ts is not None:
            query += " AND timestamp <= ?"
            params.append(to_ts)

        query += " ORDER BY timestamp ASC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._fetchall(query, tuple(params))
        return [self._row_to_dict(r) for r in rows]

    def search(
        self,
        event_type: str | None = None,
        source: str | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Flexible search across event fields."""
        query = "SELECT * FROM event_store WHERE 1=1"
        params: list[Any] = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if source:
            query += " AND source = ?"
            params.append(source)
        if correlation_id:
            query += " AND correlation_id = ?"
            params.append(correlation_id)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            rows = self._fetchall(query, tuple(params))
        return [self._row_to_dict(r) for r in rows]

    def count(self, event_type: str | None = None) -> int:
        """Count events, optionally filtered by type."""
        if event_type:
            row = self._fetchone(
                "SELECT COUNT(*) as cnt FROM event_store WHERE event_type = ?",
                (event_type,),
            )
        else:
            row = self._fetchone("SELECT COUNT(*) as cnt FROM event_store")
        return row[0] if row else 0

    def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about the event store."""
        total = self.count()
        with self._lock:
            by_type = self._fetchall(
                "SELECT event_type, COUNT(*) as cnt FROM event_store GROUP BY event_type ORDER BY cnt DESC LIMIT 20"
            )
            by_source = self._fetchall(
                "SELECT source, COUNT(*) as cnt FROM event_store GROUP BY source ORDER BY cnt DESC LIMIT 10"
            )
            recent = self._fetchall(
                "SELECT event_type, correlation_id, timestamp FROM event_store ORDER BY timestamp DESC LIMIT 5"
            )
        return {
            "total_events": total,
            "by_type": {row[0]: row[1] for row in by_type},
            "by_source": {row[0]: row[1] for row in by_source},
            "recent": [{"event_type": r[0], "correlation_id": r[1], "timestamp": r[2]} for r in recent],
        }

    def get_journal_entries(self, execution_id: str) -> list[dict[str, Any]]:
        """Return journal entries for an execution (JSON payload extraction)."""
        with self._lock:
            rows = self._fetchall(
                """SELECT * FROM event_store
                   WHERE event_type = 'execution:journal:entry'
                   AND json_extract(payload, '$.execution_id') = ?
                   ORDER BY timestamp ASC""",
                (execution_id,),
            )
        return [self._row_to_dict(r) for r in rows]

    def prune(self, before_ts: float, vacuum: bool = False) -> int:
        """Delete events older than a timestamp. Returns number of deleted rows.

        Args:
            before_ts: Delete events with timestamp older than this.
            vacuum: If True, run VACUUM + WAL checkpoint afterward (expensive).
        """
        with self._lock:
            cur = self._execute("DELETE FROM event_store WHERE timestamp < ?", (before_ts,))
            deleted = cur.rowcount if cur else 0
            if vacuum and deleted:
                self._vacuum()
        if deleted:
            logger.info("Pruned %d events older than %s", deleted, before_ts)
        return deleted

    # ── Internal ────────────────────────────────────────────────

    def _init_db(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS event_store (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id  TEXT NOT NULL,
                    event_type      TEXT NOT NULL,
                    source          TEXT NOT NULL,
                    payload         TEXT DEFAULT '{}',
                    timestamp       REAL NOT NULL,
                    duration_ms     REAL,
                    user            TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_correlation ON event_store(correlation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_type ON event_store(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_timestamp ON event_store(timestamp)")
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _insert(self, envelope: EventEnvelope) -> int:
        conn = self._get_conn()
        try:
            cur = conn.execute(
                """INSERT INTO event_store
                   (correlation_id, event_type, source, payload, timestamp, duration_ms, user)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    envelope.correlation_id,
                    envelope.event_type,
                    envelope.source,
                    json.dumps(envelope.payload),
                    envelope.timestamp,
                    envelope.duration_ms,
                    envelope.user,
                ),
            )
            conn.commit()
            return cur.lastrowid or 0
        finally:
            conn.close()

    def _fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        conn = self._get_conn()
        try:
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()

    def _fetchone(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        conn = self._get_conn()
        try:
            return conn.execute(query, params).fetchone()
        finally:
            conn.close()

    def _execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor | None:
        conn = self._get_conn()
        try:
            cur = conn.execute(query, params)
            conn.commit()
            return cur
        finally:
            conn.close()

    def _vacuum(self) -> None:
        conn = self._get_conn()
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.execute("VACUUM")
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        try:
            d["payload"] = json.loads(d["payload"]) if isinstance(d.get("payload"), str) else d.get("payload", {})
        except (json.JSONDecodeError, TypeError):
            d["payload"] = {}
        return d


# ── Singleton ────────────────────────────────────────

_store: EventStore | None = None


def get_event_store(db_path: str | Path | None = None) -> EventStore:
    global _store
    if _store is None:
        _store = EventStore(db_path=db_path)
    return _store


def reset_event_store() -> None:
    global _store
    _store = None
