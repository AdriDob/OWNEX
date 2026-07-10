"""Database Manager — multi-SQLite engine pool.

Each application registers its own database path.
The Core uses ``orion.db`` for system settings, events, and scheduler state.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.interfaces import IDatabase

logger = logging.getLogger("orion.core.database")

DATA_DIR = Path(os.environ.get("CATEYE_DATA_DIR", Path.home() / ".orion"))
DB_DIR = DATA_DIR / "database"


class DatabaseManager(IDatabase):
    """Manages multiple SQLite databases, one per application."""

    def __init__(self) -> None:
        self._engines: dict[str, Engine] = {}
        self._sessionmakers: dict[str, sessionmaker] = {}
        self._bases: dict[str, type] = {}

    # ── Registration ─────────────────────────────────────────────

    def register(self, app_id: str, db_path: str) -> None:
        """Register a database for an app. Creates engine but NOT tables."""
        if app_id in self._engines:
            logger.debug("Database for %s already registered", app_id)
            return

        full_path = self._resolve_path(db_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{full_path}"

        logger.info("Registering database for %s: %s", app_id, full_path)

        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False, "timeout": 5},
        )

        self._apply_pragmas(engine)
        self._engines[app_id] = engine
        self._sessionmakers[app_id] = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # ── Access ───────────────────────────────────────────────────

    def get_engine(self, app_id: str) -> Engine:
        engine = self._engines.get(app_id)
        if engine is None:
            raise KeyError(f"No database registered for app: {app_id}")
        return engine

    def get_session(self, app_id: str) -> Session:
        sm = self._sessionmakers.get(app_id)
        if sm is None:
            raise KeyError(f"No database registered for app: {app_id}")
        return sm()

    def run_migrations(self, app_id: str, base: type) -> None:
        """Create all tables for the app's declarative base."""
        engine = self.get_engine(app_id)
        base.metadata.create_all(engine)
        self._bases[app_id] = base
        tables = list(base.metadata.tables.keys())
        logger.info("Migrated %s: %d tables", app_id, len(tables))

    # ── Lifecycle ────────────────────────────────────────────────

    def dispose(self, app_id: str | None = None) -> None:
        if app_id:
            engine = self._engines.pop(app_id, None)
            if engine:
                engine.dispose()
                self._sessionmakers.pop(app_id, None)
                self._bases.pop(app_id, None)
        else:
            for e in self._engines.values():
                e.dispose()
            self._engines.clear()
            self._sessionmakers.clear()
            self._bases.clear()

    def list_databases(self) -> dict[str, str]:
        return {aid: str(engine.url) for aid, engine in self._engines.items()}

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _resolve_path(db_path: str) -> Path:
        if os.path.isabs(db_path):
            return Path(db_path)
        return DB_DIR / db_path

    @staticmethod
    def _apply_pragmas(engine: Engine) -> None:
        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        with engine.connect() as conn:
            for pragma in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL", "PRAGMA busy_timeout=5000"):
                try:
                    conn.execute(text(pragma))
                except Exception:
                    pass
            conn.commit()

    def _ensure_core_db(self) -> None:
        """Create orion.db for core state if not registered."""
        if "orion" not in self._engines:
            self.register("orion", "orion.db")


# ── Singleton ────────────────────────────────────────

_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    global _manager
    if _manager is None:
        _manager = DatabaseManager()
    return _manager
