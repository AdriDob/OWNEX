"""Execution Queue v1 — transiciones y estados terminales."""

from __future__ import annotations

import pytest

from core.execution_queue import assert_transition, can_transition, is_terminal


def test_happy_path_to_paid() -> None:
    path = [
        "discovered",
        "qualified",
        "ready",
        "queued",
        "executing",
        "waiting_human",
        "submitted",
        "verification",
        "paid",
    ]
    for cur, nxt in zip(path, path[1:], strict=False):
        assert can_transition(cur, nxt)


def test_skip_is_invalid() -> None:
    assert not can_transition("discovered", "queued")
    assert not can_transition("executing", "paid")


def test_human_gate_round_trip() -> None:
    assert can_transition("waiting_human", "executing")
    assert can_transition("waiting_human", "rejected")


def test_retry_and_dead_letter() -> None:
    assert can_transition("failed", "queued")
    assert can_transition("failed", "dead_letter")


def test_terminal_states() -> None:
    assert is_terminal("paid") and is_terminal("rejected") and is_terminal("blocked")
    assert not is_terminal("executing")


def test_invalid_raises() -> None:
    with pytest.raises(ValueError):
        assert_transition("discovered", "paid")
