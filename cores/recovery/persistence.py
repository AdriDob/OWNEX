"""Recovery persistence — SQLite-backed history of failures, recovery actions, and learning state.

INTEGRATED WITH VERSION BACKUP SYSTEM:
- Shared SQLite storage for recovery history and version backups
- Version backup metadata stored in recovery_history.db
- Unified local storage for both systems
"""

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
            # ⚡ INTEGRATED WITH VERSION BACKUP SYSTEM
            # Add version backup tables to shared storage
            conn.execute("""
                CREATE TABLE IF NOT EXISTS version_backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    git_commit TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'backup',
                    backup_path TEXT NOT NULL,
                    manifest TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    notes TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_version_backups_created_at
                ON version_backups(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_version_backups_version
                ON version_backups(version)
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

    # ⚡ INTEGRATED WITH VERSION BACKUP SYSTEM
    # Version backup methods using shared SQLite storage

    def save_version_backup(
        self,
        version: str,
        git_commit: str,
        backup_path: str,
        manifest: dict[str, Any],
        checksum: str,
        size: int,
        notes: str = "",
        state: str = "backup",
    ) -> None:
        """Save version backup metadata to shared storage."""
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT INTO version_backups
                   (version, git_commit, created_at, state, backup_path, manifest, checksum, size, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    version,
                    git_commit,
                    datetime.now(UTC).isoformat(),
                    state,
                    backup_path,
                    json.dumps(manifest),
                    checksum,
                    size,
                    notes[:500],
                ),
            )
            conn.commit()
            logger.info(f"[RECOVERY STORE] Saved version backup: {version} at {backup_path}")

    def get_version_backups(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all version backups from shared storage."""
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM version_backups ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d["manifest"] = json.loads(d["manifest"])
                result.append(d)
            return result

    def get_version_backup(self, version: str | None = None, git_commit: str | None = None) -> dict[str, Any] | None:
        """Get a specific version backup from shared storage."""
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            if version:
                row = conn.execute(
                    "SELECT * FROM version_backups WHERE version = ? ORDER BY created_at DESC LIMIT 1", (version,)
                ).fetchone()
            elif git_commit:
                row = conn.execute(
                    "SELECT * FROM version_backups WHERE git_commit = ? ORDER BY created_at DESC LIMIT 1", (git_commit,)
                ).fetchone()
            else:
                return None

            if row:
                d = dict(row)
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    d["manifest"] = json.loads(d["manifest"])
                return d
            return None

    def update_version_backup_state(self, version: str, state: str) -> None:
        """Update version backup state in shared storage."""
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "UPDATE version_backups SET state = ? WHERE version = ?",
                (state, version),
            )
            conn.commit()
            logger.info(f"[RECOVERY STORE] Updated version backup state: {version} -> {state}")

    def delete_version_backup(self, version: str) -> None:
        """Delete version backup from shared storage."""
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM version_backups WHERE version = ?", (version,))
            conn.commit()
            logger.info(f"[RECOVERY STORE] Deleted version backup: {version}")

    def cleanup_old_version_backups(self, max_count: int = 10) -> int:
        """Clean up old version backups, keeping only max_count."""
        with self._lock, sqlite3.connect(self._db_path) as conn:
            # Get total count
            count_result = conn.execute("SELECT COUNT(*) as count FROM version_backups").fetchone()
            total_count = count_result[0] if count_result else 0

            if total_count <= max_count:
                return 0

            # Delete oldest backups beyond max_count
            to_delete = total_count - max_count
            conn.execute(
                f"DELETE FROM version_backups WHERE id IN (SELECT id FROM version_backups ORDER BY created_at ASC LIMIT {to_delete})"
            )
            conn.commit()
            logger.info(f"[RECOVERY STORE] Cleaned up {to_delete} old version backups")
            return to_delete

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
    """Reset the singleton store (test isolation).

    Also removes the backing SQLite file so the next store starts fresh.
    Only used by tests.
    """
    global _store_instance
    if _store_instance is not None:
        db_path = _store_instance._db_path
        _store_instance = None
        for suffix in ("", "-wal", "-shm"):
            with contextlib.suppress(FileNotFoundError):
                Path(db_path + suffix).unlink()
    else:
        _store_instance = None
