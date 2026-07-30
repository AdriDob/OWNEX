"""Documentation Agent — Memory in Knowledge Department.

Maintains living documentation for the system.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.documentation")


class DocumentationAgent(SpecialistAgent):
    """Documentation Agent — Memory in Knowledge Department.

    Maintains living documentation for the system.

    Objectives:
    - Primary: Update README, architecture, changelog, CURRENT_STATE
    - Secondary: Provide context for other agents, maintain living memory

    Limits:
    - Max 10 concurrent documentation tasks
    - Max 300s per documentation operation

    Tools:
    - Markdown
    - Diagrams
    - Wiki systems

    Priorities:
    - Priority level: 4
    - Task preferences: documentation maintenance, knowledge capture

    Handoffs:
    - Receives from: All departments
    - Hands off to: Orchestrator (completion)
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.DOCUMENTATION

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Update README, architecture, changelog, CURRENT_STATE",
            secondary_objectives=[
                "Provide context for other agents",
                "Maintain living memory",
                "Document architectural decisions",
                "Track system evolution",
            ],
            max_concurrent_tasks=10,
            max_execution_time=300,
            available_tools=[
                "markdown",
                "diagrams",
                "wiki_systems",
                "changelog_generation",
            ],
            priority_level=4,
            task_preferences=["documentation_maintenance", "knowledge_capture"],
            handoff_targets=[AgentId.ORCHESTRATOR],
            handoff_conditions={
                "documentation_completed": "orchestrator",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["markdown", "diagrams", "wiki_systems"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.ORCHESTRATOR]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.DOCUMENTATION_REQUESTED, EventType.DOCUMENTATION_UPDATED, EventType.KNOWLEDGE_STORED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.DOCUMENTATION_REQUESTED:
            self._generate_documentation(event)

    def _generate_documentation(self, event: AgentEvent) -> None:
        """Generate documentation."""
        topic = event.payload.get("topic", "")
        logger.info(f"[DOCUMENTATION] Generating documentation for: {topic}")
