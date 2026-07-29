"""Integration Registry — aggregated status of all known integrations."""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.extension.capabilities import Capability

logger = logging.getLogger("orion.core.integrations.registry")

StatusValue = str  # "connected" | "disconnected" | "error" | "unknown"


@dataclass
class IntegrationStatus:
    """Runtime status of a single integration."""

    name: str
    category: str
    status: StatusValue = "unknown"
    description: str = ""
    icon: str = "🔌"
    last_sync: str | None = None
    latency_ms: float | None = None
    error: str | None = None
    permissions: list[str] = field(default_factory=lambda: ["read"])
    tags: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "description": self.description,
            "icon": self.icon,
            "last_sync": self.last_sync,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "permissions": self.permissions,
            "tags": self.tags,
            "checked_at": self.checked_at,
        }


class IntegrationRegistry:
    """Registry that stores known integrations and checks their status at runtime."""

    def __init__(self) -> None:
        self._status_cache: dict[str, IntegrationStatus] = {}
        self._loaded = False

    # ── Registration ────────────────────────────────────────────────

    def register(self, status: IntegrationStatus) -> None:
        self._status_cache[status.name] = status

    def register_from_def(
        self,
        name: str,
        category: str,
        *,
        description: str = "",
        icon: str = "🔌",
        tags: list[str] | None = None,
        status: StatusValue = "unknown",
    ) -> None:
        self.register(
            IntegrationStatus(
                name=name,
                category=category,
                description=description,
                icon=icon,
                tags=tags or [],
                status=status,
            )
        )

    def get(self, name: str) -> IntegrationStatus | None:
        return self._status_cache.get(name)

    def list(self, category: str | None = None) -> list[IntegrationStatus]:
        if category:
            return [s for s in self._status_cache.values() if s.category == category]
        return list(self._status_cache.values())

    def list_categories(self) -> list[str]:
        cats: set[str] = set()
        for s in self._status_cache.values():
            cats.add(s.category)
        return sorted(cats)

    def summary(self) -> dict[str, Any]:
        statuses = self._status_cache.values()
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for s in statuses:
            by_status[s.status] = by_status.get(s.status, 0) + 1
            by_category[s.category] = by_category.get(s.category, 0) + 1
        return {
            "total": len(self._status_cache),
            "by_status": by_status,
            "by_category": by_category,
            "categories": self.list_categories(),
            "integrations": [s.to_dict() for s in self._status_cache.values()],
        }

    # ── Status checks ───────────────────────────────────────────────

    # ── Extension bridge ─────────────────────────────────────

    def load_extensions(self, extension_registry: Any) -> None:
        """Register all discovered extensions as integrations."""
        for ext_manifest in extension_registry.list_extensions():
            ext_id = ext_manifest.id
            tags = [c.id if isinstance(c, Capability) else c for c in ext_manifest.capabilities]
            status = IntegrationStatus(
                name=ext_id,
                category="plugin",
                description=ext_manifest.description,
                icon=ext_manifest.icon,
                tags=tags,
                permissions=["read"] if ext_manifest.hot_reloadable else ["read", "write"],
            )
            self.register(status)
        self._loaded = True

    def refresh_with_extensions(self, extension_registry: Any) -> dict[str, IntegrationStatus]:
        """Refresh all integrations including plugin extensions."""
        self.load_extensions(extension_registry)
        for status in self._status_cache.values():
            self._check_one(status)
        return dict(self._status_cache)

    def refresh(self) -> dict[str, IntegrationStatus]:
        """Re-check status for all integrations."""
        for status in self._status_cache.values():
            self._check_one(status)
        return dict(self._status_cache)

    def check(self, name: str) -> IntegrationStatus | None:
        """Check a single integration by name."""
        status = self._status_cache.get(name)
        if status is None:
            return None
        self._check_one(status)
        return status

    def _check_one(self, status: IntegrationStatus) -> None:
        """Run heuristics to determine integration status."""
        now = datetime.now(timezone.utc)
        status.checked_at = now.isoformat()

        try:
            self._env_check(status)
            self._vault_check(status)
            self._health_check_callable(status)
        except Exception as exc:
            status.status = "error"
            status.error = str(exc)[:200]
            logger.warning("Integration %s check failed: %s", status.name, exc)

    def _env_check(self, status: IntegrationStatus) -> None:
        """Check env vars — if any required key is set, the integration is potentially config'd."""
        # Determine env keys from builtin defs
        from core.integrations.discovery import get_integration

        idef = get_integration(status.name)
        if idef and idef.env_keys:
            found = [k for k in idef.env_keys if os.environ.get(k)]
            if found:
                if status.status == "unknown":
                    status.status = "disconnected"
            else:
                if status.status == "unknown":
                    status.status = "disconnected"
        elif status.status == "unknown":
            status.status = "disconnected"

    def _vault_check(self, status: IntegrationStatus) -> None:
        """Check if any secrets are stored in vault for this integration."""
        from core.integrations.discovery import get_integration

        idef = get_integration(status.name)
        if not idef or not idef.vault_provider:
            return
        try:
            from core.secrets.manager import get_secrets_manager

            manager = get_secrets_manager()
            keys = manager.list_keys()
            if any(idef.vault_provider.lower() in k.lower() for k in keys):
                status.status = "connected"
            elif status.status == "unknown":
                status.status = "disconnected"
        except Exception:
            pass

    def _health_check_callable(self, status: IntegrationStatus) -> None:
        """Try to import and run a custom health check function."""
        from core.integrations.discovery import get_integration

        idef = get_integration(status.name)
        if not idef or not idef.health_check:
            return
        try:
            module_path, func_name = idef.health_check.rsplit(".", 1)
            mod = importlib.import_module(module_path)
            func = getattr(mod, func_name)
            result = func()
            if result is True or result.get("ok") is True:
                status.status = "connected"
            elif isinstance(result, dict) and "error" in result:
                status.status = "error"
                status.error = str(result["error"])[:200]
            else:
                status.status = "disconnected"
        except Exception as exc:
            status.status = "error"
            status.error = f"health check error: {exc}"[:200]


# ── Singleton ──────────────────────────────────────────────────────

_registry: IntegrationRegistry | None = None


def get_integration_registry() -> IntegrationRegistry:
    global _registry
    if _registry is None:
        _registry = IntegrationRegistry()
    return _registry


def init_integration_registry(extension_registry: Any = None) -> IntegrationRegistry:
    """Initialize the registry with all built-in integrations.

    If ``extension_registry`` is provided, also registers all
    discovered extensions as plugin integrations.
    """
    registry = get_integration_registry()
    from core.integrations.discovery import get_builtin_integrations

    registry.load_all(get_builtin_integrations())
    if extension_registry is not None:
        registry.load_extensions(extension_registry)
    return registry
