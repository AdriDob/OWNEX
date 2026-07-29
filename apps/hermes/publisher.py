"""MERLIN Event Publisher — publishes automation actions to EventBus."""

from __future__ import annotations

import logging
import time
from typing import Any

from cores.events.types import Events

logger = logging.getLogger("catseye.merlin.publisher")


class HermesEventPublisher:
    """MERLIN Event Publisher — publishes lifecycle events to the EventBus.

    Always safe to call — silently no-ops if EventBus is unavailable.
    """

    def __init__(self, event_bus: Any | None = None) -> None:
        self._bus = event_bus

    def _publish(self, event: str, **data: Any) -> None:
        if self._bus is None:
            return
        try:
            self._bus.publish(event, **data)
        except Exception:
            logger.exception("Failed to publish %s", event)

    def action_requested(self, command: str, risk: str, destructive: bool, reason: str) -> None:
        self._publish(
            Events.HERMES_ACTION_REQUESTED,
            command=command,
            risk=risk,
            destructive=destructive,
            reason=reason,
            timestamp=time.time(),
        )

    def action_approved(self, command: str, risk: str) -> None:
        self._publish(
            Events.HERMES_ACTION_APPROVED,
            command=command,
            risk=risk,
            approved_at=time.time(),
        )

    def action_started(self, command: str, **context: Any) -> None:
        self._publish(
            Events.HERMES_ACTION_STARTED,
            command=command,
            context=context,
            started_at=time.time(),
        )

    def action_completed(self, command: str, status: str, message: str, details: dict[str, Any] | None = None) -> None:
        self._publish(
            Events.HERMES_ACTION_COMPLETED,
            command=command,
            status=status,
            message=message,
            details=details or {},
            completed_at=time.time(),
        )

    def action_failed(self, command: str, error: str, details: dict[str, Any] | None = None) -> None:
        self._publish(
            Events.HERMES_ACTION_FAILED,
            command=command,
            error=error,
            details=details or {},
            failed_at=time.time(),
        )

    def permission_required(self, command: str, risk: str, impact: str, requires_confirmation: bool = True) -> None:
        self._publish(
            Events.HERMES_PERMISSION_REQUIRED,
            command=command,
            risk=risk,
            impact=impact,
            requires_confirmation=requires_confirmation,
        )

    def security_blocked(self, command: str, reason: str, details: dict[str, Any] | None = None) -> None:
        self._publish(
            Events.HERMES_SECURITY_BLOCKED,
            command=command,
            reason=reason,
            details=details or {},
            blocked_at=time.time(),
        )
