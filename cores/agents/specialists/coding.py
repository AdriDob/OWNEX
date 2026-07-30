"""Coding Agent — Developer in Build Department.

Implements code based on architecture decisions.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.coding")


class CodingAgent(SpecialistAgent):
    """Coding Agent — Developer in Build Department.

    Implements code based on architecture decisions.

    Objectives:
    - Primary: Write code, modify files, create features, refactor
    - Secondary: Apply fixes, implement PRs, optimize performance

    Limits:
    - Never makes architectural decisions
    - Max 5 concurrent coding tasks
    - Max 900s per coding operation

    Tools:
    - Aider (refactors masivos)
    - CoderAgent
    - OpenCode
    - Devin (cuando necesario)

    Priorities:
    - Priority level: 2
    - Task preferences: code generation, refactoring, implementation

    Handoffs:
    - Receives from: Architecture, Product, Debug
    - Hands off to: QA, Debug
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.CODING

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Write code, modify files, create features, refactor",
            secondary_objectives=[
                "Apply bug fixes",
                "Create pull requests",
                "Optimize code performance",
                "Follow architecture decisions",
            ],
            max_concurrent_tasks=5,
            max_execution_time=900,
            available_tools=[
                "aider",
                "opencode",
                "devin",
                "coder_agent",
                "refactoring",
                "pr_creation",
            ],
            priority_level=2,
            task_preferences=["code_generation", "refactoring", "implementation"],
            handoff_targets=[AgentId.QA, AgentId.DEBUG],
            handoff_conditions={
                "code_review_needed": "qa",
                "error_detected": "debug",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["aider", "opencode", "devin", "coder_agent", "refactoring"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.QA, AgentId.DEBUG]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.CODE_REQUESTED, EventType.FEATURE_IMPLEMENTED, EventType.ERROR_FIXED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.CODE_REQUESTED:
            self._implement_code(event)
        elif event.event_type == EventType.FEATURE_IMPLEMENTED:
            self._feature_completed(event)

    def _implement_code(self, event: AgentEvent) -> None:
        """Implement code for the requested task."""
        task = event.payload.get("task", "")
        logger.info(f"[CODING] Implementing: {task}")

    def _feature_completed(self, event: AgentEvent) -> None:
        """Handle feature completion."""
        feature = event.payload.get("feature", "")
        logger.info(f"[CODING] Feature completed: {feature}")
