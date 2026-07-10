"""Tests for Unified Memory — namespaces, CRUD, search, expiration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.memory.store import UnifiedMemoryStore, get_memory_store


@pytest.fixture(autouse=True)
def _cleanup():
    store = get_memory_store()
    for ns in store.list_namespaces():
        entries = store.query(namespace=ns, include_expired=True, limit=1000)
        for e in entries:
            store.delete(e["namespace"], e["key"])
    yield


@pytest.fixture
def mem() -> UnifiedMemoryStore:
    return get_memory_store()


class TestStore:
    def test_store_and_get(self, mem: UnifiedMemoryStore) -> None:
        mid = mem.store("test", "key1", "Test content")
        assert isinstance(mid, int)
        entry = mem.get("test", "key1")
        assert entry is not None
        assert entry["content"] == "Test content"
        assert entry["namespace"] == "test"

    def test_store_with_metadata(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "key2", "Content", metadata={"source": "manual", "score": 0.9})
        entry = mem.get("test", "key2")
        assert entry["metadata"]["source"] == "manual"
        assert entry["metadata"]["score"] == 0.9

    def test_store_with_tags(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "key3", "Content", tags=["idor", "critical"])
        entry = mem.get("test", "key3")
        assert "idor" in entry["tags"]
        assert "critical" in entry["tags"]

    def test_store_with_priority(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "high", "High priority", priority=0.9)
        mem.store("test", "low", "Low priority", priority=0.1)
        results = mem.query(namespace="test", limit=10)
        assert results[0]["key"] == "high"

    def test_update_existing(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "update", "Original")
        mem.store("test", "update", "Updated")
        entry = mem.get("test", "update")
        assert entry["content"] == "Updated"

    def test_get_nonexistent(self, mem: UnifiedMemoryStore) -> None:
        assert mem.get("test", "nonexistent") is None

    def test_delete(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "del", "To delete")
        assert mem.delete("test", "del") is True
        assert mem.delete("test", "del") is False
        assert mem.get("test", "del") is None


class TestQuery:
    def test_query_all(self, mem: UnifiedMemoryStore) -> None:
        mem.store("ns1", "a", "Alpha")
        mem.store("ns2", "b", "Beta")
        results = mem.query(limit=10)
        assert len(results) == 2

    def test_query_by_namespace(self, mem: UnifiedMemoryStore) -> None:
        mem.store("ns1", "a", "Alpha")
        mem.store("ns2", "b", "Beta")
        results = mem.query(namespace="ns1")
        assert len(results) == 1
        assert results[0]["namespace"] == "ns1"

    def test_query_by_search(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "k1", "IDOR vulnerability in /api/users")
        mem.store("test", "k2", "SSRF in /api/fetch")
        results = mem.query(namespace="test", search="IDOR")
        assert len(results) == 1

    def test_query_by_tag(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "k1", "Content", tags=["critical", "idor"])
        mem.store("test", "k2", "Content", tags=["low"])
        results = mem.query(namespace="test", tags=["critical"])
        assert len(results) == 1

    def test_query_min_priority(self, mem: UnifiedMemoryStore) -> None:
        mem.store("test", "low", "Low", priority=0.3)
        mem.store("test", "high", "High", priority=0.8)
        results = mem.query(namespace="test", min_priority=0.5)
        assert len(results) == 1
        assert results[0]["key"] == "high"

    def test_query_limit(self, mem: UnifiedMemoryStore) -> None:
        for i in range(10):
            mem.store("test", f"k{i}", f"Content {i}")
        results = mem.query(namespace="test", limit=3)
        assert len(results) == 3


class TestExpiration:
    def test_expired_excluded(self, mem: UnifiedMemoryStore) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        mem.store("test", "expired", "Expired content", expires_at=past)
        mem.store("test", "active", "Active content")
        results = mem.query(namespace="test")
        assert len(results) == 1
        assert results[0]["key"] == "active"

    def test_expired_included_with_flag(self, mem: UnifiedMemoryStore) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        mem.store("test", "expired", "Expired", expires_at=past)
        results = mem.query(namespace="test", include_expired=True)
        assert len(results) == 1

    def test_prune_expired(self, mem: UnifiedMemoryStore) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        mem.store("test", "e1", "Expired", expires_at=past)
        mem.store("test", "e2", "Expired", expires_at=past)
        mem.store("test", "f", "Future", expires_at=future)
        count = mem.prune_expired()
        assert count == 2
        assert mem.count("test") == 1


class TestEmbeddings:
    def test_store_embedding(self, mem: UnifiedMemoryStore) -> None:
        mid = mem.store("test", "emb", "Embedded content")
        assert mem.store_embedding(mid, [0.1, 0.2, 0.3]) is True

    def test_store_embedding_nonexistent(self, mem: UnifiedMemoryStore) -> None:
        assert mem.store_embedding(99999, [0.1]) is False

    def test_get_without_embeddings(self, mem: UnifiedMemoryStore) -> None:
        mid = mem.store("test", "no_emb", "No embedding")
        mem.store("test", "with_emb", "With embedding")
        mem.store_embedding(mid, [0.1, 0.2])
        results = mem.get_without_embeddings(namespace="test")
        assert len(results) == 1
        assert results[0]["key"] == "with_emb"


class TestNamespaces:
    def test_list_namespaces(self, mem: UnifiedMemoryStore) -> None:
        mem.store("cateye", "f1", "Finding")
        mem.store("atlas", "p1", "Portfolio")
        mem.store("copilot", "d1", "Decision")
        namespaces = mem.list_namespaces()
        assert "cateye" in namespaces
        assert "atlas" in namespaces
        assert "copilot" in namespaces

    def test_count(self, mem: UnifiedMemoryStore) -> None:
        mem.store("ns1", "a", "A")
        mem.store("ns1", "b", "B")
        mem.store("ns2", "c", "C")
        assert mem.count() == 3
        assert mem.count("ns1") == 2
        assert mem.count("ns2") == 1


class TestStats:
    def test_get_stats(self, mem: UnifiedMemoryStore) -> None:
        mem.store("ns1", "a", "A")
        mem.store("ns1", "b", "B")
        mem.store("ns2", "c", "C")
        stats = mem.get_stats()
        assert stats["total_entries"] == 3
        assert stats["namespaces"] == 2


class TestSingleton:
    def test_singleton(self) -> None:
        s1 = get_memory_store()
        s2 = get_memory_store()
        assert s1 is s2
