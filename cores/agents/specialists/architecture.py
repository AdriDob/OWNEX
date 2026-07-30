"""Architecture Agent — CTO in Build Department.

Designs global system architecture.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.architecture")


class ArchitectureAgent(SpecialistAgent):
    """Architecture Agent — CTO in Build Department."""

    def _get_agent_id(self) -> AgentId:
        return AgentId.ARCHITECTURE

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Design global system architecture",
            secondary_objectives=[
                "Make architectural decisions",
                "Review structure",
                "Choose technologies",
                "Analyze technical debt",
            ],
            max_concurrent_tasks=3,
            max_execution_time=600,
            available_tools=["devin", "large_models", "diagrams"],
            priority_level=2,
            task_preferences=["architecture_design", "technology_selection"],
            handoff_targets=[AgentId.CODING],
            handoff_conditions={"architecture_ready": "coding"},
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["devin", "large_models", "diagrams"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.CODING]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.ARCHITECTURE_DECISION, EventType.ARCHITECTURE_REVIEW]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.ARCHITECTURE_DECISION:
            self._handle_architecture_decision(event)

    def _handle_architecture_decision(self, event: AgentEvent) -> None:
        """Handle architecture decision."""
        decision = event.payload.get("decision", "")
        logger.info(f"[ARCHITECTURE] Decision: {decision}")
