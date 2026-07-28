"""Tests for OutlierExecutor — claim tasks, submit answers, get details via BrowserAgent."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from core.opportunity.executors.outlier_executor import OutlierExecutor


@pytest.fixture
def executor():
    return OutlierExecutor()


class TestOutlierExecutorTaskFlow:
    def test_claim_and_solve_success(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.claim_outlier_task = AsyncMock(return_value={"success": True, "task_id": "t1"})
            executor.browser_agent.solve_outlier_task = AsyncMock(return_value={"success": True, "solved": True})

            result = await executor.claim_and_solve_task("t1", {"type": "analytical"})
            assert result.success is True
            assert result.data["status"] == "completed"

        asyncio.run(run())

    def test_claim_and_solve_claim_fails(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.claim_outlier_task = AsyncMock(
                return_value={"success": False, "error": "no tasks available"}
            )

            result = await executor.claim_and_solve_task("t1", {})
            assert result.success is False
            assert "no tasks available" in result.error

        asyncio.run(run())

    def test_claim_and_solve_requires_task_id(self, executor):
        result = asyncio.run(executor.claim_and_solve_task("", {}))
        assert result.success is False
        assert "Task ID required" in result.error

    def test_claim_and_solve_handles_exception(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.claim_outlier_task = AsyncMock(side_effect=RuntimeError("browser crashed"))

            result = await executor.claim_and_solve_task("t1", {})
            assert result.success is False
            assert "browser crashed" in result.error

        asyncio.run(run())


class TestOutlierExecutorSubmitAnswer:
    def test_submit_answer_success(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.submit_outlier_answer = AsyncMock(return_value={"success": True, "submitted": True})

            result = await executor.submit_answer("t1", "answer text", 0.95)
            assert result.success is True
            assert result.data["answer_submitted"] is True
            assert result.data["confidence"] == 0.95

        asyncio.run(run())

    def test_submit_answer_fails(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.submit_outlier_answer = AsyncMock(
                return_value={"success": False, "error": "invalid answer"}
            )

            result = await executor.submit_answer("t1", "bad answer", 0.5)
            assert result.success is False
            assert "invalid answer" in result.error

        asyncio.run(run())

    def test_submit_answer_requires_task_id(self, executor):
        result = asyncio.run(executor.submit_answer("", "answer", 0.5))
        assert result.success is False
        assert "Task ID required" in result.error


class TestOutlierExecutorGetTaskDetails:
    def test_get_task_details_success(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.get_outlier_task_details = AsyncMock(
                return_value={"success": True, "title": "Task 1", "timestamp": "2026-07-28"}
            )

            result = await executor.get_task_details("t1")
            assert result.success is True
            assert result.data["task_details"]["title"] == "Task 1"

        asyncio.run(run())

    def test_get_task_details_fails(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.get_outlier_task_details = AsyncMock(
                return_value={"success": False, "error": "not found"}
            )

            result = await executor.get_task_details("t1")
            assert result.success is False
            assert "not found" in result.error

        asyncio.run(run())


class TestOutlierExecutorHealth:
    def test_health_check_success(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.health_check = AsyncMock(return_value={"success": True})

            result = await executor.health_check()
            assert result.success is True

        asyncio.run(run())

    def test_health_check_browser_unhealthy(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.health_check = AsyncMock(
                return_value={"success": False, "error": "browser not responding"}
            )

            result = await executor.health_check()
            assert result.success is False
            assert "browser not responding" in result.error

        asyncio.run(run())

    def test_health_check_no_health_method(self, executor):
        async def run():
            executor.browser_agent = AsyncMock(spec=[])
            result = await executor.health_check()
            assert result.success is True

        asyncio.run(run())


class TestOutlierExecutorDispatch:
    def test_dispatch_claim_and_solve(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.claim_outlier_task = AsyncMock(return_value={"success": True, "task_id": "t1"})
            executor.browser_agent.solve_outlier_task = AsyncMock(return_value={"success": True})

            result = await executor.execute("claim_and_solve", task_id="t1", task_data={})
            assert result.success is True

        asyncio.run(run())

    def test_dispatch_submit_answer(self, executor):
        async def run():
            executor.browser_agent = AsyncMock()
            executor.browser_agent.submit_outlier_answer = AsyncMock(return_value={"success": True, "submitted": True})

            result = await executor.execute("submit_answer", task_id="t1", answer="a", confidence=0.9)
            assert result.success is True

        asyncio.run(run())

    def test_dispatch_unknown_action(self, executor):
        result = asyncio.run(executor.execute("nonexistent"))
        assert result.success is False
        assert "Unknown action" in result.error
