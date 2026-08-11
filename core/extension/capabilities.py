from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Capability:
    """A declared capability an extension provides.

    Examples:
      - ``Capability("scanner", "subdomain")``
      - ``Capability("ai_model", "gemini")``
      - ``Capability("exporter", "pdf")``
      - ``Capability("connector", "binance")``
      - ``Capability("widget", "portfolio-value")``
      - ``Capability("notification", "telegram")``
    """

    domain: str  # e.g. "scanner", "ai_model", "exporter", "connector"
    name: str  # e.g. "subdomain", "gemini", "pdf", "binance"
    description: str = ""
    config: dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """Maps capability domain+name → extension_id."""

    def __init__(self) -> None:
        self._capabilities: dict[str, dict[str, str]] = {}  # domain → {name → ext_id}

    def register(self, extension_id: str, capability: Capability) -> None:
        self._capabilities.setdefault(capability.domain, {})
        existing = self._capabilities[capability.domain].get(capability.name)
        if existing and existing != extension_id:
            import logging

            logging.getLogger("orion.core.capabilities").warning(
                "Capability %s/%s claimed by both %s and %s — keeping %s",
                capability.domain,
                capability.name,
                existing,
                extension_id,
                existing,
            )
            return
        self._capabilities[capability.domain][capability.name] = extension_id

    def unregister(self, extension_id: str) -> None:
        for domain, names in list(self._capabilities.items()):
            to_remove = [name for name, ext_id in names.items() if ext_id == extension_id]
            for name in to_remove:
                del names[name]
            if not names:
                del self._capabilities[domain]

    def find(self, domain: str, name: str | None = None) -> list[str]:
        """Find extension IDs that provide a capability.

        Args:
            domain: Capability domain (e.g. "scanner")
            name: Specific name within domain, or None for all in domain

        Returns:
            List of extension IDs
        """
        if domain not in self._capabilities:
            return []
        if name is None:
            return list(self._capabilities[domain].values())
        ext_id = self._capabilities[domain].get(name)
        return [ext_id] if ext_id else []

    def list_capabilities(self) -> list[dict]:
        """Return all registered capabilities."""
        result = []
        for domain, names in self._capabilities.items():
            for name, ext_id in names.items():
                result.append({"domain": domain, "name": name, "extension_id": ext_id})
        return result

    def who_can(self, domain: str, name: str | None = None) -> str | None:
        """Quick lookup: who provides this capability? Returns first match."""
        ids = self.find(domain, name)
        return ids[0] if ids else None

    def has(self, domain: str, name: str) -> bool:
        return domain in self._capabilities and name in self._capabilities[domain]


_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry
