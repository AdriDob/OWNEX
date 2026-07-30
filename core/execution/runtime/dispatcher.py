from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from core.execution.runtime.context import RuntimeContext
from core.execution.runtime.publisher import ExecutionEventPublisher

logger = logging.getLogger("ownex.execution.dispatcher")


class CapabilityDispatcher:
    """Secure capability execution pipeline.

    Never calls registry.execute() directly.
    Always flows through:
      Permission → Secrets → RateLimit → Metrics → Execute → Events → Return
    """

    def __init__(
        self,
        execute_fn: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        permission_check_fn: Callable[[str, str], bool] | None = None,
        secrets_fn: Callable[[str], dict[str, Any]] | None = None,
        rate_limit_fn: Callable[[str], bool] | None = None,
        publisher: ExecutionEventPublisher | None = None,
    ) -> None:
        self._execute = execute_fn
        self._permission_check = permission_check_fn
        self._secrets = secrets_fn
        self._rate_limit = rate_limit_fn
        self.publisher = publisher or ExecutionEventPublisher()

    def bind(
        self,
        *,
        execute_fn: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        permission_check_fn: Callable[[str, str], bool] | None = None,
        secrets_fn: Callable[[str], dict[str, Any]] | None = None,
        rate_limit_fn: Callable[[str], bool] | None = None,
    ) -> None:
        if execute_fn:
            self._execute = execute_fn
        if permission_check_fn:
            self._permission_check = permission_check_fn
        if secrets_fn:
            self._secrets = secrets_fn
        if rate_limit_fn:
            self._rate_limit = rate_limit_fn

    def dispatch(
        self,
        capability: str,
        params: dict[str, Any],
        context: RuntimeContext | None = None,
    ) -> dict[str, Any]:
        """Execute a capability through the full pipeline."""

        execution_id = context.execution_id if context else "unknown"

        # 1. Permission check
        if self._permission_check:
            allowed = self._permission_check(execution_id, capability)
            if not allowed:
                msg = f"Permission denied for capability '{capability}'"
                logger.warning("[Dispatcher] %s", msg)
                return {"error": msg, "success": False}

        # 2. Secrets injection
        resolved_params = dict(params)
        if self._secrets:
            try:
                secrets = self._secrets(capability)
                resolved_params["_secrets"] = secrets
            except Exception as exc:
                logger.warning("[Dispatcher] Secrets resolution failed for %s: %s", capability, exc)

        # 3. Rate limit check
        if self._rate_limit:
            allowed = self._rate_limit(capability)
            if not allowed:
                msg = f"Rate limit exceeded for capability '{capability}'"
                logger.warning("[Dispatcher] %s", msg)
                return {"error": msg, "success": False}

        # 4. Execute
        if not self._execute:
            msg = f"No execute function registered for capability '{capability}'"
            logger.error("[Dispatcher] %s", msg)
            return {"error": msg, "success": False}

        execution_id = context.execution_id if context else "unknown"
        try:
            if context:
                context.metrics.api_calls += 1

            result = self._execute(capability, resolved_params)

            success = result.get("success", True) and "error" not in result
            if context and success:
                tokens = result.get("tokens_used", 0)
                cost = result.get("cost_usd", 0.0)
                context.metrics.tokens_used += tokens
                context.metrics.cost_usd += cost

            return result

        except Exception as exc:
            logger.exception("[Dispatcher] Capability '%s' failed: %s", capability, exc)
            if context:
                context.metrics.failures += 1
            return {"error": str(exc), "success": False}
