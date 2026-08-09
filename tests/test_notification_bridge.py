from __future__ import annotations

from cores.events.event_bus import EventBus
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


def test_event_bus_dispatch_payload_with_priority_key():
    # Regression: publish dispatch must not collide `priority` kwarg with a
    # `priority` key already present in the payload (sync + async handlers).
    import asyncio

    bus = EventBus()
    sync_calls = []
    async_calls = []

    def _sync_handler(event_type, **data):
        sync_calls.append((event_type, data.get("priority"), data.get("_priority")))

    async def _async_handler(event_type, **data):
        async_calls.append((event_type, data.get("priority"), data.get("_priority")))

    bus.subscribe("finding:created", _sync_handler)
    bus.subscribe_async("finding:created", _async_handler)

    async def _publish():
        # priority key inside payload -> previously "got multiple values for keyword argument"
        bus.publish("finding:created", title="XSS", priority="high")
        await asyncio.sleep(0)

    asyncio.run(_publish())

    assert len(sync_calls) == 1, f"sync handler failed ({sync_calls})"
    event_type, payload_priority, bus_priority = sync_calls[0]
    assert event_type == "finding:created"
    assert payload_priority == "high"
    assert bus_priority == "medium"  # bus-classified, not overwritten by payload
    assert async_calls, "async handler got multiple values for keyword argument"

    bus.unsubscribe("finding:created", _sync_handler)
    bus.unsubscribe("finding:created", _async_handler)


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
