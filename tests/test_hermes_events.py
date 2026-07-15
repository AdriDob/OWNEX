"""Tests for Hermes EventBus integration."""

from __future__ import annotations

from apps.hermes.publisher import HermesEventPublisher
from core.events.types import Events


class FakeEventBus:
    """Minimal fake EventBus for testing."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def publish(self, event: str, **data: object) -> None:
        self.events.append({"event": event, "data": data})


def test_publisher_silent_noop_without_bus() -> None:
    pub = HermesEventPublisher(event_bus=None)
    pub.action_requested("test", "low", False, "testing")
    pub.action_started("test")
    pub.action_completed("test", "ok", "done")
    pub.action_failed("test", "error")
    pub.permission_required("test", "high", "impact")
    pub.security_blocked("test", "blocked")


def test_action_requested_event() -> None:
    bus = FakeEventBus()
    pub = HermesEventPublisher(bus)
    pub.action_requested("backup", "low", False, "scheduled backup")
    assert len(bus.events) == 1
    assert bus.events[0]["event"] == Events.HERMES_ACTION_REQUESTED
    assert bus.events[0]["data"]["command"] == "backup"
    assert bus.events[0]["data"]["risk"] == "low"


def test_action_approved_event() -> None:
    bus = FakeEventBus()
    pub = HermesEventPublisher(bus)
    pub.action_approved("backup", "low")
    assert bus.events[0]["event"] == Events.HERMES_ACTION_APPROVED


def test_action_started_event() -> None:
    bus = FakeEventBus()
    pub = HermesEventPublisher(bus)
    pub.action_started("backup", target="system")
    assert bus.events[0]["event"] == Events.HERMES_ACTION_STARTED
    assert bus.events[0]["data"]["context"]["target"] == "system"


def test_action_completed_event() -> None:
    bus = FakeEventBus()
    pub = HermesEventPublisher(bus)
    pub.action_completed("backup", "ok", "Backup done", {"size_mb": 42})
    ev = bus.events[0]
    assert ev["event"] == Events.HERMES_ACTION_COMPLETED
    assert ev["data"]["status"] == "ok"
    assert ev["data"]["details"]["size_mb"] == 42


def test_action_failed_event() -> None:
    bus = FakeEventBus()
    pub = HermesEventPublisher(bus)
    pub.action_failed("backup", "Timeout", {"duration_s": 300})
    ev = bus.events[0]
    assert ev["event"] == Events.HERMES_ACTION_FAILED
    assert "Timeout" in str(ev["data"]["error"])


def test_permission_required_event() -> None:
    bus = FakeEventBus()
    pub = HermesEventPublisher(bus)
    pub.permission_required("kill", "high", "Terminates a process")
    ev = bus.events[0]
    assert ev["event"] == Events.HERMES_PERMISSION_REQUIRED
    assert ev["data"]["requires_confirmation"] is True


def test_security_blocked_event() -> None:
    bus = FakeEventBus()
    pub = HermesEventPublisher(bus)
    pub.security_blocked("kill", "PID 1 blocked", {"pid": 1})
    ev = bus.events[0]
    assert ev["event"] == Events.HERMES_SECURITY_BLOCKED
    assert ev["data"]["details"]["pid"] == 1


def test_all_hermes_events_defined() -> None:
    """Verify all Hermes event types exist in Events class."""
    assert hasattr(Events, "HERMES_ACTION_REQUESTED")
    assert hasattr(Events, "HERMES_ACTION_APPROVED")
    assert hasattr(Events, "HERMES_ACTION_STARTED")
    assert hasattr(Events, "HERMES_ACTION_COMPLETED")
    assert hasattr(Events, "HERMES_ACTION_FAILED")
    assert hasattr(Events, "HERMES_PERMISSION_REQUIRED")
    assert hasattr(Events, "HERMES_SECURITY_BLOCKED")


def test_hermes_events_in_all_set() -> None:
    """Verify all Hermes event types are registered in the ALL frozenset."""
    for attr in (
        "HERMES_ACTION_REQUESTED",
        "HERMES_ACTION_APPROVED",
        "HERMES_ACTION_STARTED",
        "HERMES_ACTION_COMPLETED",
        "HERMES_ACTION_FAILED",
        "HERMES_PERMISSION_REQUIRED",
        "HERMES_SECURITY_BLOCKED",
    ):
        assert getattr(Events, attr) in Events.ALL, f"{attr} not in Events.ALL"
