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
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("orion.core.capabilities")


@dataclass
class CapabilityEntry:
    """A registered capability provided by a module."""

    capability: str
    module: str
    metadata: dict[str, Any] = field(default_factory=dict)
    description: str = ""


class CapabilityRegistry:
    """Registry where modules register their capabilities.

    Enables COPILOT to discover available actions without hardcoding
    module names.
    """

    def __init__(self) -> None:
        self._entries: list[CapabilityEntry] = []
        self._index: dict[str, list[CapabilityEntry]] = {}
        self._lock = threading.Lock()

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
            )
            self._entries.append(entry)
            self._index.setdefault(capability, []).append(entry)
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


def reset_capability_registry() -> None:
    """Clear and recreate the registry (testing/utility)."""
    global _registry
    with _reg_lock:
        if _registry:
            _registry.clear()
        _registry = CapabilityRegistry()
