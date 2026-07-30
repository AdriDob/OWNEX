"""Agent Registry for OWNEX.

Central registry of all available agents in the system.
Used by the Copilot to discover and route tasks to appropriate agents.
"""

from __future__ import annotations

from typing import Any


class AgentRegistry:
    """Registry of available OWNEX agents."""

    def __init__(self) -> None:
        self._agents: dict[str, dict[str, Any]] = {}

    def register(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: list[str],
        status: str = "available",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "name": name,
            "description": description,
            "capabilities": capabilities,
            "status": status,
            "metadata": metadata or {},
        }

    def get(self, agent_id: str) -> dict[str, Any] | None:
        return self._agents.get(agent_id)

    def list_agents(self, status: str | None = None) -> list[dict[str, Any]]:
        if status is None:
            return list(self._agents.values())
        return [a for a in self._agents.values() if a["status"] == status]

    def list_capabilities(self) -> list[str]:
        caps: set[str] = set()
        for agent in self._agents.values():
            caps.update(agent.get("capabilities", []))
        return sorted(caps)

    def find_by_capability(self, capability: str) -> list[dict[str, Any]]:
        return [a for a in self._agents.values() if capability in a.get("capabilities", [])]

    def set_status(self, agent_id: str, status: str) -> None:
        if agent_id in self._agents:
            self._agents[agent_id]["status"] = status

    def remove(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def count(self) -> int:
        return len(self._agents)


_default_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry
