"""Mindrift Executor — Claim tasks, solve, and submit work on Mindrift.io."""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.opportunity.executors import BaseExecutor, ExecutionResult


class MindriftExecutor(BaseExecutor):
    """Executor for Mindrift.io — claim AI data tasks and submit solutions."""

    platform = "mindrift"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.token = self.config.get("token") or os.getenv("MINDRIFT_EMAIL")
        self.base_url = self.config.get("base_url", "https://api.mindrift.io/v1")

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        if action == "claim_task":
            return await self.claim_task(kwargs.get("task_id", ""))
        if action == "submit_task":
            return await self.submit_task(
                kwargs.get("task_id", ""),
                kwargs.get("solution_url", ""),
                kwargs.get("description", ""),
            )
        if action == "get_tasks":
            return await self.get_tasks(kwargs.get("status", "open"))
        if action == "health_check":
            return await self.health_check()
        return ExecutionResult(False, action, "", error=f"Unknown action: {action}")

    async def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}" if self.token else "",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def claim_task(self, task_id: str) -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "claim_task", task_id, error="MINDRIFT_EMAIL not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/tasks/{task_id}/claim",
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "claim_task", task_id, data={"response": data})
                return ExecutionResult(
                    False, "claim_task", task_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "claim_task", task_id, error=str(e))

    async def submit_task(self, task_id: str, solution_url: str, description: str = "") -> ExecutionResult:
        if not self.token:
            return ExecutionResult(False, "submit_task", task_id, error="MINDRIFT_EMAIL not configured")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/tasks/{task_id}/submit",
                    headers=await self._headers(),
                    json={
                        "solution_url": solution_url,
                        "description": description or "Automated submission via OWNEX CoderAgent",
                    },
                    timeout=30,
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return ExecutionResult(True, "submit_task", task_id, data={"response": data})
                return ExecutionResult(
                    False, "submit_task", task_id, error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            except Exception as e:
                return ExecutionResult(False, "submit_task", task_id, error=str(e))

    async def get_tasks(self, status: str = "open") -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/tasks",
                    params={"status": status},
                    headers=await self._headers(),
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return ExecutionResult(True, "get_tasks", status, data={"tasks": data})
                return ExecutionResult(False, "get_tasks", status, error=f"HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                return ExecutionResult(False, "get_tasks", status, error=str(e))

    async def health_check(self) -> ExecutionResult:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health", timeout=15)
                return ExecutionResult(resp.status_code == 200, "health_check", self.base_url)
            except Exception as e:
                return ExecutionResult(False, "health_check", self.base_url, error=str(e))


async def claim(task_id: str | None = None) -> ExecutionResult:
    """Top-level claim function for scheduler handler.

    References: ``core.opportunity.executors.mindrift_executor:claim``
    """
    executor = MindriftExecutor()
    if task_id:
        return await executor.claim_task(task_id)
    # Find first available task and claim it
    tasks_result = await executor.get_tasks("open")
    if not tasks_result.success or not tasks_result.data:
        return ExecutionResult(False, "claim", task_id, error="No open tasks available")
    tasks = tasks_result.data.get("tasks", [])
    if not tasks:
        return ExecutionResult(False, "claim", task_id, error="No open tasks available")
    first_task_id = tasks[0].get("id") if isinstance(tasks[0], dict) and "id" in tasks[0] else str(tasks[0])
    return await executor.claim_task(first_task_id)
