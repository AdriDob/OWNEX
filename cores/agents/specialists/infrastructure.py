"""Infrastructure Agent — Operations Department.

Keeps the machine alive through maintenance.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.infrastructure")


class InfrastructureAgent(SpecialistAgent):
    """Infrastructure Agent — Operations Department."""

    def _get_agent_id(self) -> AgentId:
        return AgentId.INFRASTRUCTURE

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Keep the machine alive through maintenance",
            secondary_objectives=[
                "Docker management",
                "Server maintenance",
                "Windows build",
                "Backups",
                "Updates",
            ],
            max_concurrent_tasks=3,
            max_execution_time=600,
            available_tools=["docker", "ci_cd", "monitoring", "backup_systems"],
            priority_level=5,
            task_preferences=["infrastructure_maintenance", "deployment"],
            handoff_targets=[AgentId.ORCHESTRATOR],
            handoff_conditions={"infrastructure_updated": "orchestrator"},
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["docker", "ci_cd", "monitoring", "backup_systems"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.ORCHESTRATOR]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.INFRASTRUCTURE_UPDATED, EventType.DEPLOYMENT_COMPLETED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.INFRASTRUCTURE_UPDATED:
            self._handle_infrastructure(event)

    def _handle_infrastructure(self, event: AgentEvent) -> None:
        """Handle infrastructure update."""
        update = event.payload.get("update", "")
        logger.info(f"[INFRASTRUCTURE] Update: {update}")
