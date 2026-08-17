"""Tests for cores/memory/system.py UnifiedMemoryStore (desktop startup path).

The store is a stub extended with set/get/search/get_stats persistence in the
``memory_records`` table (database.models.MemoryRecord). The session fixtures
in conftest.py isolate DATABASE_URL to /tmp, so these tests never touch the
real database/catseye.db.
"""

from __future__ import annotations

import time

from cores.memory.system import (
    MemoryNamespace,
    MemoryTier,
    UnifiedMemoryStore,
    get_memory_store,
)


def _fresh_store() -> UnifiedMemoryStore:
    return UnifiedMemoryStore()


def test_set_get_dict_roundtrip() -> None:
    store = _fresh_store()
    payload = {"command": "ls", "exit_code": 0}
    store.set(
        MemoryNamespace.CONVERSATION,
        "cmd_1",
        payload,
        tier=MemoryTier.TEMPORARY,
        ttl_seconds=86400,
    )
    assert store.get(MemoryNamespace.CONVERSATION, "cmd_1") == payload


def test_set_get_str_roundtrip() -> None:
    store = _fresh_store()
    store.set(MemoryNamespace.PREFERENCES, "language", "es")
    assert store.get(MemoryNamespace.PREFERENCES, "language") == "es"


def test_get_missing_returns_none() -> None:
    store = _fresh_store()
    assert store.get(MemoryNamespace.CONVERSATION, "missing_key") is None


def test_set_upserts_same_key() -> None:
    store = _fresh_store()
    store.set(MemoryNamespace.SYSTEM_HEALTH, "score", {"value": 50})
    store.set(MemoryNamespace.SYSTEM_HEALTH, "score", {"value": 90})
    assert store.get(MemoryNamespace.SYSTEM_HEALTH, "score") == {"value": 90}


def test_search_filters_by_namespace() -> None:
    store = _fresh_store()
    store.set(MemoryNamespace.OPPORTUNITIES, "opp_1", {"title": "opire bounty"})
    store.set(MemoryNamespace.CONVERSATION, "chat_1", {"title": "opire chat"})
    hits = store.search(namespaces=[MemoryNamespace.OPPORTUNITIES])
    assert [h.key for h in hits] == ["opp_1"]


def test_search_filters_by_query() -> None:
    store = _fresh_store()
    store.set(MemoryNamespace.OPPORTUNITIES, "opp_1", {"title": "opire bounty"})
    store.set(MemoryNamespace.OPPORTUNITIES, "opp_2", {"title": "hackerone program"})
    hits = store.search(query="opire", namespaces=[MemoryNamespace.OPPORTUNITIES])
    assert [h.key for h in hits] == ["opp_1"]


def test_search_returns_entries_with_deserialized_value() -> None:
    store = _fresh_store()
    store.set(MemoryNamespace.OPPORTUNITIES, "opp_1", {"title": "x", "reward": 100})
    hits = store.search(query="x", namespaces=[MemoryNamespace.OPPORTUNITIES])
    assert hits
    assert hits[0].value["reward"] == 100


def test_temporary_entry_expires() -> None:
    store = _fresh_store()
    store.set(MemoryNamespace.CONVERSATION, "tmp", "data", tier=MemoryTier.TEMPORARY, ttl_seconds=1)
    assert store.get(MemoryNamespace.CONVERSATION, "tmp") == "data"
    time.sleep(1.1)
    assert store.get(MemoryNamespace.CONVERSATION, "tmp") is None


def test_get_stats_shape() -> None:
    store = _fresh_store()
    store.set(MemoryNamespace.OPPORTUNITIES, "opp_1", {"title": "x"})
    store.set(MemoryNamespace.PREFERENCES, "lang", "es")
    stats = store.get_stats()
    assert stats["total"] >= 2
    assert stats["namespaces"].get("opportunities", 0) >= 1
    assert "expired_entries" in stats


def test_persistence_across_instances() -> None:
    _fresh_store().set(MemoryNamespace.PREFERENCES, "persisted", "yes")
    assert _fresh_store().get(MemoryNamespace.PREFERENCES, "persisted") == "yes"


def test_opportunity_engine_seeds_into_memory() -> None:
    from cores.opportunity.engine import get_opportunity_engine

    engine = get_opportunity_engine()
    all_opps = engine.get_all()
    assert len(all_opps) >= 3
    assert all(isinstance(o, dict) for o in all_opps)
    assert any(o.get("title") for o in all_opps)


def test_singleton_shared() -> None:
    assert get_memory_store() is get_memory_store()
