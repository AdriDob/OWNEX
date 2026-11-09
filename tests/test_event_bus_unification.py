"""Event bus unification tests — V15 / ADR-0003.

Verifies the single-bus architecture: ``core.events.CoreEventBus`` is now a
compatibility facade over the canonical ``cores.events.EventBus``. Events
published on either side must reach subscribers on both, exactly once.
"""

from __future__ import annotations

import pytest

from core.events.event_bus import CoreEventBus, get_core_event_bus
from cores.events.event_bus import get_event_bus


@pytest.fixture(autouse=True)
def _clean_handlers():
    """Isolate tests from singleton state where possible."""
    yield


class TestCrossTreeDelivery:
    def test_facade_publish_reaches_cores_subscriber(self):
        received = []
        get_event_bus().subscribe("unif:test_a", lambda **kw: received.append(kw))
        get_core_event_bus().publish("unif:test_a", value=1)
        assert len(received) == 1
        assert received[0]["event_type"] == "unif:test_a"
        assert received[0]["value"] == 1

    def test_cores_publish_reaches_facade_subscriber(self):
        received = []
        bus = CoreEventBus()
        bus.subscribe("unif:test_b", lambda **kw: received.append(kw))
        get_event_bus().publish("unif:test_b", value=2)
        assert len(received) == 1
        assert received[0]["event"] == "unif:test_b"
        assert received[0]["value"] == 2
        bus.clear()

    def test_facade_publish_reaches_facade_subscriber(self):
        received = []
        bus = CoreEventBus()
        bus.subscribe("unif:test_c", lambda **kw: received.append(kw))
        bus.publish("unif:test_c", value=3)
        assert len(received) == 1
        assert received[0]["event"] == "unif:test_c"
        bus.clear()


class TestWildcardsAndNamespaces:
    def test_wildcard_pattern(self):
        received = []
        bus = CoreEventBus()
        bus.subscribe("cycle:*", lambda **kw: received.append(kw["event"]))
        bus.publish("cycle:created", cid=1)
        bus.publish("cycle:updated", cid=1)
        bus.publish("other:event")
        assert received == ["cycle:created", "cycle:updated"]
        bus.clear()

    def test_subscribe_app(self):
        received = []
        bus = CoreEventBus()
        bus.subscribe_app("myapp", lambda **kw: received.append(kw["event"]))
        bus.publish("myapp:ping")
        bus.publish("otherapp:ping")
        assert received == ["myapp:ping"]
        bus.clear()

    def test_app_event_helper(self):
        bus = CoreEventBus()
        assert bus.app_event("atlas", "price:updated") == "atlas:price:updated"

    def test_cores_bus_wildcard(self):
        received = []
        unsub = get_event_bus().subscribe("unifns:*", lambda **kw: received.append(kw["event_type"]))
        get_event_bus().publish("unifns:one")
        get_event_bus().publish("other:two")
        unsub()
        get_event_bus().publish("unifns:three")
        assert received == ["unifns:one"]


class TestNoDuplicateNoLoss:
    def test_single_delivery_per_publish(self):
        count = []
        bus = CoreEventBus()
        bus.subscribe("unif:dup", lambda **kw: count.append(1))
        bus.publish("unif:dup")
        assert count == [1]
        bus.clear()

    def test_unsubscribe_callable(self):
        count = []
        bus = CoreEventBus()
        unsub = bus.subscribe("unif:unsub", lambda **kw: count.append(1))
        bus.publish("unif:unsub")
        unsub()
        bus.publish("unif:unsub")
        assert count == [1]
        bus.clear()

    def test_core_event_bus_alias_is_same_object(self):
        from cores.events.event_bus import get_core_event_bus as cores_alias

        assert cores_alias() is get_event_bus()


class TestHistoryAndPersistence:
    def test_facade_history_shape_and_app_filter(self):
        bus = get_core_event_bus()
        bus.publish("vhist:app_one", n=1)
        bus.publish("other:app_two", n=2)
        hist = bus.get_history(app_id="vhist", limit=50)
        assert hist, "expected at least one vhist event"
        assert all(r["app_id"] == "vhist" for r in hist)
        assert all("event" in r and "data" in r and "timestamp" in r for r in hist)

    def test_event_lands_in_canonical_history(self):
        get_event_bus().publish("vhist:canonical_check", marker=True)
        hist = get_event_bus().get_history(event_type="vhist:canonical_check", limit=10)
        assert any(e["type"] == "vhist:canonical_check" for e in hist)

    def test_priority_classification_still_applies(self):
        hist = get_event_bus().get_history(event_type="system:error", limit=5)
        # classification is internal; at minimum publish must not raise
        get_event_bus().publish("system:error", message="unif-test")
        hist = get_event_bus().get_history(event_type="system:error", limit=5)
        assert any(e.get("priority") == "critical" for e in hist)


class TestLegacyImports:
    def test_all_import_paths_resolve(self):
        from core.events import CoreEventBus
        from core.events import get_core_event_bus as g1
        from core.events.event_bus import get_event_bus as g2
        from cores.events.event_bus import get_core_event_bus as g3
        from cores.events.event_bus import get_event_bus as g4

        # g1 is the compatibility facade (CoreEventBus); g2/g3/g4 are the
        # canonical cores EventBus singleton — one underlying bus.
        assert g3() is g4()
        assert g2() is g4()
        assert isinstance(g1(), CoreEventBus)
        assert isinstance(CoreEventBus(), CoreEventBus)
        assert g3.__name__ == "get_event_bus"


class TestAsyncHandlers:
    @pytest.mark.asyncio
    async def test_async_handler_receives_event(self):
        received = []

        async def handler(**kw):
            received.append(kw["event_type"])

        get_event_bus().subscribe_async("unif:async_evt", handler)
        get_event_bus().publish("unif:async_evt")
        import asyncio

        await asyncio.sleep(0.2)
        assert "unif:async_evt" in received
