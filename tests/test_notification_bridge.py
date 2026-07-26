from __future__ import annotations

from cores.notifications.event_bridge import (
    EVENT_PRIORITY_MAP,
    EVENT_TITLE_MAP,
    NotificationEventBridge,
)


def test_event_map_keys_match():
    assert set(EVENT_PRIORITY_MAP.keys()) == set(EVENT_TITLE_MAP.keys())


def test_event_priorities_are_valid():
    valid = {"low", "medium", "high", "critical"}
    for event, prio in EVENT_PRIORITY_MAP.items():
        assert prio in valid, f"{event} has invalid priority {prio}"


def test_event_bridge_subscribe_unsubscribe():
    bus = _FakeEventBus()
    bridge = NotificationEventBridge(bus)
    assert bridge.start() == len(EVENT_PRIORITY_MAP)
    assert len(bridge.subscribed_events) == len(EVENT_PRIORITY_MAP)
    assert len(bus._subscriptions) == len(EVENT_PRIORITY_MAP)
    bridge.stop()
    remaining = sum(len(h) for h in bus._subscriptions.values())
    assert remaining == 0, "all handlers should be unsubscribed"


def test_event_bridge_handler_called():
    bus = _FakeEventBus()
    bridge = NotificationEventBridge(bus)
    bridge.start()

    called = [False]

    # replace internal handler so publish actually runs our trap
    def _trap(event, **data):
        called[0] = True

    for ev in list(bus._subscriptions):
        bus._subscriptions[ev] = [_trap]

    bus.publish("finding:created", severity="critical", endpoint="/api/test")
    assert called[0]

    bridge.stop()


class _FakeEventBus:
    def __init__(self):
        self._subscriptions: dict[str, list] = {}

    def subscribe(self, event: str, handler) -> callable:
        self._subscriptions.setdefault(event, []).append(handler)

        def unsubscribe():
            handlers = self._subscriptions.get(event, [])
            if handler in handlers:
                handlers.remove(handler)

        return unsubscribe

    def publish(self, event: str, **data):
        for handler in self._subscriptions.get(event, []):
            handler(event=event, **data)
