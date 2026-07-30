"""Capability Registry for OWNEX.

Central registry of all available capabilities in the system.
Used by the Copilot to discover what the system can do.
"""

from __future__ import annotations

from typing import Any


class CapabilityRegistry:
    """Registry of available OWNEX capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, dict[str, Any]] = {}

    def register(
        self,
        capability_id: str,
        name: str,
        description: str,
        agent_id: str,
        status: str = "available",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._capabilities[capability_id] = {
            "capability_id": capability_id,
            "name": name,
            "description": description,
            "agent_id": agent_id,
            "status": status,
            "metadata": metadata or {},
        }

    def get(self, capability_id: str) -> dict[str, Any] | None:
        return self._capabilities.get(capability_id)

    def list_capabilities(self, status: str | None = None) -> list[dict[str, Any]]:
        if status is None:
            return list(self._capabilities.values())
        return [c for c in self._capabilities.values() if c["status"] == status]

    def find_by_agent(self, agent_id: str) -> list[dict[str, Any]]:
        return [c for c in self._capabilities.values() if c.get("agent_id") == agent_id]

    def set_status(self, capability_id: str, status: str) -> None:
        if capability_id in self._capabilities:
            self._capabilities[capability_id]["status"] = status

    def remove(self, capability_id: str) -> None:
        self._capabilities.pop(capability_id, None)

    def count(self) -> int:
        return len(self._capabilities)


_default_registry: CapabilityRegistry | None = None


def get_capability_registry() -> CapabilityRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = CapabilityRegistry()
    return _default_registry
