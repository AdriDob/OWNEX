"""Emit — one-line EventBus publisher for user-facing notifications.

Every backend module that reaches a user-meaningful outcome calls
``emit(event_type, message=..., id=..., url=...)`` instead of hand-rolling
bus access. Never raises: notification must never break the flow that
produced it. Fan-out (hub → DB → WS → desktop/mobile) lives in the
bridges wired at boot (see api/lifespan ``_init_notification_bridges``).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.notifications.emit")


def emit(event_type: str, **payload: Any) -> bool:
    """Publish a notification event. Returns False only when the bus is down."""
    try:
        from cores.events.event_bus import get_event_bus

        get_event_bus().publish(event_type, **payload)
        return True
    except Exception as exc:
        logger.debug("emit(%s) skipped: %s", event_type, exc)
        return False
