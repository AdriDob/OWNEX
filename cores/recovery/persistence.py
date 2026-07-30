"""Recovery persistence — SQLite-backed history of failures, recovery actions, and learning state."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("cateye.recovery.persistence")


class RecoveryStore:
    """Thread-safe SQLite store for recovery history."""

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_dir = Path(os.getenv("CATEYE_DATA_DIR", Path.home() / ".orion" / "data"))
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "recovery_history.db")
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recovery_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    component TEXT NOT NULL,
                    failure_type TEXT NOT NULL,
                    recovery_action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT DEFAULT '',
                    duration_ms REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS circuit_breaker_state (
                    component TEXT PRIMARY KEY,
                    state TEXT NOT NULL DEFAULT 'closed',
                    failure_count INTEGER DEFAULT 0,
                    last_failure TEXT,
                    opened_at TEXT,
                    cooldown_until TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_state (
                    key TEXT PRIMARY KEY,
                    value REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)
            conn.commit()

    def record_recovery(
        self,
        component: str,
        failure_type: str,
        recovery_action: str,
        status: str,
        details: str = "",
        duration_ms: float = 0.0,
    ) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO recovery_events
                   (timestamp, component, failure_type, recovery_action, status, details, duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(UTC).isoformat(),
                    component,
                    failure_type,
                    recovery_action,
                    status,
                    details[:500],
                    duration_ms,
                ),
            )
            conn.commit()

    def get_recovery_history(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM recovery_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def update_circuit_breaker(
        self,
        component: str,
        state: str,
        failure_count: int,
        opened_at: str | None = None,
        cooldown_until: str | None = None,
    ) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO circuit_breaker_state
                   (component, state, failure_count, last_failure, opened_at, cooldown_until)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (component, state, failure_count, datetime.now(UTC).isoformat(), opened_at, cooldown_until),
            )
            conn.commit()

    def get_circuit_breaker(self, component: str) -> dict[str, Any] | None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM circuit_breaker_state WHERE component = ?", (component,)).fetchone()
            return dict(row) if row else None

    def update_learning_state(self, key: str, value: float) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO learning_state (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, value, datetime.now(UTC).isoformat()),
            )
            conn.commit()

    def get_learning_state(self, key: str) -> float | None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT value FROM learning_state WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def get_all_learning_state(self) -> dict[str, float]:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT key, value FROM learning_state").fetchall()
            return {r["key"]: r["value"] for r in rows}

    def save_health_snapshot(self, source: str, data: dict) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO health_snapshots (timestamp, source, data)
                   VALUES (?, ?, ?)""",
                (datetime.now(UTC).isoformat(), source, json.dumps(data)),
            )
            conn.commit()

    def get_health_snapshots(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM health_snapshots ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d["data"] = json.loads(d["data"])
                result.append(d)
            return result

    def close(self) -> None:
        pass


_store_instance: RecoveryStore | None = None
_store_lock = threading.Lock()


def get_recovery_store() -> RecoveryStore:
    global _store_instance
    if _store_instance is None:
        with _store_lock:
            if _store_instance is None:
                _store_instance = RecoveryStore()
    return _store_instance


def reset_recovery_store() -> None:
    global _store_instance
    _store_instance = None
