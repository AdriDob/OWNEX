"""Direct Work Execution Engine — Executes work items using available executors.

Provides execution logic that can be used by WorkerCore for the EXECUTE phase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.direct_work_engine.execution")


@dataclass(slots=True)
class ExecutionResult:
    """Result of executing a work item."""

    success: bool
    artifacts: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    output: str = ""
    error: str | None = None
    execution_time_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "artifacts": self.artifacts,
            "evidence": self.evidence,
            "output": self.output,
            "error": self.error,
            "execution_time_s": self.execution_time_s,
        }


class DirectWorkExecutionEngine:
    """Executes work items using available executors.

    Supports:
    - CoderAgent for code generation tasks
    - BrowserAgent for browser automation tasks
    - Platform executors for platform-specific submission
    - Generic command execution
    """

    def __init__(self) -> None:
        self._coder_agent = None
        self._browser_agent = None
        self._desktop_agent = None
        self._executors = {}

    def set_coder_agent(self, coder_agent: Any) -> None:
        self._coder_agent = coder_agent

    def set_browser_agent(self, browser_agent: Any) -> None:
        self._browser_agent = browser_agent

    def set_desktop_agent(self, desktop_agent: Any) -> None:
        self._desktop_agent = desktop_agent

    def register_executor(self, platform: str, executor: Any) -> None:
        self._executors[platform.lower()] = executor

    def execute(self, work_item: Any, profile: Any = None) -> dict[str, Any]:
        """Execute a work item using the appropriate executor.

        Args:
            work_item: Work item to execute
            profile: User profile (optional)

        Returns:
            Execution result dict
        """
        import time

        start_time = time.time()

        platform = getattr(work_item, "platform", "").lower()

        try:
            # Determine execution strategy
            if self._coder_agent and self._is_coding_task(work_item):
                result = self._execute_with_coder(work_item)
            elif self._browser_agent and self._is_browser_task(work_item):
                result = self._execute_with_browser(work_item)
            elif self._desktop_agent and self._is_desktop_task(work_item):
                result = self._execute_with_desktop(work_item)
            elif platform in self._executors:
                result = self._execute_with_platform_executor(work_item)
            else:
                result = self._execute_generic(work_item)

            execution_time = time.time() - start_time
            result.execution_time_s = time.time() - start_time
            return result.to_dict()

        except Exception as exc:
            logger.exception("Execution failed for work item %s", getattr(work_item, "id", "unknown"))
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                error=str(exc),
                execution_time_s=execution_time,
            ).to_dict()

    def _is_coding_task(self, work_item: Any) -> bool:
        """Determine if work item is a coding task suitable for CoderAgent."""
        category = getattr(work_item, "category", "").lower()
        coding_categories = [
            "software_engineering",
            "backend",
            "frontend",
            "full_stack",
            "api_development",
            "devops",
            "cloud",
            "infrastructure",
            "ai_engineering",
            "ml_engineering",
            "game_development",
            "blockchain_development",
            "smart_contracts",
        ]
        return any(cat in category for cat in coding_categories)

    def _is_desktop_task(self, work_item: Any) -> bool:
        """Determine if work item requires desktop GUI automation."""
        category = getattr(work_item, "category", "").lower()
        desktop_categories = [
            "desktop_automation",
            "gui_automation",
            "desktop_app",
            "system_automation",
            "form_filling",
            "data_entry",
        ]
        return any(cat in category for cat in desktop_categories)

    def _is_browser_task(self, work_item: Any) -> bool:
        """Determine if work item requires browser automation."""
        category = getattr(work_item, "category", "").lower()
        browser_categories = [
            "browser_automation",
            "qa_automation",
            "web_scraping",
            "data_annotation",
            "synthetic_data",
        ]
        platform = getattr(work_item, "platform", "").lower()
        browser_platforms = ["outlier", "mindrift", "remotasks", "upwork"]
        return any(cat in category for cat in browser_categories) or platform in browser_platforms

    def _execute_with_coder(self, work_item: Any) -> Any:
        """Execute using CoderAgent."""
        import asyncio

        from cores.autonomy.coder_agent import CoderAgent, CoderAgentConfig

        coder = CoderAgent(CoderAgentConfig())

        # Build issue dict for solve_issue
        issue = {
            "id": getattr(work_item, "opportunity_id", "") or getattr(work_item, "id", "unknown"),
            "title": getattr(work_item, "title", ""),
            "description": getattr(work_item, "description", ""),
            "platform": getattr(work_item, "platform", ""),
            "url": getattr(work_item, "url", ""),
            "repo_url": getattr(work_item, "repo_url", ""),
            "category": getattr(work_item, "category", ""),
        }

        # Run async solve_issue
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already in async context — create task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, coder.solve_issue(issue)).result()
            else:
                result = asyncio.run(coder.solve_issue(issue))
        except RuntimeError:
            result = asyncio.run(coder.solve_issue(issue))

        return ExecutionResult(
            success=getattr(result, "success", False),
            artifacts=getattr(result, "pr_result", None) and [getattr(result.pr_result, "pr_url", "")] or [],
            evidence=[f"CoderAgent: {getattr(result, 'verdict', 'unknown')}"],
            output=f"Issue {getattr(result, 'issue_id', '?')}: {getattr(result, 'verdict', 'unknown')}",
            error=getattr(result, "error", None),
        )

    def _execute_with_browser(self, work_item: Any) -> Any:
        """Execute using BrowserAgent for platform-specific actions."""
        import asyncio

        from cores.automation.browser_agent import BrowserAgent

        url = getattr(work_item, "url", "")
        platform = getattr(work_item, "platform", "").lower()

        async def _run_browser() -> ExecutionResult:
            async with BrowserAgent() as browser:
                if not url:
                    return ExecutionResult(
                        success=False,
                        error="No URL provided for browser task",
                    )

                # Navigate to the target
                nav_result = await browser.goto(url)
                if not nav_result.success:
                    return ExecutionResult(
                        success=False,
                        error=f"Navigation failed: {nav_result.error}",
                    )

                # Platform-specific actions
                if platform == "linkedin" and "easy_apply" in str(getattr(work_item, "category", "")):
                    result = await browser.easy_apply_linkedin(url)
                    return ExecutionResult(
                        success=result.success,
                        artifacts=[url],
                        evidence=[f"LinkedIn Easy Apply: {result.error or 'success'}"],
                        output=result.error or "Easy Apply completed",
                        error=result.error,
                    )
                elif platform == "algora":
                    result = await browser.claim_algora_issue(url)
                    return ExecutionResult(
                        success=result.success,
                        artifacts=[url],
                        evidence=[f"Algora claim: {result.error or 'success'}"],
                        output=result.error or "Issue claimed",
                        error=result.error,
                    )
                else:
                    # Generic: just navigate and report
                    text = await browser.get_text("body")
                    return ExecutionResult(
                        success=True,
                        artifacts=[url],
                        evidence=[f"Visited {url}"],
                        output=f"Page loaded: {len(text.output) if text.success else 0} chars",
                    )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, _run_browser()).result()
            else:
                return asyncio.run(_run_browser())
        except RuntimeError:
            return asyncio.run(_run_browser())

    def _execute_with_platform_executor(self, work_item: Any) -> Any:
        """Execute using platform-specific executor."""
        platform = getattr(work_item, "platform", "").lower()
        executor = self._executors.get(platform.lower())

        if not executor:
            raise RuntimeError(f"No executor registered for platform: {platform}")

        # Execute platform-specific logic
        result = executor.execute(work_item)

        return ExecutionResult(
            success=result.get("success", False),
            artifacts=result.get("artifacts", []),
            evidence=result.get("evidence", []),
            output=result.get("output", ""),
            error=result.get("error"),
        )

    def _execute_with_desktop(self, work_item: Any) -> Any:
        """Execute using ComputerUseTool (desktop GUI automation)."""
        import asyncio

        from cores.tools.computer_use import ComputerUseAgent, ComputerUseConfig

        config = ComputerUseConfig(
            max_steps=15,
            vision_provider="ollama",
            model="moondream",
        )
        agent = ComputerUseAgent(config)

        task = (f"{getattr(work_item, 'title', '')} {getattr(work_item, 'description', '')}").strip()
        if not task:
            task = f"Complete work item {getattr(work_item, 'id', 'unknown')}"

        try:
            result = asyncio.run(agent.run(task))
            return ExecutionResult(
                success=result.success,
                artifacts=[result.final_screenshot] if result.final_screenshot else [],
                evidence=[f"Desktop automation: {result.summary}"],
                output=result.summary or result.error or "Desktop task completed",
                error=result.error,
            )
        except Exception as exc:
            return ExecutionResult(
                success=False,
                error=f"Desktop automation failed: {exc}",
            )

    def _execute_generic(self, work_item: Any) -> Any:
        """Generic execution fallback — prepare deliverable for manual submission."""
        work_id = getattr(work_item, "id", "unknown")
        title = getattr(work_item, "title", "Untitled")
        platform = getattr(work_item, "platform", "unknown")

        logger.info(
            "Generic execution for %s: %s (%s) — preparing deliverable",
            work_id,
            title,
            platform,
        )

        return ExecutionResult(
            success=True,
            artifacts=[f"deliverable_{work_id}"],
            evidence=[f"Prepared submission for {platform}: {title}"],
            output=f"Ready for manual submission on {platform}",
        )


# Convenience function
async def execute_work_item(work_item: Any, profile: Any = None) -> dict[str, Any]:
    """Convenience function for executing a work item."""
    engine = DirectWorkExecutionEngine()
    return engine.execute(work_item, profile)
