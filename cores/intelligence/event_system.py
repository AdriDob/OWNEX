"""
intelligence.event_system — Typed wrapper over the canonical EventBus.

All events go through a single EventBus (SQLite-backed).
This module provides typed event names and a stable API for intelligence components.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from cores.events.event_bus import get_event_bus

LOG = logging.getLogger("ownex.intelligence.event_system")

EVENT_TYPES = {
    "NewEndpoint",
    "PipelineUpdated",
    "EvidenceAdded",
    "VerdictChanged",
    "ReportGenerated",
    "ScreenshotUpdated",
    "DifferentialUpdated",
    "AIInsightUpdated",
    "QuickWinsUpdated",
    "ExecutionPlanUpdated",
    "AttackSurfaceUpdated",
    "ROIUpdated",
    "HypothesisUpdated",
    "CacheHit",
    "CacheMiss",
    "ArtifactInvalidated",
}

EVENT_PREFIX = "intel:"

EventHandler = Callable[[str, Any], None]


class EventSystem:
    """Typed wrapper around EventBus. Validates event types, delegates storage to EventBus."""

    def __init__(self) -> None:
        self._bus = get_event_bus()

    def emit(self, event_type: str, payload: Any = None) -> None:
        if event_type not in EVENT_TYPES:
            LOG.warning("Unknown event type: %s", event_type)
        topic = f"{EVENT_PREFIX}{event_type}"
        self._bus.publish(topic, data=payload)
        LOG.debug("Event: %s", event_type)

    def subscribe(self, event_type: str, handler) -> None:
        if event_type not in EVENT_TYPES:
            LOG.warning("Subscribing to unknown event type: %s", event_type)
        topic = f"{EVENT_PREFIX}{event_type}"

        def _wrapper(actual_topic: str, data: Any) -> None:
            if actual_topic == topic:
                handler(event_type, data)

        self._bus.subscribe(topic, _wrapper)

    def unsubscribe(self, event_type: str, handler) -> None:
        pass

    def get_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        topic = f"{EVENT_PREFIX}{event_type}" if event_type else EVENT_PREFIX
        raw = self._bus.get_history(topic if event_type else None, limit=500)
        return [
            {
                "event_id": i,
                "event_type": e.get("topic", "").replace(EVENT_PREFIX, ""),
                "timestamp": e.get("timestamp", ""),
                "payload": e.get("data", {}),
            }
            for i, e in enumerate(raw)
        ]

    def clear(self) -> None:
        self._bus.clear_history()

    def stats(self) -> dict[str, Any]:
        all_events = self._bus.get_history(None, limit=10000)
        types: dict[str, int] = {}
        for e in all_events:
            t = e.get("topic", "")
            if t.startswith(EVENT_PREFIX):
                tname = t[len(EVENT_PREFIX):]
                types[tname] = types.get(tname, 0) + 1
        return {
            "total_events": sum(types.values()),
            "event_types": types,
            "subscribers": {},
        }


_global_event_system: EventSystem | None = None
_global_event_system_lock = __import__("threading").Lock()


def get_event_system() -> EventSystem:
    global _global_event_system
    if _global_event_system is None:
        with _global_event_system_lock:
            if _global_event_system is None:
                _global_event_system = EventSystem()
    return _global_event_system
