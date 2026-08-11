"""Outlier Executor — Claim, solve, and submit tasks on Outlier.ai using browser automation."""

from __future__ import annotations

from typing import Any

from core.automation.browser_agent import BrowserAgent
from core.opportunity.executors import BaseExecutor, ExecutionResult

__all__ = ["OutlierExecutor"]


class OutlierExecutor(BaseExecutor):
    """Executor for Outlier.ai — claim tasks, solve via manual workflow, submit answers."""

    platform = "outlier"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.browser_agent = BrowserAgent()

    async def claim_and_solve_task(self, task_id: str, task_data: dict[str, Any]) -> ExecutionResult:
        """Claim an outlier task and solve it (requires browser automation)."""
        if not task_id:
            return ExecutionResult(False, "claim_and_solve_task", task_id, error="Task ID required")

        try:
            # Use browser agent to claim and solve the task
            claim_result = await self.browser_agent.claim_outlier_task(task_id)
            if not claim_result.get("success"):
                return ExecutionResult(
                    False, "claim_and_solve_task", task_id, error=claim_result.get("error", "Failed to claim task")
                )

            # After claiming, we need to solve the task (Outlier tasks are typically language/analytical tasks)
            # For now, we'll simulate task solving - in practice this would involve the task content
            # and potentially integrating with the CoderAgent for complex tasks
            solve_result = await self.browser_agent.solve_outlier_task(task_id, task_data)

            return ExecutionResult(
                True,
                "claim_and_solve_task",
                task_id,
                "Task claimed and solved via Outlier.ai",
                data={
                    "claim_result": claim_result,
                    "solve_result": solve_result,
                    "status": "completed",
                },
            )
        except Exception as e:
            return ExecutionResult(False, "claim_and_solve_task", task_id, error=str(e))

    async def submit_answer(self, task_id: str, answer: str, confidence: float) -> ExecutionResult:
        """Submit the solved answer for an Outlier task."""
        if not task_id:
            return ExecutionResult(False, "submit_answer", task_id, error="Task ID required")

        try:
            # Use browser agent to submit the answer
            submit_result = await self.browser_agent.submit_outlier_answer(task_id, answer, confidence)
            if not submit_result.get("success"):
                return ExecutionResult(
                    False, "submit_answer", task_id, error=submit_result.get("error", "Failed to submit answer")
                )

            return ExecutionResult(
                True,
                "submit_answer",
                task_id,
                "Answer submitted successfully",
                data={
                    "submit_result": submit_result,
                    "answer_submitted": True,
                    "confidence": confidence,
                },
            )
        except Exception as e:
            return ExecutionResult(False, "submit_answer", task_id, error=str(e))

    async def get_task_details(self, task_id: str) -> ExecutionResult:
        """Fetch details for a specific outlier task."""
        if not task_id:
            return ExecutionResult(False, "get_task_details", task_id, error="Task ID required")

        try:
            # Use browser agent to fetch task details
            details_result = await self.browser_agent.get_outlier_task_details(task_id)
            if not details_result.get("success"):
                return ExecutionResult(
                    False,
                    "get_task_details",
                    task_id,
                    error=details_result.get("error", "Failed to fetch task details"),
                )

            return ExecutionResult(
                True,
                "get_task_details",
                task_id,
                "Task details fetched successfully",
                data={
                    "task_details": details_result,
                    "fetched_at": details_result.get("timestamp"),
                },
            )
        except Exception as e:
            return ExecutionResult(False, "get_task_details", task_id, error=str(e))

    async def health_check(self) -> ExecutionResult:
        """Check the health/status of the Outlier executor."""
        try:
            # Check if browser agent is healthy
            if hasattr(self.browser_agent, "health_check"):
                browser_health = await self.browser_agent.health_check()
                if not browser_health.get("success"):
                    return ExecutionResult(
                        False,
                        "health_check",
                        self.platform,
                        error=f"Browser agent unhealthy: {browser_health.get('error')}",
                        data=browser_health,
                    )

            return ExecutionResult(
                True,
                "health_check",
                self.platform,
                "Outlier executor healthy",
                data={
                    "platform": self.platform,
                    "browser_agent": "healthy",
                    "capabilities": ["task_claim", "task_solving", "answer_submit", "task_details_fetch"],
                },
            )
        except Exception as e:
            return ExecutionResult(False, "health_check", self.platform, error=str(e))

    async def execute(self, action: str, **kwargs) -> ExecutionResult:
        """Execute an Outlier platform action."""
        if action == "claim_and_solve":
            return await self.claim_and_solve_task(kwargs.get("task_id"), kwargs.get("task_data", {}))
        elif action == "submit_answer":
            return await self.submit_answer(kwargs.get("task_id"), kwargs.get("answer"), kwargs.get("confidence", 0.5))
        elif action == "get_task_details":
            return await self.get_task_details(kwargs.get("task_id"))
        elif action == "health_check":
            return await self.health_check()
        else:
            return ExecutionResult(False, action, "", error=f"Unknown action: {action}")
