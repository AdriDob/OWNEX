"""Computer Use Submission Executor — Form filling via desktop automation.

When API submission is unavailable or fails, this executor uses Computer Use
(the perception-action loop) to fill web forms on platforms automatically.

Flow:
    AutoSubmitEngine._submit_to_platform() → ComputerUseExecutor.submit() →
    PlatformFormManager.get_template() → ComputerUseAgent.run(task) → Done

Safety:
    - AutonomyLevel.L2_WITH_APPROVAL for all form submissions
    - Human gate for any financial/payment actions
    - Full audit trail via memory system
    - Dry-run mode for testing
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cores.computer_use.learning import (
    ComputerUseLearner,
    FieldPosition,
    get_computer_use_learner,
)
from cores.computer_use.platform_forms import (
    PlatformFormManager,
    generate_filling_task,
    get_platform_form_manager,
)
from cores.tools.computer_use import (
    ComputerUseAgent,
    ComputerUseConfig,
    ComputerUseResult,
)

logger = logging.getLogger("ownex.computer_use.submission")


@dataclass
class SubmissionTask:
    """A form-filling task for Computer Use to execute."""

    platform: str
    action: str  # "login" | "submit" | "both"
    work_data: dict[str, Any]
    work_item_id: str = ""
    opportunity_title: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class SubmissionResult:
    """Result of a Computer Use submission attempt."""

    success: bool
    platform: str
    task: str
    computer_use_result: ComputerUseResult | None = None
    form_template_used: str = ""
    error: str | None = None
    duration_ms: float = 0.0
    screenshots: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "task": self.task,
            "form_template_used": self.form_template_used,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "screenshots": self.screenshots,
            "computer_use_result": self.computer_use_result.to_dict() if self.computer_use_result else None,
        }


class ComputerUseExecutor:
    """Executes form submissions via Computer Use (desktop automation).

    This is the fallback executor for platforms that don't have API adapters.
    It uses PlatformFormManager to understand the form layout and
    ComputerUseAgent to actually fill and submit it.
    """

    def __init__(
        self,
        form_manager: PlatformFormManager | None = None,
        config: ComputerUseConfig | None = None,
        learner: ComputerUseLearner | None = None,
    ):
        self._form_manager = form_manager or get_platform_form_manager()
        self._config = config or ComputerUseConfig(
            max_steps=30,
            vision_provider="ollama",
            model="moondream",
            step_delay=1.5,
        )
        self._learner = learner or get_computer_use_learner()

    def can_handle(self, platform: str) -> bool:
        """Check if we can submit to this platform via form filling."""
        return self._form_manager.needs_form_filling(platform)

    async def submit(
        self,
        platform: str,
        work_data: dict[str, Any],
        work_item_id: str = "",
        opportunity_title: str = "",
        dry_run: bool = False,
    ) -> SubmissionResult:
        """Submit work to a platform via Computer Use form filling.

        Args:
            platform: Platform identifier (e.g., "outlier", "mindrift")
            work_data: Form data to fill (title, description, severity, etc.)
            work_item_id: WorkBank item ID for tracking
            opportunity_title: Human-readable title
            dry_run: If True, plan but don't execute

        Returns:
            SubmissionResult with success status and details
        """
        start_time = time.time()

        # Get platform template
        template = self._form_manager.get_template(platform)
        if template is None:
            return SubmissionResult(
                success=False,
                platform=platform,
                task="",
                error=f"No form template for platform: {platform}",
            )

        # Generate task for Computer Use
        task = generate_filling_task(template, work_data, action="submit")

        logger.info(
            "[COMPUTER_USE_SUBMIT] Starting form filling for %s: %s",
            platform,
            opportunity_title or work_item_id,
        )

        # Execute via Computer Use
        config = ComputerUseConfig(
            **{**self._config.__dict__, "dry_run": dry_run},
        )
        agent = ComputerUseAgent(config)

        try:
            result = await agent.run(task)
        except Exception as exc:
            return SubmissionResult(
                success=False,
                platform=platform,
                task=task,
                error=f"Computer Use failed: {exc}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Collect screenshots
        screenshots = [s.screenshot_path for s in result.steps if s.screenshot_path]

        duration_ms = (time.time() - start_time) * 1000

        submission_result = SubmissionResult(
            success=result.success,
            platform=platform,
            task=task,
            computer_use_result=result,
            form_template_used=template.platform_id,
            error=result.error,
            duration_ms=duration_ms,
            screenshots=screenshots,
        )

        # Record in learning system
        try:
            if result.success:
                # Extract field positions from the result steps
                positions = []
                for step in result.steps:
                    for action in step.actions_planned:
                        if hasattr(action, "x") and action.x is not None:
                            positions.append(
                                FieldPosition(
                                    field_name=getattr(action, "reasoning", "unknown"),
                                    x=action.x or 0,
                                    y=action.y or 0,
                                    confidence=0.7,
                                )
                            )
                self._learner.record_success(
                    platform=platform,
                    task=task,
                    fields=work_data,
                    positions=positions,
                    duration_ms=duration_ms,
                    steps=result.total_steps,
                    screenshots=screenshots,
                )
            else:
                self._learner.record_failure(
                    platform=platform,
                    task=task,
                    error=result.error or "unknown",
                    duration_ms=duration_ms,
                    steps=result.total_steps,
                    screenshots=screenshots,
                )
        except Exception as exc:
            logger.warning("Failed to record learning data: %s", exc)

        logger.info(
            "[COMPUTER_USE_SUBMIT] %s form filling %s in %.1fs (%d steps)",
            platform,
            "succeeded" if result.success else "failed",
            submission_result.duration_ms / 1000,
            result.total_steps,
        )

        return submission_result

    async def login(
        self,
        platform: str,
        credentials: dict[str, str],
        dry_run: bool = False,
    ) -> SubmissionResult:
        """Log in to a platform via Computer Use.

        Args:
            platform: Platform identifier
            credentials: Dict with email/password (or platform-specific fields)
            dry_run: If True, plan but don't execute

        Returns:
            SubmissionResult
        """
        start_time = time.time()

        template = self._form_manager.get_template(platform)
        if template is None:
            return SubmissionResult(
                success=False,
                platform=platform,
                task="",
                error=f"No form template for platform: {platform}",
            )

        task = generate_filling_task(template, credentials, action="login")

        config = ComputerUseConfig(
            **{**self._config.__dict__, "dry_run": dry_run},
        )
        agent = ComputerUseAgent(config)

        try:
            result = await agent.run(task)
        except Exception as exc:
            return SubmissionResult(
                success=False,
                platform=platform,
                task=task,
                error=f"Computer Use login failed: {exc}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        screenshots = [s.screenshot_path for s in result.steps if s.screenshot_path]

        return SubmissionResult(
            success=result.success,
            platform=platform,
            task=task,
            computer_use_result=result,
            form_template_used=template.platform_id,
            error=result.error,
            duration_ms=(time.time() - start_time) * 1000,
            screenshots=screenshots,
        )


# ── Integration with AutoSubmitEngine ─────────────────────────────


def should_use_computer_use(platform: str, api_submission_failed: bool = False) -> bool:
    """Decide if Computer Use should be used for a submission.

    Returns True when:
    - Platform has no API adapter (needs form filling)
    - API submission failed and form filling is available as fallback
    """
    manager = get_platform_form_manager()

    # If API failed and platform supports form filling, try Computer Use
    if api_submission_failed and manager.needs_form_filling(platform):
        return True

    # If platform only supports form filling, always use Computer Use
    return bool(manager.needs_form_filling(platform))


# ── Singleton ─────────────────────────────────────────────────────

_executor: ComputerUseExecutor | None = None


def get_computer_use_executor(config: ComputerUseConfig | None = None) -> ComputerUseExecutor:
    """Get or create the Computer Use executor singleton."""
    global _executor
    if _executor is None:
        _executor = ComputerUseExecutor(config=config)
    return _executor
