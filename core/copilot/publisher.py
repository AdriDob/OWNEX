"""COPILOT event publishing — thin bridge between COPILOT and EventBus.

COPILOT never calls ``bus.publish()`` directly. It calls this module,
which handles envelope creation, persistence, and transport.
"""

from __future__ import annotations

import logging
from typing import Any

from core.events.correlation import get_or_create_correlation_id
from core.events.store import get_event_store
from core.events.types import EventEnvelope

logger = logging.getLogger("orion.core.copilot.publisher")
SOURCE = "copilot"

_bus: Any = None


def _get_bus() -> Any:
    global _bus
    if _bus is None:
        from core.events.event_bus import get_core_event_bus

        _bus = get_core_event_bus()
    return _bus


def publish_copilot_event(
    event_type: str,
    payload: dict[str, Any],
    *,
    duration_ms: float | None = None,
    correlation_id: str | None = None,
    user: str | None = None,
) -> None:
    """Create envelope, persist to EventStore, publish to CoreEventBus."""
    cid = correlation_id or get_or_create_correlation_id()
    envelope = EventEnvelope.create(
        event_type=event_type,
        source=SOURCE,
        correlation_id=cid,
        payload=payload,
        duration_ms=duration_ms,
        user=user,
    )

    try:
        get_event_store().store(envelope)
    except Exception:
        logger.exception("Failed to persist event: %s", event_type)

    try:
        _get_bus().publish(event_type, **envelope.to_dict())
    except Exception:
        logger.debug("Failed to publish event: %s", event_type)
