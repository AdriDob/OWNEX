"""Remotasks Worker — UI automation for Remotasks.com tasks."""

from __future__ import annotations

from typing import Any

from core.automation.browser_agent import BrowserAgent


class RemotasksWorker:
    """Worker for Remotasks — login, claim tasks, submit work via browser."""

    platform = "remotasks"

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.browser = BrowserAgent(config)

    async def login(self, email: str = "", password: str = "") -> dict[str, Any]:
        result = await self.browser.goto("https://remotasks.com/login")
        if not result.success:
            return {"success": False, "error": result.error}
        if email:
            await self.browser.fill('input[name="email"]', email)
        if password:
            await self.browser.fill('input[name="password"]', password)
        submit = await self.browser.click('button[type="submit"]')
        return {"success": submit.success, "message": "Logged in" if submit.success else "Login failed"}

    async def claim_task(self, task_url: str) -> dict[str, Any]:
        result = await self.browser.goto(task_url)
        if not result.success:
            return {"success": False, "error": result.error}
        claim = await self.browser.click('button:has-text("Claim"), button:has-text("Start Task")')
        return {"success": claim.success, "message": "Task claimed" if claim.success else claim.error}

    async def submit_task(self, task_id: str, answer: str = "") -> dict[str, Any]:
        if answer:
            await self.browser.fill("textarea", answer)
        submit = await self.browser.click('button:has-text("Submit"), button:has-text("Done")')
        return {"success": submit.success, "message": "Submitted", "error": submit.error}

    async def execute(self, action: str, **kwargs: Any) -> dict[str, Any]:
        if action == "login":
            return await self.login(kwargs.get("email", ""), kwargs.get("password", ""))
        if action == "claim_task":
            return await self.claim_task(kwargs.get("task_url", ""))
        if action == "submit_task":
            return await self.submit_task(kwargs.get("task_id", ""), kwargs.get("answer", ""))
        return {"success": False, "error": f"Unknown action: {action}"}
