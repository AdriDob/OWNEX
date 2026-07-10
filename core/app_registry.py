"""App Registry — dynamically discovers and loads application plugins."""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import declarative_base

from core.interfaces.app import IAppPlugin

logger = logging.getLogger("orion.core.registry")

APPS_PACKAGE = "apps"
APPS_DIR = Path(__file__).resolve().parent.parent / APPS_PACKAGE


class AppRegistry:
    """Singleton — loads all installed apps and tracks their manifests."""

    def __init__(self) -> None:
        self._apps: dict[str, IAppPlugin] = {}
        self._loaded = False

    # ── Discovery ────────────────────────────────────────────────

    def discover(self) -> dict[str, IAppPlugin]:
        """Scan apps/ directory and import every manifest."""
        if self._loaded:
            return self._apps

        if not APPS_DIR.is_dir():
            logger.warning("apps/ directory not found at %s", APPS_DIR)
            return self._apps

        for entry in sorted(APPS_DIR.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_") or entry.name.startswith("."):
                continue
            manifest_path = entry / "manifest.py"
            if not manifest_path.exists():
                logger.debug("Skipping %s — no manifest.py", entry.name)
                continue
            try:
                mod = importlib.import_module(f"{APPS_PACKAGE}.{entry.name}.manifest")
                manifest: IAppPlugin = getattr(mod, "manifest", None)
                if manifest is None:
                    logger.warning("%s/manifest.py has no 'manifest' variable", entry.name)
                    continue
                self._apps[manifest.id] = manifest
                logger.info("Discovered app: %s v%s (%s)", manifest.name, manifest.version, manifest.id)
            except Exception as exc:
                logger.error("Failed to load app %s: %s", entry.name, exc)

        self._loaded = True
        return self._apps

    # ── Access ───────────────────────────────────────────────────

    def get(self, app_id: str) -> IAppPlugin | None:
        return self._apps.get(app_id)

    def list_apps(self) -> list[IAppPlugin]:
        return sorted(self._apps.values(), key=lambda a: a.order)

    def get_routers(self) -> list[tuple[str, APIRouter]]:
        """Return (prefix, router) pairs for all apps."""
        result: list[tuple[str, APIRouter]] = []
        for app in self._apps.values():
            for router in app.routers:
                prefix = f"/api/{app.router_prefix or app.id}"
                result.append((prefix, router))
        return result

    def get_models(self) -> dict[str, list[type]]:
        """Return {app_id: [model classes]} for all apps."""
        return {aid: app.models for aid, app in self._apps.items()}

    def get_scheduler_jobs(self) -> list[Any]:
        """Return all scheduler jobs across apps."""
        jobs = []
        for app in self._apps.values():
            jobs.extend(app.scheduler_jobs)
        return jobs

    # ── Lifecycle ────────────────────────────────────────────────

    def mount_routers(self, fastapi_app: FastAPI) -> None:
        """Mount all app routers onto the FastAPI instance."""
        for prefix, router in self.get_routers():
            fastapi_app.include_router(router, prefix=prefix)
            logger.info("Mounted router: %s", prefix)

    def register_database_models(self, db_manager: Any) -> None:
        """Register each app's models with the database manager."""
        for app_id, models in self.get_models().items():
            if models:
                base = declarative_base()
                # Each app uses its own Base
                db_manager.run_migrations(app_id, base)

    def status(self) -> dict[str, dict]:
        """Return status dict for all apps (for health endpoint)."""
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

    # ── Extension bridge ────────────────────────────────────────────

    def discover_extensions(self) -> dict[str, Any]:
        """Bridge to ExtensionRegistry — discover and load extensions.

        Returns status dict for logging.
        """
        try:
            from core.extension.registry import get_extension_registry
            er = get_extension_registry()
            manifests = er.discover()
            results = er.load_all()
            loaded = sum(1 for v in results.values() if v)
            failed = sum(1 for v in results.values() if not v)
            return {
                "discovered": len(manifests),
                "loaded": loaded,
                "failed": failed,
                "errors": er.get_errors(),
            }
        except Exception as exc:
            logger.warning("Extension discovery failed (non-fatal): %s", exc)
            return {"discovered": 0, "loaded": 0, "failed": 0, "errors": {"bridge": str(exc)}}


# ── Singleton ────────────────────────────────────────

_registry: AppRegistry | None = None


def get_app_registry() -> AppRegistry:
    global _registry
    if _registry is None:
        _registry = AppRegistry()
    return _registry
