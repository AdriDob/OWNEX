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


class TestExecutorHonesty:
    def test_mutating_action_gated_without_approval(self, monkeypatch):
        import core.execution_queue.driver as drv

        called = []

        class FakeExec:
            async def execute(self, action, **kw):
                called.append(action)
                from cores.opportunity.executors import ExecutionResult

                return ExecutionResult(True, action, "x")

        import sys
        import types

        mod = types.ModuleType("fake_exec_mod")
        mod.FakeExec = FakeExec
        sys.modules["fake_exec_mod"] = mod
        monkeypatch.setattr(drv, "_MUTATING_ACTIONS", {"submit_work"} | drv._MUTATING_ACTIONS)

        res = drv._run_platform_executor("fake_exec_mod", "FakeExec", "submit_work", {"bounty_id": "1"})
        assert res["requires_human"] is True
        assert res["submitted"] is False
        assert called == []  # executor never invoked — gate is pre-call

    def test_read_action_never_submitted(self, tmp_path, monkeypatch):
        import core.execution_queue.driver as drv

        class FakeExec:
            async def execute(self, action, **kw):
                from cores.opportunity.executors import ExecutionResult

                return ExecutionResult(True, action, "x")

        import sys
        import types

        mod = types.ModuleType("fake_exec_mod2")
        mod.FakeExec = FakeExec
        sys.modules["fake_exec_mod2"] = mod

        res = drv._run_platform_executor("fake_exec_mod2", "FakeExec", "get_bounties", {})
        assert res["submitted"] is False
        assert res["requires_human"] is False
        assert res["result"].success is True

    def test_approved_mutating_reports_submitted(self, tmp_path, monkeypatch):
        import core.execution_queue.driver as drv

        class FakeExec:
            async def execute(self, action, **kw):
                assert kw.get("bounty_id") == "b1"
                assert "approved" not in kw
                from cores.opportunity.executors import ExecutionResult

                return ExecutionResult(True, action, "b1")

        import sys
        import types

        mod = types.ModuleType("fake_exec_mod3")
        mod.FakeExec = FakeExec
        sys.modules["fake_exec_mod3"] = mod

        res = drv._run_platform_executor("fake_exec_mod3", "FakeExec", "submit_work", {"bounty_id": "b1", "approved": True})
        assert res["submitted"] is True
        assert res["requires_human"] is False
