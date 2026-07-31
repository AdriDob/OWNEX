"""Research Agent — Knowledge Department.

Explores and investigates technologies.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.research")


class ResearchAgent(SpecialistAgent):
    """Research Agent — Knowledge Department."""

    def _get_agent_id(self) -> AgentId:
        return AgentId.RESEARCH

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Explore and investigate technologies",
            secondary_objectives=[
                "Investigate technologies",
                "Find repositories",
                "Compare solutions",
                "Study trends",
            ],
            max_concurrent_tasks=5,
            max_execution_time=300,
            available_tools=["web_search", "github_search", "technology_radar"],
            priority_level=4,
            task_preferences=["research", "investigation"],
            handoff_targets=[AgentId.ARCHITECTURE, AgentId.REVENUE],
            handoff_conditions={"research_completed": "architecture"},
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["web_search", "github_search", "technology_radar"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.ARCHITECTURE, AgentId.REVENUE]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.RESEARCH_START, EventType.RESEARCH_COMPLETED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.RESEARCH_START:
            self._start_research(event)

    def _start_research(self, event: AgentEvent) -> None:
        """Start research."""
        topic = event.payload.get("topic", "")
        logger.info(f"[RESEARCH] Researching: {topic}")
