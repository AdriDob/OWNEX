"""Cycle Engine — CoreEventBus integration for cycle lifecycle events."""

from __future__ import annotations

from typing import Any

from core.events.event_bus import get_core_event_bus

# Event names
CYCLE_CREATED = "cycle.created"
CYCLE_UPDATED = "cycle.updated"
CYCLE_DELETED = "cycle.deleted"
CYCLE_ACTIVATED = "cycle.activated"
CYCLE_PAUSED = "cycle.paused"
CYCLE_STATUS_CHANGED = "cycle.status_changed"
CYCLE_METRICS_UPDATED = "cycle.metrics_updated"
CYCLE_ERROR = "cycle.error"


def publish_cycle_event(
    event: str,
    cycle_id: int,
    cycle_slug: str,
    cycle_name: str,
    old_status: str | None = None,
    new_status: str | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Publish a cycle lifecycle event to the CoreEventBus."""
    bus = get_core_event_bus()
    bus.publish(
        event,
        cycle_id=cycle_id,
        cycle_slug=cycle_slug,
        cycle_name=cycle_name,
        old_status=old_status,
        new_status=new_status,
        data=data or {},
    )


def publish_cycle_created(cycle_id: int, slug: str, name: str, data: dict | None = None) -> None:
    get_core_event_bus().publish("cycle.created", cycle_id=cycle_id, cycle_slug=slug, cycle_name=name, data=data or {})


def publish_cycle_updated(cycle_id: int, slug: str, name: str, data: dict | None = None) -> None:
    get_core_event_bus().publish("cycle.updated", cycle_id=cycle_id, cycle_slug=slug, cycle_name=name, data=data or {})


def publish_cycle_deleted(cycle_id: int, slug: str, name: str) -> None:
    get_core_event_bus().publish("cycle.deleted", cycle_id=cycle_id, cycle_slug=slug, cycle_name=name)


def publish_cycle_activated(cycle_id: int, slug: str, name: str, old_status: str) -> None:
    get_core_event_bus().publish(
        "cycle.activated",
        cycle_id=cycle_id,
        cycle_slug=slug,
        cycle_name=name,
        old_status=old_status,
        new_status="running",
    )


def publish_cycle_paused(cycle_id: int, slug: str, name: str, old_status: str) -> None:
    get_core_event_bus().publish(
        "cycle.paused", cycle_id=cycle_id, cycle_slug=slug, cycle_name=name, old_status=old_status, new_status="paused"
    )


def publish_cycle_status_changed(cycle_id: int, slug: str, name: str, old_status: str, new_status: str) -> None:
    get_core_event_bus().publish(
        "cycle.status_changed",
        cycle_id=cycle_id,
        cycle_slug=slug,
        cycle_name=name,
        old_status=old_status,
        new_status=new_status,
    )


def publish_cycle_metrics_updated(cycle_id: int, slug: str, name: str, metrics: dict) -> None:
    get_core_event_bus().publish(
        "cycle.metrics_updated", cycle_id=cycle_id, cycle_slug=slug, cycle_name=name, data=metrics
    )


def publish_cycle_error(cycle_id: int, slug: str, name: str, error: str) -> None:
    get_core_event_bus().publish(
        "cycle.error", cycle_id=cycle_id, cycle_slug=slug, cycle_name=name, data={"error": error}
    )
