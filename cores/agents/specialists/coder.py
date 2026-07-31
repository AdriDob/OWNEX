"""Coder Specialist — Code generation, refactoring, and implementation."""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.specialists.coder")


class CoderAgent(SpecialistAgent):
    """Coder — Code generation and implementation specialist.

    Objectives:
    - Primary: Generate, refactor, and implement code
    - Secondary: Create PRs, apply fixes, optimize performance

    Limits:
    - Max 5 concurrent coding tasks
    - Max 900s per coding operation

    Tools:
    - Code generation (Devin, OpenCode)
    - Refactoring tools
    - PR creation
    - Testing integration

    Priorities:
    - Priority level: 3
    - Task preferences: code generation, refactoring

    Handoffs:
    - Receives from: Commander, Planner, Research
    - Hands off to: Reviewer, Documentation
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.CODER

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Generate, refactor, and implement code",
            secondary_objectives=[
                "Create pull requests",
                "Apply bug fixes",
                "Optimize code performance",
                "Ensure code quality",
            ],
            max_concurrent_tasks=5,
            max_execution_time=900,
            available_tools=[
                "code_generation",
                "refactoring",
                "pr_creation",
                "testing",
                "linting",
            ],
            priority_level=3,
            task_preferences=["code_generation", "refactoring"],
            handoff_targets=[AgentId.REVIEWER, AgentId.DOCUMENTATION],
            handoff_conditions={
                "code_review_needed": "reviewer",
                "documentation_needed": "documentation",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["code_generation", "refactoring", "pr_creation", "testing"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.REVIEWER, AgentId.DOCUMENTATION]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.CODE_REQUESTED, EventType.FIX_APPLIED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.CODE_REQUESTED:
            self._generate_code(event)

    def _generate_code(self, event: AgentEvent) -> None:
        """Generate code for the requested task."""
        task = event.payload.get("task", "")
        logger.info(f"[CODER] Generating code for: {task}")
        # Implement code generation logic
