from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Action:
    id: str
    description: str
    tool: str
    params: dict[str, Any]
    risk: float = 0.0  # 0.0 (none) to 1.0 (critical)


@dataclass
class Feedback:
    action_id: str
    outcome: str  # success | failure | partial
    reward: float = 0.0
    notes: str = ""


@dataclass
class AgentContext:
    app_id: str
    state: dict[str, Any] = field(default_factory=dict)
    memory: list[dict] = field(default_factory=list)
    last_action: Action | None = None


class IAgent(ABC):
    """Specialized AI agent for one application domain.

    Each agent has its own prompt, tools, and memory namespace.
    """

    agent_id: str
    app_id: str

    @abstractmethod
    async def get_next_action(self, context: AgentContext) -> Action | None:
        """Decide the next action based on context and memory."""

    @abstractmethod
    async def learn(self, feedback: Feedback) -> None:
        """Incorporate feedback into memory and adjust future behavior."""

    @abstractmethod
    def get_tools(self) -> list[str]:
        """Return tool names available to this agent."""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the agent's system prompt."""
