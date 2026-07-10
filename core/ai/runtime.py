"""AI Runtime — manages agent instances and LLM providers.

Each app registers its own agent. Agents share the LLM provider pool
but have independent prompts, tools, and memory namespaces.
"""

from __future__ import annotations

import logging
from typing import Any

from core.interfaces.agent import IAgent, Action, AgentContext, Feedback

logger = logging.getLogger("orion.core.ai")


class AIRuntime:
    """Runtime for multi-agent execution."""

    def __init__(self) -> None:
        self._agents: dict[str, IAgent] = {}
        self._contexts: dict[str, AgentContext] = {}

    def register_agent(self, agent: IAgent) -> None:
        """Register an agent instance."""
        self._agents[agent.agent_id] = agent
        self._contexts[agent.agent_id] = AgentContext(app_id=agent.app_id)
        logger.info("Registered agent: %s (app=%s)", agent.agent_id, agent.app_id)

    def unregister_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self._contexts.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> IAgent | None:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[dict]:
        return [
            {
                "id": a.agent_id,
                "app_id": a.app_id,
                "tools": a.get_tools(),
            }
            for a in self._agents.values()
        ]

    async def get_next_action(self, app_id: str) -> Action | None:
        """Ask an app's agent for the next action."""
        agent = self._find_agent(app_id)
        if agent is None:
            return None
        ctx = self._contexts.get(agent.agent_id) or AgentContext(app_id=app_id)
        return await agent.get_next_action(ctx)

    async def learn(self, app_id: str, feedback: Feedback) -> None:
        """Send feedback to an app's agent."""
        agent = self._find_agent(app_id)
        if agent:
            await agent.learn(feedback)

    def _find_agent(self, app_id: str) -> IAgent | None:
        for agent in self._agents.values():
            if agent.app_id == app_id:
                return agent
        return None

    def status(self) -> dict:
        return {
            "total_agents": len(self._agents),
            "apps": list({a.app_id for a in self._agents.values()}),
        }


# ── Singleton ────────────────────────────────────────

_runtime: AIRuntime | None = None


def get_ai_runtime() -> AIRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AIRuntime()
    return _runtime
