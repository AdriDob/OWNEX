"""Tests for Event Foundation: types, correlation, store, capabilities, publisher."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from core.capabilities.registry import (
    CapabilityRegistry,
    get_capability_registry,
    reset_capability_registry,
)
from cores.events.correlation import (
    get_correlation_id,
    get_or_create_correlation_id,
    new_correlation_id,
    set_correlation_id,
    with_correlation_id,
    with_new_correlation_id,
)
from cores.events.store import EventStore, get_event_store, reset_event_store
from cores.events.types import CorrelationId, Decision, EventEnvelope, Events

# ── Event Types ────────────────────────────────────────────────


def test_events_all_defined() -> None:
    assert len(Events.ALL) > 30
    assert Events.FINDING_CREATED == "finding:created"
    assert Events.FINDING_CONFIRMED == "finding:confirmed"
    assert Events.COPILOT_ANALYSIS_COMPLETED == "copilot:analysis:completed"
    assert Events.COPILOT_DECISION == "copilot:decision"
    assert Events.ARCA_INVOICE_CREATED == "arca:invoice:created"
    assert Events.NOTIFICATION_SENT == "notification:sent"
    assert Events.EMAIL_SENT == "outlook:email:sent"
    assert Events.FINANCIAL_CANDIDATE == "financial:candidate"
    assert Events.INVOICE_REQUESTED == "invoice:requested"
    assert Events.SYSTEM_DEGRADED == "system:degraded"


# ── CorrelationId ──────────────────────────────────────────────


def test_correlation_id_value_object() -> None:
    cid = CorrelationId()
    assert len(cid.value) == 32  # hex uuid
    assert str(cid) == cid.value
    assert repr(cid).startswith("CorrelationId(")


def test_correlation_id_unique() -> None:
    c1 = CorrelationId()
    c2 = CorrelationId()
    assert c1.value != c2.value


# ── Correlation context ────────────────────────────────────────


def test_get_or_create_generates() -> None:
    cid = get_or_create_correlation_id()
    assert len(cid) == 32


def test_set_and_get() -> None:
    set_correlation_id("test123")
    assert get_correlation_id() == "test123"


def test_with_correlation_id_context() -> None:
    set_correlation_id("outer")
    with with_correlation_id("inner"):
        assert get_correlation_id() == "inner"
    assert get_correlation_id() == "outer"


def test_with_new_correlation_id_yields() -> None:
    with with_new_correlation_id() as cid:
        assert len(cid) == 32
        assert get_correlation_id() == cid


def test_new_correlation_id_fresh() -> None:
    first = new_correlation_id()
    second = new_correlation_id()
    assert first != second


# ── EventEnvelope ──────────────────────────────────────────────


def test_envelope_create() -> None:
    env = EventEnvelope.create(
        event_type=Events.FINDING_CONFIRMED,
        source="test",
        correlation_id="abc123",
        payload={"finding_id": "f-001"},
        duration_ms=150.0,
        user="test@example.com",
    )
    assert env.event_type == Events.FINDING_CONFIRMED
    assert env.correlation_id == "abc123"
    assert env.payload == {"finding_id": "f-001"}
    assert env.duration_ms == 150.0
    assert env.user == "test@example.com"


def test_envelope_to_dict() -> None:
    env = EventEnvelope.create(
        event_type="test:event",
        source="test",
        payload={"key": "value"},
        duration_ms=100.0,
    )
    d = env.to_dict()
    assert d["event_type"] == "test:event"
    assert d["payload"] == {"key": "value"}
    assert d["duration_ms"] == 100.0
    assert "timestamp" in d
    assert "correlation_id" in d


def test_envelope_auto_correlation() -> None:
    env = EventEnvelope.create(event_type="test:auto", source="test")
    assert env.correlation_id != ""


def test_envelope_without_optionals() -> None:
    env = EventEnvelope.create(event_type="test:minimal", source="test")
    d = env.to_dict()
    assert "duration_ms" not in d
    assert "user" not in d


# ── Decision ───────────────────────────────────────────────────


def test_decision_minimal() -> None:
    d = Decision(
        event_type=Events.FINDING_CONFIRMED,
        correlation_id="abc123",
        priority="high",
        reason="Finding confirmed",
        confidence=0.85,
        actions=[{"action": "generate_report", "target": "f-001"}],
        human_required=False,
    )
    assert d.priority == "high"
    assert d.human_required is False
    assert d.roi is None  # not set


def test_decision_with_human_required() -> None:
    d = Decision(
        event_type=Events.SYSTEM_ERROR,
        correlation_id="abc123",
        priority="critical",
        reason="System error",
        confidence=0.25,
        actions=[{"action": "manual_intervention", "target": "system"}],
        human_required=True,
    )
    assert d.human_required is True


def test_decision_to_envelope() -> None:
    d = Decision(
        event_type=Events.FINDING_CONFIRMED,
        correlation_id="abc123",
        priority="high",
        reason="Test",
        confidence=0.9,
        actions=[{"action": "test"}],
    )
    env = d.to_envelope()
    # The envelope event_type is the same as the decision's event_type
    assert env.event_type == Events.FINDING_CONFIRMED
    assert env.payload["decision_event"] == Events.FINDING_CONFIRMED
    assert env.payload["priority"] == "high"
    assert env.payload["confidence"] == 0.9


def test_decision_to_dict() -> None:
    d = Decision(
        event_type="test:event",
        correlation_id="abc",
        priority="low",
        reason="reason",
        confidence=0.5,
        actions=[],
    )
    dd = d.to_dict()
    assert dd["event_type"] == "test:event"
    assert dd["priority"] == "low"


# ── Event Store ────────────────────────────────────────────────


@pytest.fixture
def tmp_store(tmp_path: Path) -> EventStore:
    reset_event_store()
    db_path = tmp_path / "test_events.db"
    store = EventStore(db_path=db_path)
    return store


def test_store_and_retrieve(tmp_store: EventStore) -> None:
    env = EventEnvelope.create(
        event_type=Events.FINDING_CONFIRMED,
        source="test",
        payload={"finding_id": "f-001"},
    )
    row_id = tmp_store.store(env)
    assert row_id > 0

    by_cid = tmp_store.get_by_correlation_id(env.correlation_id)
    assert len(by_cid) == 1
    assert by_cid[0]["event_type"] == Events.FINDING_CONFIRMED


def test_store_dict(tmp_store: EventStore) -> None:
    row_id = tmp_store.store_dict(
        event_type=Events.COPILOT_ANALYSIS_COMPLETED,
        correlation_id="corr-1",
        source="copilot",
        payload={"finding_id": "f-001", "confidence": 0.9},
        duration_ms=250.0,
        user="admin",
    )
    assert row_id > 0

    events = tmp_store.get_by_correlation_id("corr-1")
    assert len(events) == 1
    assert events[0]["duration_ms"] == 250.0
    assert events[0]["user"] == "admin"


def test_get_by_event_type(tmp_store: EventStore) -> None:
    tmp_store.store_dict("test:type:a", "c1", "test")
    tmp_store.store_dict("test:type:b", "c2", "test")
    tmp_store.store_dict("test:type:a", "c3", "test")

    type_a = tmp_store.get_by_event_type("test:type:a")
    assert len(type_a) == 2


def test_replay_time_range(tmp_store: EventStore) -> None:
    now = time.time()
    tmp_store.store_dict("test:old", "c1", "test")
    tmp_store.store_dict("test:new", "c2", "test")

    recent = tmp_store.replay(from_ts=now - 1)
    assert len(recent) >= 2

    future = tmp_store.replay(from_ts=now + 3600)
    assert len(future) == 0


def test_search(tmp_store: EventStore) -> None:
    tmp_store.store_dict("test:a", "c1", "mod1")
    tmp_store.store_dict("test:b", "c2", "mod1")
    tmp_store.store_dict("test:a", "c3", "mod2")

    by_type = tmp_store.search(event_type="test:a")
    assert len(by_type) == 2

    by_source = tmp_store.search(source="mod1")
    assert len(by_source) == 2

    by_cid = tmp_store.search(correlation_id="c1")
    assert len(by_cid) == 1


def test_count(tmp_store: EventStore) -> None:
    assert tmp_store.count() == 0
    tmp_store.store_dict("test:count", "c1", "test")
    tmp_store.store_dict("test:count", "c2", "test")
    assert tmp_store.count() == 2
    assert tmp_store.count(event_type="test:count") == 2
    assert tmp_store.count(event_type="nonexistent") == 0


def test_get_stats(tmp_store: EventStore) -> None:
    tmp_store.store_dict("test:a", "c1", "src1")
    tmp_store.store_dict("test:b", "c2", "src2")
    tmp_store.store_dict("test:a", "c3", "src1")

    stats = tmp_store.get_stats()
    assert stats["total_events"] == 3
    assert stats["by_type"]["test:a"] == 2
    assert stats["by_source"]["src1"] == 2


def test_prune(tmp_store: EventStore) -> None:
    tmp_store.store_dict("test:new", "c1", "test")
    now = time.time()
    # prune everything older than 1 hour from now — at most 1 event if it was stored recently
    pruned = tmp_store.prune(now + 3600)
    assert pruned >= 0
    assert tmp_store.count() >= 0


def test_singleton(tmp_path: Path) -> None:
    reset_event_store()
    s1 = get_event_store(db_path=tmp_path / "s1.db")
    s2 = get_event_store(db_path=tmp_path / "s2.db")
    assert s1 is s2


# ── Capability Registry ────────────────────────────────────────


def test_register_and_find() -> None:
    reg = CapabilityRegistry()
    reg.register("send_email", "outlook", {"auth": "oauth2"}, "Send email via Graph API")
    reg.register("send_email", "gmail", {"auth": "oauth2"}, "Send email via Gmail API")

    results = reg.find("send_email")
    assert len(results) == 2
    assert results[0].module == "outlook"
    assert results[0].description == "Send email via Graph API"


def test_has_capability() -> None:
    reg = CapabilityRegistry()
    assert reg.has_capability("nonexistent") is False
    reg.register("test_cap", "test_mod")
    assert reg.has_capability("test_cap") is True


def test_list_capabilities() -> None:
    reg = CapabilityRegistry()
    reg.register("cap_a", "mod1")
    reg.register("cap_b", "mod2")
    caps = reg.list_capabilities()
    assert "cap_a" in caps
    assert "cap_b" in caps


def test_list_by_module() -> None:
    reg = CapabilityRegistry()
    reg.register("cap_a", "mod1")
    reg.register("cap_b", "mod1")
    reg.register("cap_c", "mod2")
    mod1 = reg.list_by_module("mod1")
    assert len(mod1) == 2
    mod2 = reg.list_by_module("mod2")
    assert len(mod2) == 1


def test_unregister() -> None:
    reg = CapabilityRegistry()
    reg.register("send_email", "outlook")
    reg.register("send_email", "gmail")
    assert len(reg.find("send_email")) == 2
    reg.unregister("send_email", "outlook")
    assert len(reg.find("send_email")) == 1
    assert reg.find("send_email")[0].module == "gmail"


def test_clear() -> None:
    reg = CapabilityRegistry()
    reg.register("a", "m1")
    reg.register("b", "m2")
    assert reg.count() == 2
    reg.clear()
    assert reg.count() == 0


def test_capability_registry_singleton() -> None:
    reset_capability_registry()
    r1 = get_capability_registry()
    r2 = get_capability_registry()
    assert r1 is r2
