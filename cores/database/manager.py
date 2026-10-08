"""Database Manager — multi-SQLite engine pool.

Each application registers its own database path.
The Core uses ``ownex.db`` for system settings, events, and scheduler state.
"""

from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, MetaData, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from cores.interfaces import IDatabase

logger = logging.getLogger("ownex.core.database")

DATA_DIR = Path(os.environ.get("OWNEX_DATA_DIR", Path.home() / ".ownex"))
DB_DIR = DATA_DIR / "database"


class DatabaseManager(IDatabase):
    """Manages multiple SQLite databases, one per application."""

    def __init__(self) -> None:
        self._engines: dict[str, Engine] = {}
        self._sessionmakers: dict[str, sessionmaker] = {}
        self._bases: dict[str, Any] = {}

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

    def run_migrations(self, app_id: str, base: Any) -> None:
        """Create all tables for the app's declarative base (or ``MetaData``).

        Acepta las dos formas a propósito. Cada app declara SU propio
        ``Base`` en su ``models.py`` (``Base = declarative_base()``), así que
        el base del app nunca es el del runtime: pasar una base nueva vacía
        creaba **0 tablas** y la DB de cada app quedaba vacía para siempre
        (medido 2026-10-08: ``aegis``, ``atlas`` y ``odyssey`` con 0 tablas
        y 53 call sites que las consultan). Ver ``api/lifespan.py``.
        """
        engine = self.get_engine(app_id)
        metadata = base if isinstance(base, MetaData) else base.metadata
        metadata.create_all(engine)
        self._bases[app_id] = base
        tables = list(metadata.tables.keys())
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
                with contextlib.suppress(Exception):
                    conn.execute(text(pragma))
            conn.commit()

    def _ensure_core_db(self) -> None:
        """Create ownex.db for core state if not registered."""
        if "ownex" not in self._engines:
            self.register("ownex", "ownex.db")


# ── Singleton ────────────────────────────────────────

_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    global _manager
    if _manager is None:
        _manager = DatabaseManager()
    return _manager
