"""Execution Result — unified result type and base executor for all executors."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any

from core.security.credential_broker import AccessLevel, get_credential_broker

logger = logging.getLogger(__name__)

# Environment names a provider secret may arrive under, in priority order.
CREDENTIAL_ENV_SUFFIXES: tuple[str, ...] = ("_TOKEN", "_API_KEY", "_PASSWORD")


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


def env_credential(provider: str) -> str | None:
    """Read a provider secret from the environment (legacy, unscoped source)."""
    for suffix in CREDENTIAL_ENV_SUFFIXES:
        value = os.getenv(f"{provider.upper()}{suffix}")
        if value:
            return value
    return None


class BaseExecutor:
    """Base class for all executors.

    Credentials are resolved through the project-scoped credential broker: an
    executor asks for a provider secret for its own project (``project_id``,
    defaulting to the platform it belongs to) and the broker enforces the access
    level, expiration and audit trail. Nothing is cached on the instance, so a
    revoked or expired credential stops working immediately.

    ``credential_sources`` maps a provider to the config key that may still carry
    its secret. That config/env path is kept only as a migration fallback and is
    logged as unscoped whenever it is used.
    """

    platform: str = "unknown"
    credential_sources: dict[str, str] = {}
    # provider -> explicit environment variable that carries its secret
    credential_env: dict[str, str] = {}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.project_id = str(self.config.get("project_id") or self.platform)

    def is_enabled(self) -> bool:
        return self.enabled

    def get_config(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def credential(
        self,
        provider: str,
        required_level: AccessLevel = AccessLevel.EXECUTION,
    ) -> str | None:
        """Resolve a credential for this executor's project.

        Once the project has an assignment for ``provider``, the broker is the
        only source: an expired or under-privileged assignment returns None
        instead of silently falling back to the global config/env secret.
        """
        broker = get_credential_broker()
        granted = broker.resolve_credential(self.project_id, provider, required_level)
        if granted is not None:
            return granted.value

        if broker.has_credential(self.project_id, provider):
            logger.warning(
                "%s credential for project %s is assigned but unusable (expired or "
                "insufficient access level) — refusing the unscoped fallback",
                provider,
                self.project_id,
            )
            return None

        config_key = self.credential_sources.get(provider)
        fallback = self.config.get(config_key) if config_key else None
        explicit_env = self.credential_env.get(provider)
        fallback = (
            fallback
            or (os.getenv(explicit_env) if explicit_env else None)
            or env_credential(provider)
        )
        if fallback:
            logger.warning(
                "Using UNscoped %s credential from config/env for project %s — "
                "assign it to the credential broker to get audit/expiry enforcement",
                provider,
                self.project_id,
            )
        return fallback

    async def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        """Execute an action — override in subclass."""
        raise NotImplementedError(f"Action {action} not implemented")

    async def health_check(self) -> ExecutionResult:
        """Check executor health — override in subclass."""
        return ExecutionResult(True, "health_check", self.platform, f"{self.platform} executor healthy")


def get_executors(config: dict[str, Any] | None = None) -> dict[str, BaseExecutor]:
    """Get executor instances for all registered executors."""
    from core.opportunity.executors.algora_executor import AlgoraExecutor
    from core.opportunity.executors.freelancer_executor import FreelancerExecutor
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
    "CREDENTIAL_ENV_SUFFIXES",
    "ExecutionResult",
    "BaseExecutor",
    "env_credential",
    "FreelancerExecutor",
    "AlgoraExecutor",
    "MindriftExecutor",
    "OpireExecutor",
    "IssueHuntExecutor",
    "get_executors",
]
