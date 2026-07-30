"""Automation Agent — Operations Department.

Creates hands through workflows and integrations.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.automation")


class AutomationAgent(SpecialistAgent):
    """Automation Agent — Operations Department."""

    def _get_agent_id(self) -> AgentId:
        return AgentId.AUTOMATION

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Create hands through workflows and integrations",
            secondary_objectives=[
                "Create workflows",
                "Build integrations",
                "Develop APIs",
                "Deploy bots",
            ],
            max_concurrent_tasks=5,
            max_execution_time=600,
            available_tools=["playwright", "n8n", "zapier", "api_development"],
            priority_level=4,
            task_preferences=["workflow_creation", "integration_building"],
            handoff_targets=[AgentId.INFRASTRUCTURE],
            handoff_conditions={"workflow_ready": "infrastructure"},
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["playwright", "n8n", "zapier", "api_development"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.INFRASTRUCTURE]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.WORKFLOW_CREATED, EventType.INTEGRATION_BUILT]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.WORKFLOW_CREATED:
            self._handle_workflow(event)

    def _handle_workflow(self, event: AgentEvent) -> None:
        """Handle workflow creation."""
        workflow = event.payload.get("workflow", "")
        logger.info(f"[AUTOMATION] Workflow: {workflow}")
