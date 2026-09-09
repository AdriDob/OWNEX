from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy import Engine
from sqlalchemy.orm import Session


class IDatabase(ABC):
    """Multi-database manager — each app gets its own SQLite instance."""

    @abstractmethod
    def register(self, app_id: str, db_path: str) -> None:
        """Register a database for an app.

        Creates the engine but does NOT create tables yet.
        """

    @abstractmethod
    def get_engine(self, app_id: str) -> Engine: ...

    @abstractmethod
    def get_session(self, app_id: str) -> Session: ...

    @abstractmethod
    def run_migrations(self, app_id: str, base: type) -> None:
        """Create all tables for an app's declarative base."""

    @abstractmethod
    def dispose(self, app_id: str | None = None) -> None:
        """Dispose engines, optionally for one app."""

    @abstractmethod
    def list_databases(self) -> dict[str, str]:
        """Return {app_id: db_path} for all registered databases."""
