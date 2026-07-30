"""Product Agent — Business Department.

Thinks like a user and defines features.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.product")


class ProductAgent(SpecialistAgent):
    """Product Agent — Business Department."""

    def _get_agent_id(self) -> AgentId:
        return AgentId.PRODUCT

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Think like user and define features",
            secondary_objectives=[
                "UX/UI design",
                "Feature prioritization",
                "Roadmap management",
                "Detect valuable features",
            ],
            max_concurrent_tasks=5,
            max_execution_time=300,
            available_tools=["user_research", "prototyping", "analytics"],
            priority_level=3,
            task_preferences=["ux_review", "feature_definition"],
            handoff_targets=[AgentId.CODING, AgentId.ORCHESTRATOR],
            handoff_conditions={"feature_defined": "coding"},
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["user_research", "prototyping", "analytics"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.CODING, AgentId.ORCHESTRATOR]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.FEATURE_REQUESTED, EventType.UX_REVIEW, EventType.PRIORITY_UPDATED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.FEATURE_REQUESTED:
            self._define_feature(event)

    def _define_feature(self, event: AgentEvent) -> None:
        """Define feature."""
        feature = event.payload.get("feature", "")
        logger.info(f"[PRODUCT] Defining: {feature}")
