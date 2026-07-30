"""QA Agent — Quality Gatekeeper in Quality Department.

Prevents things from breaking through testing.
"""

from __future__ import annotations

import logging

from cores.agents.specialist import SpecialistAgent, SpecialistConfig
from cores.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("ownex.agents.departments.qa")


class QAAgent(SpecialistAgent):
    """QA Agent — Quality Gatekeeper in Quality Department.

    Prevents things from breaking through testing.

    Objectives:
    - Primary: Unit tests, integration tests, E2E tests, validation
    - Secondary: Quality gate, approval/denial, regression prevention

    Limits:
    - Max 8 concurrent QA tasks
    - Max 600s per test suite

    Tools:
    - pytest
    - vitest
    - coverage tools
    - E2E frameworks

    Priorities:
    - Priority level: 5
    - Task preferences: test execution, quality checks

    Handoffs:
    - Receives from: Coding
    - Hands off to: Coding (if failed), Orchestrator (if approved)
    """

    def _get_agent_id(self) -> AgentId:
        return AgentId.QA

    def _get_default_config(self) -> SpecialistConfig:
        return SpecialistConfig(
            primary_objective="Unit tests, integration tests, E2E tests, validation",
            secondary_objectives=[
                "Quality gate for code changes",
                "Approval/denial of PRs",
                "Regression prevention",
                "Coverage analysis",
            ],
            max_concurrent_tasks=8,
            max_execution_time=600,
            available_tools=[
                "pytest",
                "vitest",
                "coverage",
                "e2e_frameworks",
                "test_runners",
            ],
            priority_level=5,
            task_preferences=["test_execution", "quality_checks"],
            handoff_targets=[AgentId.CODING, AgentId.ORCHESTRATOR],
            handoff_conditions={
                "test_failed": "coding",
                "approval_granted": "orchestrator",
            },
        )

    def _get_specialist_tools(self) -> list[str]:
        return ["pytest", "vitest", "coverage", "e2e_frameworks"]

    def _get_handoff_targets(self) -> list[AgentId]:
        return [AgentId.CODING, AgentId.ORCHESTRATOR]

    def _get_subscriptions(self) -> list[EventType | str]:
        return [EventType.TEST_REQUESTED, EventType.TEST_EXECUTED, EventType.TEST_FAILED, EventType.APPROVAL_GRANTED]

    def handle_event(self, event: AgentEvent) -> None:
        if event.event_type == EventType.TEST_REQUESTED:
            self._run_tests(event)
        elif event.event_type == EventType.TEST_FAILED:
            self._handle_test_failure(event)

    def _run_tests(self, event: AgentEvent) -> None:
        """Run tests for the requested feature."""
        feature = event.payload.get("feature", "")
        logger.info(f"[QA] Running tests for: {feature}")

    def _handle_test_failure(self, event: AgentEvent) -> None:
        """Handle test failure."""
        test = event.payload.get("test", "")
        error = event.payload.get("error", "")
        logger.warning(f"[QA] Test failed: {test} - {error}")
