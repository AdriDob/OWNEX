"""Evolution Agent — Strategic Department.

Improves OWNEX through audits and improvements.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.evolution")


class EvolutionAgent(SpecialistAgent):
    """Evolution Agent — Strategic Department."""

    def _get_agent_id(self) -> AgentId:
        return AgentId.EVOLUTION

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Improve OWNEX through audits and improvements",
            secondary_objectives=[
                "Periodic audits",
                "Detect improvements",
                "Propose changes",
                "Analyze future architecture",
            ],
            max_concurrent_tasks=3,
            max_execution_time=600,
            available_tools=["system_analysis", "trend_watching", "architecture_review"],
            priority_level=6,
            task_preferences=["system_audit", "improvement_proposal"],
            handoff_targets=[AgentId.ORCHESTRATOR],
            handoff_conditions={"improvement_suggested": "orchestrator"},
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["system_analysis", "trend_watching", "architecture_review"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.ORCHESTRATOR]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.SYSTEM_AUDIT, EventType.IMPROVEMENT_SUGGESTED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.SYSTEM_AUDIT:
            self._run_audit(event)

    def _run_audit(self, event: AgentEvent) -> None:
        """Run system audit."""
        scope = event.payload.get("scope", "")
        logger.info(f"[EVOLUTION] Auditing: {scope}")
