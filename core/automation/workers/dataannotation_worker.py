"""DataAnnotation Worker — UI automation for DataAnnotation.tech tasks."""

from __future__ import annotations

from typing import Any

from core.automation.browser_agent import BrowserAgent


class DataAnnotationWorker:
    """Worker for DataAnnotation.tech — login, claim tasks, submit work via browser."""

    platform = "dataannotation"

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.browser = BrowserAgent(config)
        self.email = config.get("email", "")
        self.password = config.get("password", "")

    async def login(self) -> dict[str, Any]:
        result = await self.browser.login_dataannotation(self.email, self.password)
        return {"success": result.success, "message": result.message, "error": result.error}

    async def claim_task(self, task_url: str) -> dict[str, Any]:
        result = await self.browser.dataannotation_claim_task(task_url)
        return {"success": result.success, "message": result.message, "error": result.error}

    async def submit_work(self, task_id: str, answer: str) -> dict[str, Any]:
        result = await self.browser.fill("textarea", answer)
        if not result.success:
            return {"success": False, "error": result.error}
        result = await self.browser.click('button:has-text("Submit"), button:has-text("Done")')
        return {"success": result.success, "message": "Answer submitted", "error": result.error}

    async def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        if action == "login":
            self.email = kwargs.get("email", self.email)
            self.password = kwargs.get("password", self.password)
            return await self.login()
        if action == "claim_task":
            return await self.claim_task(kwargs.get("task_url", ""))
        if action == "submit_work":
            return await self.submit_work(kwargs.get("task_id", ""), kwargs.get("answer", ""))
        return {"success": False, "error": f"Unknown action: {action}"}
