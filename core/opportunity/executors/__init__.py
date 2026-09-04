"""Execution Result — unified result type and base executor for all executors."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any


@dataclass
class ExecutionResult:
    """Result of an executor action."""

    success: bool
    action: str
    target: str
    message: str = ""
    error: str | None = None
    data: Any | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class BaseExecutor:
    """Base class for all executors."""

    platform: str = "unknown"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

    def is_enabled(self) -> bool:
        return self.enabled

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        """Execute an action — override in subclass."""
        raise NotImplementedError(f"Action {action} not implemented")

    async def health_check(self) -> ExecutionResult:
        """Check executor health — override in subclass."""
        return ExecutionResult(True, "health_check", self.platform, f"{self.platform} executor healthy")


def get_executors(config: dict[str, Any] | None = None) -> dict[str, BaseExecutor]:
    """Get executor instances for all registered executors."""
    from core.opportunity.executors.algora_executor import AlgoraExecutor
    from core.opportunity.executors.code4rena_executor import Code4renaExecutor
    from core.opportunity.executors.freelancer_executor import FreelancerExecutor
    from core.opportunity.executors.immunefi_executor import ImmunefiExecutor
    from core.opportunity.executors.issuehunt_executor import IssueHuntExecutor
    from core.opportunity.executors.mindrift_executor import MindriftExecutor
    from core.opportunity.executors.opire_executor import OpireExecutor
    from cores.opportunity.executors.platform_workers import (
        DataAnnotationWorker,
        MindriftBrowserWorker,
        OutlierWorker,
        RemotasksWorker,
    )

    _config = config or {}
    executors: dict[str, BaseExecutor] = {}
    for cls in [
        FreelancerExecutor,
        AlgoraExecutor,
        MindriftExecutor,
        OpireExecutor,
        IssueHuntExecutor,
        ImmunefiExecutor,
        Code4renaExecutor,
        DataAnnotationWorker,
        OutlierWorker,
        MindriftBrowserWorker,
        RemotasksWorker,
    ]:
        try:
            name = getattr(cls, "platform", cls.__name__.lower().replace("executor", "").replace("worker", ""))
            executors[name] = cls(_config)
        except Exception:
            pass
    return executors


__all__ = [
    "ExecutionResult",
    "BaseExecutor",
    "FreelancerExecutor",
    "AlgoraExecutor",
    "MindriftExecutor",
    "OpireExecutor",
    "IssueHuntExecutor",
    "Code4renaExecutor",
    "get_executors",
]
