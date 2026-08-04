"""Capability Registry — modules register their abilities here.

COPILOT (or any module) discovers what the system can do without
knowing module names: "Who can send email?" → Outlook.

Usage:

    from core.capabilities.registry import get_capability_registry

    reg = get_capability_registry()
    reg.register("send_email", "outlook", {"auth": "oauth2", "provider": "microsoft"})
    reg.register("create_invoice", "arca", {"country": "AR", "tax_system": "WSFEv1"})

    # COPILOT discovers capabilities
    email_modules = reg.find("send_email")  # → [CapabilityEntry(...)]
    all_caps = reg.list_capabilities()       # → ["send_email", "create_invoice", ...]

The registry is persistent: every mutation is flushed to
``data/capabilities_registry.json`` so registrations survive restarts.
Each entry also tracks operational metrics (usage count, health score,
avg performance) used by the Capability Expansion Engine.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.core.capabilities")

# Default persistence path (overridable via env for tests)
_DEFAULT_STORE = Path(os.environ.get("OWNEX_DATA_DIR", "data")) / "capabilities_registry.json"


@dataclass
class CapabilityEntry:
    """A registered capability provided by a module."""

    capability: str
    module: str
    metadata: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    # ── Operational metrics (expansion engine) ─────────────────────
    category: str = ""
    version: str = ""
    dependencies: list[str] = field(default_factory=list)
    status: str = "active"  # active | disabled | broken
    health: float = 1.0  # 0.0 .. 1.0
    avg_performance_ms: float = 0.0
    usage_count: int = 0
    last_used_at: float = 0.0
    improvement_potential: float = 0.0  # 0.0 .. 1.0
    installed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityEntry:
        known = {
            "capability",
            "module",
            "metadata",
            "description",
            "category",
            "version",
            "dependencies",
            "status",
            "health",
            "avg_performance_ms",
            "usage_count",
            "last_used_at",
            "improvement_potential",
            "installed_at",
        }
        clean = {k: v for k, v in data.items() if k in known}
        return cls(**clean)


class CapabilityRegistry:
    """Registry where modules register their capabilities.

    Enables COPILOT to discover available actions without hardcoding
    module names. Persistent across restarts.
    """

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._entries: list[CapabilityEntry] = []
        self._index: dict[str, list[CapabilityEntry]] = {}
        self._lock = threading.Lock()
        self._store_path = Path(store_path) if store_path else _DEFAULT_STORE
        self._dirty = False
        self._load()

    # ── Persistence ───────────────────────────────────────────────

    def _load(self) -> None:
        """Load persisted entries from disk (best-effort)."""
        try:
            if self._store_path.exists():
                data = json.loads(self._store_path.read_text(encoding="utf-8"))
                entries = data.get("entries", []) if isinstance(data, dict) else data
                for item in entries:
                    entry = CapabilityEntry.from_dict(item)
                    self._entries.append(entry)
                    self._index.setdefault(entry.capability, []).append(entry)
                if self._entries:
                    logger.info(
                        "[CAP] Loaded %d capability entries from %s",
                        len(self._entries),
                        self._store_path,
                    )
        except Exception as exc:  # noqa: BLE001 — persistence must never break startup
            logger.warning("[CAP] Failed to load capability registry: %s", exc)

    def _flush(self) -> None:
        """Persist entries to disk (no-op if store path unwritable)."""
        if not self._dirty:
            return
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"version": 1, "entries": [e.to_dict() for e in self._entries]}
            self._store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            self._dirty = False
        except Exception as exc:  # noqa: BLE001
            logger.warning("[CAP] Failed to persist capability registry: %s", exc)

    def persist(self) -> None:
        """Force an immediate flush."""
        with self._lock:
            self._flush()

    # ── Registration ────────────────────────────────────────────

    def register(
        self,
        capability: str,
        module: str,
        metadata: dict[str, Any] | None = None,
        description: str = "",
    ) -> None:
        """Register a module as providing a capability."""
        with self._lock:
            entry = CapabilityEntry(
                capability=capability,
                module=module,
                metadata=metadata or {},
                description=description,
                category=str((metadata or {}).get("category", "")),
                version=str((metadata or {}).get("version", "")),
                installed_at=time.time(),
            )
            self._entries.append(entry)
            self._index.setdefault(capability, []).append(entry)
            self._dirty = True
        self._flush()
        logger.debug("Registered capability '%s' → %s", capability, module)

    def unregister(self, capability: str, module: str) -> bool:
        """Remove a capability registration. Returns True if found."""
        with self._lock:
            before = len(self._entries)
            self._entries[:] = [e for e in self._entries if not (e.capability == capability and e.module == module)]
            if capability in self._index:
                self._index[capability] = [e for e in self._index[capability] if e.module != module]
                if not self._index[capability]:
                    del self._index[capability]
            removed = before - len(self._entries)
            self._dirty = self._dirty or removed > 0
        if removed:
            self._flush()
            logger.debug("Unregistered capability '%s' from %s", capability, module)
        return removed > 0

    # ── Operational metrics ─────────────────────────────────────

    def record_usage(
        self,
        capability: str,
        module: str | None = None,
        duration_ms: float | None = None,
    ) -> None:
        """Record a usage event (and optional duration) for a capability."""
        with self._lock:
            entry = self._find_entry(capability, module)
            if entry is None:
                return
            entry.usage_count += 1
            entry.last_used_at = time.time()
            if duration_ms is not None:
                prev = entry.avg_performance_ms
                entry.avg_performance_ms = (
                    (prev * (entry.usage_count - 1) + duration_ms) / entry.usage_count
                    if entry.usage_count > 1
                    else duration_ms
                )
            self._dirty = True
        self._flush()

    def set_health(self, capability: str, health: float, module: str | None = None) -> None:
        """Set health score (0.0..1.0) for a capability."""
        with self._lock:
            entry = self._find_entry(capability, module)
            if entry is None:
                return
            entry.health = max(0.0, min(1.0, health))
            self._dirty = True
        self._flush()

    def set_status(self, capability: str, status: str, module: str | None = None) -> None:
        """Set operational status: active | disabled | broken."""
        with self._lock:
            entry = self._find_entry(capability, module)
            if entry is None:
                return
            entry.status = status
            self._dirty = True
        self._flush()

    def _find_entry(self, capability: str, module: str | None) -> CapabilityEntry | None:
        if module:
            for e in self._entries:
                if e.capability == capability and e.module == module:
                    return e
        entries = self._index.get(capability, [])
        return entries[0] if entries else None

    # ── Discovery ───────────────────────────────────────────────

    def find(self, capability: str) -> list[CapabilityEntry]:
        """Find all modules providing a given capability."""
        with self._lock:
            return list(self._index.get(capability, []))

    def has_capability(self, capability: str) -> bool:
        """Check if a capability is registered."""
        with self._lock:
            return bool(self._index.get(capability))

    def list_capabilities(self) -> list[str]:
        """List all unique capability names."""
        with self._lock:
            return list(self._index.keys())

    def list_modules(self) -> list[str]:
        """List all registered module names."""
        with self._lock:
            return list({e.module for e in self._entries})

    def list_by_module(self, module: str) -> list[CapabilityEntry]:
        """List all capabilities registered by a specific module."""
        with self._lock:
            return [e for e in self._entries if e.module == module]

    def list_by_category(self, category: str) -> list[CapabilityEntry]:
        """List all capabilities in a category."""
        with self._lock:
            return [e for e in self._entries if (e.category or "").lower() == category.lower()]

    def categories(self) -> list[str]:
        """List all distinct categories present in the registry."""
        with self._lock:
            return sorted({e.category for e in self._entries if e.category})

    def get_entry(self, capability: str, module: str) -> CapabilityEntry | None:
        """Get a specific capability registration."""
        with self._lock:
            for e in self._entries:
                if e.capability == capability and e.module == module:
                    return e
        return None

    def clear(self) -> None:
        """Clear all registrations (testing/utility)."""
        with self._lock:
            self._entries.clear()
            self._index.clear()
            self._dirty = True
        self._flush()
        logger.debug("Capability registry cleared")

    def count(self) -> int:
        """Return total number of registered capability entries."""
        with self._lock:
            return len(self._entries)

    def stats(self) -> dict[str, Any]:
        """Aggregate registry statistics for health/expansion reporting."""
        with self._lock:
            entries = list(self._entries)
        active = sum(1 for e in entries if e.status == "active")
        broken = sum(1 for e in entries if e.status == "broken")
        total_uses = sum(e.usage_count for e in entries)
        return {
            "total_entries": len(entries),
            "unique_capabilities": len({e.capability for e in entries}),
            "active": active,
            "broken": broken,
            "categories": sorted({e.category for e in entries if e.category}),
            "total_usage_count": total_uses,
            "persisted": self._store_path.exists(),
            "store_path": str(self._store_path),
        }


# ── Singleton API ───────────────────────────────────────────────────

_registry: CapabilityRegistry | None = None
_reg_lock = threading.Lock()


def get_capability_registry() -> CapabilityRegistry:
    """Get or create the global CapabilityRegistry instance."""
    global _registry
    if _registry is None:
        with _reg_lock:
            if _registry is None:
                _registry = CapabilityRegistry()
    return _registry


def reset_capability_registry(store_path: str | Path | None = None) -> CapabilityRegistry:
    """Clear and recreate the registry (testing/utility)."""
    global _registry
    with _reg_lock:
        if _registry:
            _registry.clear()
        _registry = CapabilityRegistry(store_path=store_path)
        return _registry
