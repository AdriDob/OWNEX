"""Agent Factory Adapter — Minimal stub for backward compatibility."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AgentType(StrEnum):
    """Types of investment agents."""

    TRADING = "trading"
    ANALYSIS = "analysis"
    REBALANCING = "rebalancing"
    MONITORING = "monitoring"


class AgentStatus(StrEnum):
    """Agent status."""

    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentSpec:
    """Specification for an agent."""

    name: str
    agent_type: AgentType
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInstance:
    """Running agent instance."""

    id: str
    spec: AgentSpec
    status: AgentStatus = AgentStatus.IDLE


class AgentFactory:
    """Factory for creating and managing investment agents."""

    def __init__(self) -> None:
        self.agents: dict[str, AgentInstance] = {}

    def create(self, spec: AgentSpec) -> AgentInstance:
        """Create a new agent."""
        agent = AgentInstance(id=f"agent_{len(self.agents)}", spec=spec)
        self.agents[agent.id] = agent
        return agent

    def get(self, agent_id: str) -> AgentInstance | None:
        """Get agent by ID."""
        return self.agents.get(agent_id)

    def list_agents(self) -> list[AgentInstance]:
        """List all agents."""
        return list(self.agents.values())


def build_agent_factory() -> AgentFactory:
    """Build a new AgentFactory."""
    return AgentFactory()
