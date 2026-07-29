"""Offensive Intelligence event publisher — thin wrapper over EventBus."""

from __future__ import annotations

import logging
from typing import Any

from core.events.event_bus import get_core_event_bus
from core.events.types import EventEnvelope

logger = logging.getLogger("orion.core.offensive.publisher")

EVENT_PREFIX = "reasoner"


def publish_offensive_event(event_type: str, data: dict[str, Any], correlation_id: str = "") -> None:
    """Publish an offensive intelligence event to the EventBus."""
    envelope = EventEnvelope.create(
        event_type=f"{EVENT_PREFIX}:{event_type}",
        source="offensive",
        payload=data,
    )
    if correlation_id:
        envelope.correlation_id = correlation_id
    try:
        bus = get_core_event_bus()
        bus.publish(envelope.event_type, **envelope.payload)
        logger.debug("[Offensive] Published %s", envelope.event_type)
    except Exception as exc:
        logger.warning("Failed to publish offensive event %s: %s", event_type, exc)
