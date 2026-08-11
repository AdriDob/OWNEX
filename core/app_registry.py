"""App Registry — dynamically discovers and loads application plugins."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import declarative_base

from core.interfaces.app import IAppPlugin
from core.plugin.discovery import discover_manifests

logger = logging.getLogger("orion.core.registry")

APPS_PACKAGE = "apps"
APPS_DIR = Path(__file__).resolve().parent.parent / APPS_PACKAGE


class AppRegistry:
    """Singleton — loads all installed apps and tracks their manifests."""

    def __init__(self) -> None:
        self._apps: dict[str, IAppPlugin] = {}
        self._loaded = False

    def discover(self) -> dict[str, IAppPlugin]:
        """Scan ``apps/`` directory and import every manifest."""
        if self._loaded:
            return self._apps
        manifests = discover_manifests(APPS_DIR, APPS_PACKAGE, IAppPlugin)
        self._apps.update(manifests)  # type: ignore[arg-type]
        self._loaded = True
        return self._apps

    def get(self, app_id: str) -> IAppPlugin | None:
        return self._apps.get(app_id)

    def list_apps(self) -> list[IAppPlugin]:
        return sorted(self._apps.values(), key=lambda a: a.order)

    def get_routers(self) -> list[tuple[str, APIRouter]]:
        result: list[tuple[str, APIRouter]] = []
        for app in self._apps.values():
            for router in app.routers:
                prefix = f"/api/{app.router_prefix or app.id}"
                result.append((prefix, router))
        return result

    def get_models(self) -> dict[str, list[type]]:
        return {aid: app.models for aid, app in self._apps.items()}

    def get_scheduler_jobs(self) -> list[Any]:
        jobs = []
        for app in self._apps.values():
            jobs.extend(app.scheduler_jobs)
        return jobs

    def mount_routers(self, fastapi_app: FastAPI) -> None:
        for prefix, router in self.get_routers():
            fastapi_app.include_router(router, prefix=prefix)
            logger.info("Mounted router: %s", prefix)

    def register_database_models(self, db_manager: Any) -> None:
        for app_id, models in self.get_models().items():
            if models:
                base = declarative_base()
                db_manager.run_migrations(app_id, base)

    def status(self) -> dict[str, dict]:
        return {
            app.id: {
                "name": app.name,
                "version": app.version,
                "description": app.description,
                "icon": app.icon,
                "has_agent": app.agent_class is not None,
                "has_db": bool(app.db_path),
                "providers": len(app.providers),
                "widgets": len(app.widgets),
            }
            for app in self._apps.values()
        }


_registry: AppRegistry | None = None


def get_app_registry() -> AppRegistry:
    global _registry
    if _registry is None:
        _registry = AppRegistry()
    return _registry
