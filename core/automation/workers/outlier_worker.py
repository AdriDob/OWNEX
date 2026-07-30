"""Outlier Worker — UI automation for Outlier.ai tasks."""

from __future__ import annotations

from typing import Any

from core.automation.browser_agent import BrowserAgent


class OutlierWorker:
    """Worker for Outlier.ai — login, claim tasks, submit work via browser."""

    platform = "outlier"

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.browser = BrowserAgent(config)
        self.auto_login = config.get("auto_login", False)

    async def claim_and_solve_task(self, task_id: str, task_data: dict[str, Any]) -> dict[str, Any]:
        claim_result = await self.browser.outlier_claim_task(task_data.get("task_url", ""))
        return {"success": claim_result.success, "message": claim_result.message, "error": claim_result.error}

    async def submit_answer(self, task_id: str, answer: str, confidence: float) -> dict[str, Any]:
        fill_result = await self.browser.fill("textarea", answer)
        if not fill_result.success:
            return {"success": False, "error": fill_result.error}
        submit_result = await self.browser.click('button:has-text("Submit"), button:has-text("Done")')
        return {"success": submit_result.success, "answer": answer, "error": submit_result.error}

    async def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        if action == "claim_and_solve_task":
            return await self.claim_and_solve_task(kwargs.get("task_id", ""), kwargs.get("task_data", {}))
        if action == "submit_answer":
            return await self.submit_answer(
                kwargs.get("task_id", ""), kwargs.get("answer", ""), kwargs.get("confidence", 0.0)
            )
        return {"success": False, "error": f"Unknown action: {action}"}
