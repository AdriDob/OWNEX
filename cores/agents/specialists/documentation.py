"""Documentation Specialist — Documentation generation and maintenance."""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.documentation")


class DocumentationAgent(SpecialistAgent):
    """Documentation — Documentation generation and maintenance specialist.
    
    Objectives:
    - Primary: Generate and maintain system documentation
    - Secondary: Create guides, update API docs, document procedures
    
    Limits:
    - Max 10 concurrent documentation tasks
    - Max 300s per documentation operation
    
    Tools:
    - Guide generation
    - API documentation
    - Procedure documentation
    - Markdown formatting
    
    Priorities:
    - Priority level: 5
    - Task preferences: guide generation, documentation maintenance
    
    Handoffs:
    - Receives from: All specialists
    - Hands off to: Commander (completion)
    """
    
    def _get_agent_id(self) -> AgentId:
        return AgentId.DOCUMENTATION
    
    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Generate and maintain system documentation",
            secondary_objectives=[
                "Create user guides and tutorials",
                "Update API documentation",
                "Document procedures and workflows",
            ],
            max_concurrent_tasks=10,
            max_execution_time=300,
            available_tools=[
                "guide_generation",
                "api_documentation",
                "procedure_documentation",
                "markdown_formatting",
            ],
            priority_level=5,
            task_preferences=["guide_generation", "documentation_maintenance"],
            handoff_targets=[AgentId.COMMANDER],
            handoff_conditions={
                "documentation_completed": "commander",
            },
        )
    
    def _get_specialist_tools(self) -> list[str]:
        return ["guide_generation", "api_documentation", "procedure_documentation"]
    
    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.COMMANDER]
    
    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.DOCUMENTATION_REQUESTED, EventType.GUIDE_GENERATED]
    
    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.DOCUMENTATION_REQUESTED:
            self._generate_documentation(event)
    
    def _generate_documentation(self, event: AgentEvent) -> None:
        """Generate documentation."""
        topic = event.payload.get("topic", "")
        logger.info(f"[DOCUMENTATION] Generating documentation for: {topic}")