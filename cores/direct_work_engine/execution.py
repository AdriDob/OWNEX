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
        from cores.autonomy.coder_agent import get_coder_agent

        coder = get_coder_agent()
        if not coder:
            raise RuntimeError("CoderAgent not available")

        # Prepare task for CoderAgent
        task = {
            "type": "code_generation",
            "description": getattr(work_item, "description", ""),
            "title": getattr(work_item, "title", ""),
            "platform": getattr(work_item, "platform", ""),
            "category": getattr(work_item, "category", ""),
            "requirements": getattr(work_item, "skills_required", []),
            "technologies": getattr(work_item, "technologies", []),
        }

        # Execute CoderAgent pipeline
        result = coder.execute_task(task)

        return ExecutionResult(
            success=result.get("success", False),
            artifacts=result.get("artifacts", []),
            evidence=result.get("evidence", []),
            output=result.get("output", ""),
            error=result.get("error"),
        )

    def _execute_with_browser(self, work_item: Any) -> Any:
        """Execute using BrowserAgent."""
        from cores.automation.browser_agent import BrowserAgent

        browser = BrowserAgent()
        if not browser.is_available():
            raise RuntimeError("BrowserAgent not available")

        # Prepare browser task
        task = {
            "url": getattr(work_item, "url", ""),
            "actions": getattr(work_item, "browser_actions", []),
            "platform": getattr(work_item, "platform", ""),
        }

        result = browser.execute_task(task)

        return ExecutionResult(
            success=result.get("success", False),
            artifacts=result.get("artifacts", []),
            evidence=result.get("evidence", []),
            output=result.get("output", ""),
            error=result.get("error"),
        )

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
        """Generic execution fallback."""
        # For now, just mark as prepared
        logger.info("Generic execution for work item %s", getattr(work_item, "id", "unknown"))

        return ExecutionResult(
            success=True,
            artifacts=[f"prepared_{getattr(work_item, 'id', 'unknown')}"],
            evidence=["Work item prepared for manual execution"],
            output="Work item prepared for manual execution",
        )


# Convenience function
async def execute_work_item(work_item: Any, profile: Any = None) -> dict[str, Any]:
    """Convenience function for executing a work item."""
    engine = DirectWorkExecutionEngine()
    return engine.execute(work_item, profile)
