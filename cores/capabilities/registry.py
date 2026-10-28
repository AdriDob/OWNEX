"""Capability Registry — modules register their abilities here.

COPILOT (or any module) discovers what the system can do without
knowing module names: "Who can send email?" → Outlook.

Usage:

    from cores.capabilities.registry import get_capability_registry

    reg = get_capability_registry()
    reg.register("send_email", "outlook", {"auth": "oauth2", "provider": "microsoft"})
    reg.register("create_invoice", "arca", {"country": "AR", "tax_system": "WSFEv1"})

    # COPILOT discovers capabilities
    email_modules = reg.find("send_email")  # → [CapabilityEntry(...)]
    all_caps = reg.list_capabilities()       # → ["send_email", "create_invoice", ...]
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.core.capabilities")


@dataclass
class CapabilityEntry:
    """A registered capability provided by a module."""

    capability: str
    module: str
    metadata: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    #: Lifecycle: `active` (usable) or `broken` (registered but failing).
    #: Read by `CapabilityExpansionEngine.daily_evolution_report()`
    #: (cores/capabilities/expansion.py:645) to tell "integrated" from
    #: "known but not working".
    status: str = "active"
    #: Performance counters read by the same report (expansion.py:582-588).
    #: `health` is UNKNOWN (None) until measured — never a default 1.0.
    category: str = ""
    usage_count: int = 0
    total_duration_ms: float = 0.0
    health: float | None = None

    @property
    def avg_performance_ms(self) -> float:
        """Mean measured duration, or 0.0 when never used (not a claim).

        Named `avg_performance_ms` because that is what
        `CapabilityExpansionEngine` reads (expansion.py:587,656).
        """
        return self.total_duration_ms / self.usage_count if self.usage_count else 0.0


class CapabilityRegistry:
    """Registry where modules register their capabilities.

    Enables COPILOT to discover available actions without hardcoding
    module names.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self._entries: list[CapabilityEntry] = []
        self._index: dict[str, list[CapabilityEntry]] = {}
        self._lock = threading.Lock()
        # Test-isolation only: the registry is in-memory by design (no
        # save/load), so an explicit path lets a test get its own instance
        # without touching the process-global one. Never implies persistence.
        self._store_path = store_path
        self._load()

    # ── Persistence (opt-in, only when store_path was given) ─────────

    def persist(self) -> None:
        """Force a snapshot. No-op unless a `store_path` was given.

        Called by `CapabilityExpansionEngine` (expansion.py:505) after it
        mutates entries directly.
        """
        self._save()

    def _save(self) -> None:
        """Best-effort snapshot. A store failure never breaks registration."""
        if self._store_path is None:
            return
        try:
            self._store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "entries": [asdict(e) for e in self._entries],
            }
            self._store_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not persist capability registry: %s", exc)

    def _load(self) -> None:
        """Restore a previous snapshot. Corrupt/absent file = empty registry."""
        if self._store_path is None or not self._store_path.exists():
            return
        try:
            payload = json.loads(self._store_path.read_text(encoding="utf-8"))
            for raw in payload.get("entries", []):
                entry = CapabilityEntry(
                    capability=raw["capability"],
                    module=raw.get("module", ""),
                    metadata=raw.get("metadata") or {},
                    description=raw.get("description", ""),
                    status=raw.get("status", "active"),
                    category=raw.get("category", ""),
                    usage_count=int(raw.get("usage_count", 0) or 0),
                    total_duration_ms=float(raw.get("total_duration_ms", 0.0) or 0.0),
                    health=raw.get("health"),
                )
                self._entries.append(entry)
                self._index.setdefault(entry.capability, []).append(entry)
        except Exception as exc:
            logger.warning("Could not load capability registry: %s", exc)

    # ── Registration ────────────────────────────────────────────

    def register(
        self, capability: str, module: str, metadata: dict[str, Any] | None = None, description: str = ""
    ) -> None:
        """Register a module as providing a capability."""
        with self._lock:
            entry = CapabilityEntry(
                capability=capability,
                module=module,
                metadata=metadata or {},
                description=description,
                category=str((metadata or {}).get("category", "")),
            )
            self._entries.append(entry)
            self._index.setdefault(capability, []).append(entry)
        logger.debug("Registered capability '%s' → %s", capability, module)
        self._save()

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
        if removed:
            logger.debug("Unregistered capability '%s' from %s", capability, module)
        return removed > 0

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

    def record_usage(self, capability: str, duration_ms: float, module: str | None = None) -> bool:
        """Record one measured use of a capability. Returns False if unknown."""
        with self._lock:
            targets = self._index.get(capability, [])
            if module is not None:
                targets = [e for e in targets if e.module == module]
            if not targets:
                return False
            for entry in targets:
                entry.usage_count += 1
                entry.total_duration_ms += max(0.0, float(duration_ms))
            self._save()
            return True

    def set_health(self, capability: str, health: float, module: str | None = None) -> bool:
        """Set measured health in [0, 1]. Returns False if unknown or invalid."""
        if not 0.0 <= float(health) <= 1.0:
            return False
        with self._lock:
            targets = self._index.get(capability, [])
            if module is not None:
                targets = [e for e in targets if e.module == module]
            if not targets:
                return False
            for entry in targets:
                entry.health = float(health)
            self._save()
            return True

    def set_status(self, capability: str, status: str, module: str | None = None) -> bool:
        """Mark a capability (or one module's registration of it) active/broken.

        Returns False when nothing matched, so callers can tell "no such
        capability" from "status applied".
        """
        with self._lock:
            targets = self._index.get(capability, [])
            if module is not None:
                targets = [e for e in targets if e.module == module]
            if not targets:
                return False
            for entry in targets:
                entry.status = status
            self._save()
            return True

    def stats(self) -> dict[str, Any]:
        """Aggregate registry counters.

        Consumed by `GET /api/stability/status` (`api/routers/stability.py`)
        and `CapabilityExpansionEngine.daily_evolution_report()`. Derived
        from live entries — never a hardcoded number.
        """
        with self._lock:
            entries = list(self._entries)
            unique = list(self._index.keys())
        broken = [e for e in entries if e.status == "broken" or not e.module]
        active = [e for e in entries if e not in broken]
        categories = sorted({e.module for e in entries if e.module})
        metadata_categories = {str(e.metadata.get("category")) for e in entries if e.metadata.get("category")}
        return {
            "unique_capabilities": len(unique),
            "total_usage_count": sum(e.usage_count for e in entries),
            "total_entries": len(entries),
            "active": len(active),
            "broken": len(broken),
            "categories": sorted(set(categories) | metadata_categories),
        }

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
        logger.debug("Capability registry cleared")

    def count(self) -> int:
        """Return total number of registered capability entries."""
        with self._lock:
            return len(self._entries)


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


def reset_capability_registry(store_path: Path | None = None) -> CapabilityRegistry:
    """Clear and recreate the registry, returning the new instance.

    `store_path` is forwarded for test isolation (see `CapabilityRegistry`).
    """
    global _registry
    with _reg_lock:
        if _registry:
            _registry.clear()
        _registry = CapabilityRegistry(store_path=store_path)
        return _registry
