from __future__ import annotations

"""Core EventBus — namespace-aware event bus with SQLite persistence.
Bridges events to CATEYE's legacy EventBus so app events reach
legacy subscribers.
"""
# ruff: noqa: E402
from core.events.event_bus import CoreEventBus, get_core_event_bus
from cores.events.store import EventStore, get_event_store, reset_event_store
from cores.events.types import CorrelationId, Decision, EventEnvelope, Events

__all__ = [
    "CoreEventBus",
    "get_core_event_bus",
    "EventStore",
    "get_event_store",
    "reset_event_store",
    "Events",
    "EventEnvelope",
    "CorrelationId",
    "Decision",
    "get_correlation_id",
    "set_correlation_id",
    "get_or_create_correlation_id",
    "new_correlation_id",
    "with_correlation_id",
    "with_new_correlation_id",
]
