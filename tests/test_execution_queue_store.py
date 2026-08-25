"""Persistencia de la Execution Queue (JSON atómico)."""

from __future__ import annotations

import pytest

from core.execution_queue import ExecutionQueueStore


@pytest.fixture()
def store(tmp_path):
    return ExecutionQueueStore(tmp_path / "queue.json")


def test_add_and_persist_roundtrip(store: ExecutionQueueStore, tmp_path) -> None:
    store.add("op-1", {"title": "Fix bug"})
    reloaded = ExecutionQueueStore(tmp_path / "queue.json")
    assert reloaded.get("op-1")["payload"]["title"] == "Fix bug"
    assert reloaded.get("op-1")["state"] == "discovered"


def test_transition_validates_and_records_history(store: ExecutionQueueStore) -> None:
    store.add("op-1")
    store.transition("op-1", "qualified")
    item = store.transition("op-1", "ready")
    assert item["history"] == ["discovered", "qualified", "ready"]
    with pytest.raises(ValueError):
        store.transition("op-1", "paid")


def test_pending_by_state(store: ExecutionQueueStore) -> None:
    store.add("a")
    store.add("b")
    store.transition("b", "qualified")
    assert set(store.pending_by_state("discovered")) == {"a"}
    assert set(store.pending_by_state("qualified")) == {"b"}
