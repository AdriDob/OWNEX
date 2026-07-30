"""Debug Agent — SRE in Build Department.

Finds problems and diagnoses errors.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.debug")


class DebugAgent(SpecialistAgent):
    """Debug Agent — SRE in Build Department."""

    def _get_agent_id(self) -> AgentId:
        return AgentId.DEBUG

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Find problems and diagnose errors",
            secondary_objectives=[
                "Analyze errors",
                "Review logs",
                "Analyze stack traces",
                "Diagnose test failures",
                "Find regressions",
            ],
            max_concurrent_tasks=5,
            max_execution_time=300,
            available_tools=["log_analysis", "stack_trace_analysis", "debugger"],
            priority_level=3,
            task_preferences=["error_diagnosis", "log_analysis"],
            handoff_targets=[AgentId.CODING],
            handoff_conditions={"error_diagnosed": "coding"},
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["log_analysis", "stack_trace_analysis", "debugger"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.CODING]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.ERROR_DETECTED, EventType.ERROR_DIAGNOSED, EventType.ERROR_FIXED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.ERROR_DETECTED:
            self._diagnose_error(event)

    def _diagnose_error(self, event: AgentEvent) -> None:
        """Diagnose error."""
        error = event.payload.get("error", "")
        logger.info(f"[DEBUG] Diagnosing: {error}")
