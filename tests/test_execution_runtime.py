from __future__ import annotations

import time as _real_time

import pytest

from core.execution.compiler import BytecodeInstruction, Opcode
from core.execution.runtime.api import RuntimeAPI
from core.execution.runtime.approval import ApprovalManager
from core.execution.runtime.checkpoint import CheckpointManager
from core.execution.runtime.clock import VirtualClock
from core.execution.runtime.context import RuntimeContext, RuntimeMetrics
from core.execution.runtime.dispatcher import CapabilityDispatcher
from core.execution.runtime.journal import ExecutionJournal
from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.metrics import MetricsEngine
from core.execution.runtime.publisher import ExecutionEventPublisher
from core.execution.runtime.resource import ResourceManager
from core.execution.runtime.retry import RetryEngine, RetryPolicy
from core.execution.runtime.rollback import RollbackEngine
from core.execution.runtime.scheduler import Scheduler
from core.execution.runtime.state_machine import (
    NodeState,
    TransitionError,
    WorkflowState,
    enforce_node_transition,
    enforce_workflow_transition,
    validate_node_transition,
    validate_workflow_transition,
)
from core.execution.runtime.timeout import TimeoutEngine
from core.execution.runtime.worker import WorkerEngine

# ═══════════════════════════════════════════════════════════════════════════
# EP-5A: VirtualClock
# ═══════════════════════════════════════════════════════════════════════════


class TestVirtualClock:
    def test_now_real_mode(self) -> None:
        clock = VirtualClock(simulation=False)
        n = clock.now()
        assert n > 0

    def test_now_simulation_mode(self) -> None:
        clock = VirtualClock(simulation=True)
        n0 = clock.now()
        clock.advance(500)
        n1 = clock.now()
        assert n1 > n0
        assert abs((n1 - n0) * 1000 - 500) < 1

    def test_wait_real_mode(self) -> None:
        clock = VirtualClock(simulation=False)
        t0 = _real_time.time()
        clock.wait(50)
        dt = (_real_time.time() - t0) * 1000
        assert dt >= 40

    def test_wait_simulation_mode(self) -> None:
        clock = VirtualClock(simulation=True)
        n0 = clock.now()
        clock.wait(100)
        n1 = clock.now()
        assert abs((n1 - n0) * 1000 - 100) < 1

    def test_advance_triggers_timers(self) -> None:
        clock = VirtualClock(simulation=True)
        fired: list[str] = []

        def cb() -> None:
            fired.append("fired")

        clock.schedule(50, cb)
        assert clock.pending_timers == 1
        clock.advance(100)
        assert len(fired) == 1
        assert clock.pending_timers == 0

    def test_cancel_timer(self) -> None:
        clock = VirtualClock(simulation=True)
        fired: list[str] = []

        def cb() -> None:
            fired.append("fired")

        tid = clock.schedule(50, cb)
        clock.cancel(tid)
        clock.advance(100)
        assert len(fired) == 0

    def test_pause_resume(self) -> None:
        clock = VirtualClock(simulation=True)
        assert not clock.is_paused
        clock.pause()
        assert clock.is_paused
        clock.resume()
        assert not clock.is_paused

    def test_advance_raises_in_real_mode(self) -> None:
        clock = VirtualClock(simulation=False)
        with pytest.raises(RuntimeError, match="simulation"):
            clock.advance(10)


# ═══════════════════════════════════════════════════════════════════════════
# EP-5A: RuntimeContext
# ═══════════════════════════════════════════════════════════════════════════


class TestRuntimeContext:
    def test_create_context(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        assert ctx.workflow_id == "wf1"
        assert ctx.execution_id
        assert ctx.correlation_id
        assert ctx.state.value == "created"

    def test_set_get_variable(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        ctx.set_variable("url", "https://example.com")
        assert ctx.get_variable("url") == "https://example.com"
        assert ctx.get_variable("missing", default=42) == 42

    def test_node_state_lifecycle(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        ctx.set_node_state("n1", NodeState.READY)
        ns = ctx.get_node_state("n1")
        assert ns is not None
        assert ns.node_id == "n1"
        assert ns.status.value == "ready"

    def test_context_snapshot(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        ctx.set_variable("key", "val")
        snap = ctx.snapshot()
        assert snap["workflow_id"] == "wf1"
        assert snap["variables"]["key"] == "val"
        assert snap["state"] == "created"

    def test_add_error(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        ctx.add_error("something broke")
        assert "something broke" in ctx.errors

    def test_metrics_to_dict(self) -> None:
        m = RuntimeMetrics()
        m.cpu_ms = 100.0
        m.tokens_used = 500
        d = m.to_dict()
        assert d["cpu_ms"] == 100.0
        assert d["tokens_used"] == 500


# ═══════════════════════════════════════════════════════════════════════════
# EP-5D: State Machine
# ═══════════════════════════════════════════════════════════════════════════


class TestStateMachine:
    def test_valid_node_transition(self) -> None:
        assert validate_node_transition(NodeState.PENDING, NodeState.READY)
        assert validate_node_transition(NodeState.READY, NodeState.RUNNING)
        assert validate_node_transition(NodeState.RUNNING, NodeState.COMPLETED)
        assert validate_node_transition(NodeState.RUNNING, NodeState.FAILED)

    def test_invalid_node_transition(self) -> None:
        assert not validate_node_transition(NodeState.PENDING, NodeState.COMPLETED)
        assert not validate_node_transition(NodeState.PENDING, NodeState.FAILED)
        assert not validate_node_transition(NodeState.COMPLETED, NodeState.RUNNING)

    def test_enforce_node_transition_raises(self) -> None:
        with pytest.raises(TransitionError):
            enforce_node_transition(NodeState.COMPLETED, NodeState.RUNNING)

    def test_valid_workflow_transition(self) -> None:
        assert validate_workflow_transition(WorkflowState.CREATED, WorkflowState.VALIDATED)
        assert validate_workflow_transition(WorkflowState.COMPILED, WorkflowState.EXECUTING)
        assert validate_workflow_transition(WorkflowState.EXECUTING, WorkflowState.FINISHED)

    def test_invalid_workflow_transition(self) -> None:
        assert not validate_workflow_transition(WorkflowState.CREATED, WorkflowState.FINISHED)
        assert not validate_workflow_transition(WorkflowState.FINISHED, WorkflowState.EXECUTING)

    def test_enforce_workflow_transition_raises(self) -> None:
        with pytest.raises(TransitionError):
            enforce_workflow_transition(WorkflowState.CREATED, WorkflowState.FINISHED)

    def test_all_node_states_defined(self) -> None:
        expected = {
            NodeState.PENDING,
            NodeState.READY,
            NodeState.RUNNING,
            NodeState.WAITING,
            NodeState.PAUSED,
            NodeState.RETRYING,
            NodeState.APPROVED,
            NodeState.SKIPPED,
            NodeState.ROLLBACK,
            NodeState.COMPLETED,
            NodeState.FAILED,
            NodeState.CANCELLED,
        }
        assert set(NodeState) == expected

    def test_all_workflow_states_defined(self) -> None:
        expected = {
            WorkflowState.CREATED,
            WorkflowState.VALIDATED,
            WorkflowState.COMPILED,
            WorkflowState.EXECUTING,
            WorkflowState.PAUSED,
            WorkflowState.WAITING_APPROVAL,
            WorkflowState.ROLLING_BACK,
            WorkflowState.ROLLED_BACK,
            WorkflowState.FINISHED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
            WorkflowState.SIMULATING,
        }
        assert set(WorkflowState) == expected

    def test_node_retrying_cycle(self) -> None:
        assert validate_node_transition(NodeState.FAILED, NodeState.RETRYING)
        assert validate_node_transition(NodeState.RETRYING, NodeState.READY)
        assert validate_node_transition(NodeState.READY, NodeState.RUNNING)

    def test_node_skip_from_pending(self) -> None:
        assert validate_node_transition(NodeState.PENDING, NodeState.SKIPPED)
        assert validate_node_transition(NodeState.READY, NodeState.SKIPPED)

    def test_node_waiting_cycle(self) -> None:
        assert validate_node_transition(NodeState.RUNNING, NodeState.WAITING)
        assert validate_node_transition(NodeState.WAITING, NodeState.RUNNING)


# ═══════════════════════════════════════════════════════════════════════════
# EP-5L: ExecutionJournal
# ═══════════════════════════════════════════════════════════════════════════


class TestExecutionJournal:
    def test_create_journal(self) -> None:
        j = ExecutionJournal(execution_id="e1", workflow_id="wf1", correlation_id="c1")
        assert j.execution_id == "e1"
        assert j.entry_count == 0

    def test_record_entry(self) -> None:
        j = ExecutionJournal(execution_id="e1", workflow_id="wf1", correlation_id="c1")
        entry = j.create_entry(
            node_id="n1",
            node_type="capability",
            timestamp=100.0,
            input_data={"url": "https://x.com"},
            output_data={"status": 200},
            duration_ms=50.0,
        )
        assert entry.entry_id
        assert j.entry_count == 1
        assert j.get_entry(entry.entry_id) is entry

    def test_get_node_entries(self) -> None:
        j = ExecutionJournal(execution_id="e1", workflow_id="wf1", correlation_id="c1")
        j.create_entry(node_id="n1", node_type="start", timestamp=1.0)
        j.create_entry(node_id="n2", node_type="capability", timestamp=2.0)
        j.create_entry(node_id="n1", node_type="end", timestamp=3.0)
        n1_entries = j.get_node_entries("n1")
        assert len(n1_entries) == 2

    def test_replay(self) -> None:
        j = ExecutionJournal(execution_id="e1", workflow_id="wf1", correlation_id="c1")
        j.create_entry(node_id="n1", node_type="start", timestamp=1.0)
        j.create_entry(node_id="n2", node_type="end", timestamp=2.0)
        entries = j.replay()
        assert len(entries) == 2
        assert entries[0].node_id == "n1"

    def test_clear(self) -> None:
        j = ExecutionJournal(execution_id="e1", workflow_id="wf1", correlation_id="c1")
        j.create_entry(node_id="n1", node_type="start", timestamp=1.0)
        assert j.entry_count == 1
        j.clear()
        assert j.entry_count == 0

    def test_to_dict(self) -> None:
        j = ExecutionJournal(execution_id="e1", workflow_id="wf1", correlation_id="c1")
        j.create_entry(node_id="n1", node_type="start", timestamp=1.0)
        d = j.to_dict()
        assert len(d) == 1
        assert d[0]["node_id"] == "n1"


# ═══════════════════════════════════════════════════════════════════════════
# ExecutionKernel
# ═══════════════════════════════════════════════════════════════════════════


class TestExecutionKernel:
    def test_create_context(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        assert ctx.workflow_id == "wf1"
        assert kernel.has_context(ctx.execution_id)

    def test_get_context(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        assert kernel.get_context(ctx.execution_id) is ctx

    def test_get_journal(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        j = kernel.get_journal(ctx.execution_id)
        assert j is not None
        assert j.execution_id == ctx.execution_id

    def test_workflow_state_transition(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        assert kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        assert kernel.get_workflow_state(ctx.execution_id) == WorkflowState.EXECUTING

    def test_workflow_state_invalid(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        assert not kernel.set_workflow_state(ctx.execution_id, WorkflowState.FINISHED)

    def test_node_state_transition(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        assert kernel.set_node_state(ctx.execution_id, "n1", NodeState.READY)
        assert kernel.set_node_state(ctx.execution_id, "n1", NodeState.RUNNING)
        assert kernel.set_node_state(ctx.execution_id, "n1", NodeState.COMPLETED)

    def test_node_state_invalid(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        assert not kernel.set_node_state(ctx.execution_id, "n1", NodeState.COMPLETED)

    def test_journal_record(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.journal_record(
            execution_id=ctx.execution_id,
            node_id="n1",
            node_type="capability",
            input_data={"url": "x"},
        )
        j = kernel.get_journal(ctx.execution_id)
        assert j is not None
        assert j.entry_count == 1

    def test_set_get_variable(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_variable(ctx.execution_id, "key", "value")
        assert kernel.get_variable(ctx.execution_id, "key") == "value"
        assert kernel.get_variable(ctx.execution_id, "missing", 42) == 42

    def test_remove_context(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        eid = ctx.execution_id
        assert kernel.has_context(eid)
        kernel.remove_context(eid)
        assert not kernel.has_context(eid)

    def test_clear(self) -> None:
        kernel = ExecutionKernel()
        kernel.create_context(workflow_id="wf1")
        kernel.create_context(workflow_id="wf2")
        kernel.clear()
        assert not kernel.has_context("any")


# ═══════════════════════════════════════════════════════════════════════════
# EP-5K: ExecutionEventPublisher
# ═══════════════════════════════════════════════════════════════════════════


class TestExecutionEventPublisher:
    def test_publish_without_bind(self) -> None:
        from core.execution.runtime.publisher import ExecutionEventPublisher

        p = ExecutionEventPublisher()
        p.workflow_started("wf1", "e1", "c1")
        p.node_completed("e1", "n1", {"result": "ok"})

    def test_publish_with_callback(self) -> None:
        published: list[tuple[str, dict]] = []

        def fake_publish(envelope: object) -> None:
            published.append(("called", {}))

        p = ExecutionEventPublisher(publish_fn=fake_publish)
        p.workflow_started("wf1", "e1", "c1")
        assert len(published) == 1

    def test_bind(self) -> None:
        published: list[str] = []

        def fn(envelope: object) -> None:
            published.append("ok")

        p = ExecutionEventPublisher()
        p.bind(fn)
        p.execution_started("e1", "wf1")
        assert len(published) == 1


# ═══════════════════════════════════════════════════════════════════════════
# EP-5E: CapabilityDispatcher
# ═══════════════════════════════════════════════════════════════════════════


class TestCapabilityDispatcher:
    def test_dispatch_success(self) -> None:
        def execute(cap: str, params: dict) -> dict:
            return {"success": True, "data": "ok"}

        d = CapabilityDispatcher(execute_fn=execute)
        ctx = RuntimeContext(workflow_id="wf1")
        result = d.dispatch("test:ping", {}, ctx)
        assert result["success"]

    def test_dispatch_failure(self) -> None:
        d = CapabilityDispatcher()
        ctx = RuntimeContext(workflow_id="wf1")
        result = d.dispatch("test:fail", {}, ctx)
        assert not result["success"]

    def test_permission_denied(self) -> None:
        def perm_check(eid: str, cap: str) -> bool:
            return False

        def execute(cap: str, params: dict) -> dict:
            return {"success": True}

        d = CapabilityDispatcher(execute_fn=execute, permission_check_fn=perm_check)
        ctx = RuntimeContext(workflow_id="wf1")
        result = d.dispatch("test:deny", {}, ctx)
        assert not result["success"]
        assert "denied" in result.get("error", "")

    def test_rate_limited(self) -> None:
        def rl(cap: str) -> bool:
            return False

        def execute(cap: str, params: dict) -> dict:
            return {"success": True}

        d = CapabilityDispatcher(execute_fn=execute, rate_limit_fn=rl)
        ctx = RuntimeContext(workflow_id="wf1")
        result = d.dispatch("test:limited", {}, ctx)
        assert not result["success"]
        assert "Rate limit" in result.get("error", "")


# ═══════════════════════════════════════════════════════════════════════════
# EP-5C: WorkerEngine
# ═══════════════════════════════════════════════════════════════════════════


class TestWorkerEngine:
    def test_execute_nop(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.NOP, node_id="n1")
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]

    def test_execute_halt(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.HALT, node_id="n1")
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]

    def test_execute_capability(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)

        def execute(cap: str, params: dict) -> dict:
            return {"success": True, "data": "done"}

        dispatcher = CapabilityDispatcher(execute_fn=execute)
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(
            opcode=Opcode.CALL_CAPABILITY,
            args={"capability": "test:scan", "params": {"url": "x"}},
            node_id="n1",
        )
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]

    def test_execute_wait_simulation(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)
        t0 = clock.now()
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.WAIT, args={"duration_ms": 50}, node_id="n1")
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]
        dt = (clock.now() - t0) * 1000
        assert abs(dt - 50) < 1

    def test_execute_condition_true(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        ctx.set_variable("x", 10)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.CONDITION, args={"expression": "x > 5"}, node_id="n1")
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]
        assert result["output"]["condition_result"] is True

    def test_execute_condition_false(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        ctx.set_variable("x", 1)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.CONDITION, args={"expression": "x > 5"}, node_id="n1")
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]
        assert result["output"]["condition_result"] is False

    def test_execute_approval(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(
            opcode=Opcode.REQUEST_APPROVAL,
            args={"required_level": "operator", "reason": "Needs review"},
            node_id="n1",
        )
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]
        assert "approval_id" in result["output"]

    def test_execute_checkpoint(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.CHECKPOINT, node_id="n1")
        result = worker.execute_node(ctx.execution_id, instr)
        assert result["success"]
        cp_id = result["output"].get("checkpoint_id", "")
        assert cp_id in ctx.checkpoints

    def test_journal_after_execution(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.NOP, node_id="n1")
        worker.execute_node(ctx.execution_id, instr)
        j = kernel.get_journal(ctx.execution_id)
        assert j is not None
        assert j.entry_count == 1

    def test_node_state_tracking(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        instr = BytecodeInstruction(opcode=Opcode.NOP, node_id="n1")
        worker.execute_node(ctx.execution_id, instr)
        ns = kernel.get_node_state(ctx.execution_id, "n1")
        assert ns == NodeState.COMPLETED or ns == NodeState.FAILED


# ═══════════════════════════════════════════════════════════════════════════
# EP-5F: CheckpointManager
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckpointManager:
    def test_save_checkpoint(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        cm = CheckpointManager(kernel, snapshot_interval=1)
        cm.increment(ctx.execution_id)
        cp_id = cm.save_checkpoint(ctx, "n1", label="test")
        assert cp_id in ctx.checkpoints

    def test_restore_checkpoint(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        ctx.set_variable("key", "original")
        cm = CheckpointManager(kernel, snapshot_interval=1)
        cm.increment(ctx.execution_id)
        cp_id = cm.save_checkpoint(ctx, "n1")
        ctx.set_variable("key", "modified")
        assert ctx.get_variable("key") == "modified"
        cm.restore_checkpoint(ctx, cp_id)
        assert ctx.get_variable("key") == "original"

    def test_should_checkpoint(self) -> None:
        kernel = ExecutionKernel()
        cm = CheckpointManager(kernel, snapshot_interval=3)
        assert not cm.should_checkpoint("e1")
        cm.increment("e1")
        assert not cm.should_checkpoint("e1")
        cm.increment("e1")
        assert not cm.should_checkpoint("e1")
        cm.increment("e1")
        assert cm.should_checkpoint("e1")

    def test_list_checkpoints(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        cm = CheckpointManager(kernel, snapshot_interval=1)
        cm.increment(ctx.execution_id)
        cm.save_checkpoint(ctx, "n1")
        cm.increment(ctx.execution_id)
        cm.save_checkpoint(ctx, "n2")
        cps = cm.list_checkpoints(ctx)
        assert len(cps) == 2

    def test_clear_checkpoints(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        cm = CheckpointManager(kernel, snapshot_interval=1)
        cm.increment(ctx.execution_id)
        cm.save_checkpoint(ctx, "n1")
        assert len(ctx.checkpoints) == 1
        cm.clear_checkpoints(ctx)
        assert len(ctx.checkpoints) == 0


# ═══════════════════════════════════════════════════════════════════════════
# EP-5G: RetryEngine
# ═══════════════════════════════════════════════════════════════════════════


class TestRetryEngine:
    def test_immediate_success(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = RetryEngine(clock)
        result, attempts, ok = engine.execute_retry(
            "test:ok",
            lambda: "done",
            max_retries=3,
            policy=RetryPolicy.IMMEDIATE,
        )
        assert ok
        assert result == "done"
        assert attempts == 0

    def test_retry_eventually_succeeds(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = RetryEngine(clock)
        call_count: list[int] = [0]

        def flaky() -> str:
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("not yet")
            return "done"

        result, attempts, ok = engine.execute_retry(
            "test:flaky",
            flaky,
            max_retries=5,
            policy=RetryPolicy.IMMEDIATE,
        )
        assert ok
        assert result == "done"
        assert attempts == 2  # 0-indexed, so 3rd attempt

    def test_retry_exhausted(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = RetryEngine(clock)

        def always_fail() -> str:
            raise ValueError("always")

        result, attempts, ok = engine.execute_retry(
            "test:fail",
            always_fail,
            max_retries=2,
            policy=RetryPolicy.IMMEDIATE,
        )
        assert not ok
        assert attempts == 2

    def test_manual_policy_no_retry(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = RetryEngine(clock)
        assert not engine.should_retry("test:manual", 0, 3, RetryPolicy.MANUAL)

    def test_exponential_delay(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = RetryEngine(clock)
        calls: list[float] = []

        def track() -> None:
            calls.append(clock.now())

        clock.schedule = lambda *a: None  # type: ignore
        engine.execute_retry(
            "test:fail",
            lambda: (_ for _ in ()).throw(ValueError("fail")),
            max_retries=3,
            policy=RetryPolicy.EXPONENTIAL,
            base_delay_ms=10,
            max_delay_ms=1000,
        )
        # Should not crash

    def test_circuit_breaker(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = RetryEngine(clock)
        assert engine._check_circuit_breaker("test:cb", 3, 10000)
        engine._failure_counts["test:cb"] = 5
        assert not engine._check_circuit_breaker("test:cb", 3, 10000)
        assert engine._circuit_open.get("test:cb")


# ═══════════════════════════════════════════════════════════════════════════
# EP-5H: TimeoutEngine
# ═══════════════════════════════════════════════════════════════════════════


class TestTimeoutEngine:
    def test_node_timeout_triggers(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = TimeoutEngine(clock)
        fired: list[str] = []

        def on_timeout() -> None:
            fired.append("timeout")

        engine.start_node_timeout("e1", "n1", 50, on_timeout)
        clock.advance(100)
        assert len(fired) == 1

    def test_cancel_node_timeout(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = TimeoutEngine(clock)
        fired: list[str] = []

        def on_timeout() -> None:
            fired.append("timeout")

        engine.start_node_timeout("e1", "n1", 50, on_timeout)
        assert engine.cancel_node_timeout("e1", "n1")
        clock.advance(100)
        assert len(fired) == 0

    def test_workflow_timeout(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = TimeoutEngine(clock)
        fired: list[str] = []

        def on_timeout() -> None:
            fired.append("wf_timeout")

        engine.start_workflow_timeout("e1", 50, on_timeout)
        clock.advance(100)
        assert len(fired) == 1

    def test_approval_timeout(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = TimeoutEngine(clock)
        fired: list[str] = []

        def on_timeout() -> None:
            fired.append("ap_timeout")

        engine.start_approval_timeout("ap1", 50, on_timeout)
        clock.advance(100)
        assert len(fired) == 1

    def test_active_timeouts_count(self) -> None:
        clock = VirtualClock(simulation=True)
        engine = TimeoutEngine(clock)
        engine.start_node_timeout("e1", "n1", 100, lambda: None)
        engine.start_workflow_timeout("e1", 200, lambda: None)
        assert engine.active_timeouts == 2


# ═══════════════════════════════════════════════════════════════════════════
# EP-5I: RollbackEngine
# ═══════════════════════════════════════════════════════════════════════════


class TestRollbackEngine:
    def test_rollback_to_checkpoint(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        cm = CheckpointManager(kernel, snapshot_interval=1)
        cm.increment(ctx.execution_id)
        ctx.set_variable("key", "before")
        cm.save_checkpoint(ctx, "n1")
        ctx.set_variable("key", "after")
        rollback = RollbackEngine(kernel, cm)
        ok = rollback.rollback(ctx, to_node_id="n1")
        assert ok
        assert ctx.get_variable("key") == "before"

    def test_rollback_latest(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        ctx.set_variable("key", "original")
        cm = CheckpointManager(kernel, snapshot_interval=1)
        cm.increment(ctx.execution_id)
        cm.save_checkpoint(ctx, "n1")
        ctx.set_variable("key", "modified")
        rollback = RollbackEngine(kernel, cm)
        ok = rollback.rollback(ctx)
        assert ok
        assert ctx.get_variable("key") == "original"  # restored from snapshot

    def test_rollback_no_checkpoint(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        cm = CheckpointManager(kernel, snapshot_interval=1)
        rollback = RollbackEngine(kernel, cm)
        ok = rollback.rollback(ctx)
        assert not ok


# ═══════════════════════════════════════════════════════════════════════════
# EP-5B: Scheduler
# ═══════════════════════════════════════════════════════════════════════════


class TestScheduler:
    def test_enqueue_dequeue(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        sched = Scheduler(kernel)
        sched.enqueue(ctx.execution_id, "test", priority=1)
        assert sched.pending_count == 1
        eid = sched.dequeue()
        assert eid == ctx.execution_id

    def test_peek(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        sched = Scheduler(kernel)
        sched.enqueue(ctx.execution_id, "test")
        assert sched.peek() == ctx.execution_id

    def test_cancel(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        sched = Scheduler(kernel)
        sched.enqueue(ctx.execution_id, "test")
        assert sched.cancel(ctx.execution_id)
        assert sched.pending_count == 0

    def test_priority_ordering(self) -> None:
        kernel = ExecutionKernel()
        ctx1 = kernel.create_context(workflow_id="wf-low")
        ctx2 = kernel.create_context(workflow_id="wf-high")
        kernel.set_workflow_state(ctx1.execution_id, WorkflowState.EXECUTING)
        kernel.set_workflow_state(ctx2.execution_id, WorkflowState.EXECUTING)
        sched = Scheduler(kernel)
        sched.enqueue(ctx1.execution_id, "low", priority=10)
        sched.enqueue(ctx2.execution_id, "high", priority=1)
        first = sched.dequeue()
        assert first == ctx2.execution_id  # lower number = higher priority

    def test_assign_worker(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        sched = Scheduler(kernel)
        sched.assign_worker(ctx.execution_id, "worker-1")
        assert sched.get_assigned_worker(ctx.execution_id) == "worker-1"

    def test_clear(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf1")
        sched = Scheduler(kernel)
        sched.enqueue(ctx.execution_id, "test")
        sched.clear()
        assert sched.queue_size == 0


# ═══════════════════════════════════════════════════════════════════════════
# EP-5J: MetricsEngine
# ═══════════════════════════════════════════════════════════════════════════


class TestMetricsEngine:
    def test_record_node_metrics(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        me = MetricsEngine()
        me.record_node_metrics(ctx, cpu_ms=10.0, ram_mb=50.0, tokens_used=100, cost_usd=0.01, api_calls=1)
        assert ctx.metrics.cpu_ms == 10.0
        assert ctx.metrics.ram_mb == 50.0
        assert ctx.metrics.tokens_used == 100
        assert ctx.metrics.api_calls == 1

    def test_record_retry_and_failure(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        me = MetricsEngine()
        me.record_retry(ctx)
        me.record_failure(ctx)
        assert ctx.metrics.retries == 1
        assert ctx.metrics.failures == 1

    def test_collect_and_publish(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        ctx.metrics.api_calls = 5
        me = MetricsEngine()
        metrics = me.collect_and_publish(ctx)
        assert metrics["api_calls"] == 5

    def test_global_metrics(self) -> None:
        ctx = RuntimeContext(workflow_id="wf1")
        ctx.metrics.cost_usd = 10.0
        me = MetricsEngine()
        me.collect_and_publish(ctx)
        global_m = me.get_global_metrics()
        assert global_m["total_executions"] == 1
        assert global_m["total_cost_usd"] >= 10.0


# ═══════════════════════════════════════════════════════════════════════════
# EP-5M: ResourceManager
# ═══════════════════════════════════════════════════════════════════════════


class TestResourceManager:
    def test_register_resource(self) -> None:
        rm = ResourceManager()
        rm.register_resource("shodan", max_concurrency=2)
        assert rm.is_available("shodan")

    def test_acquire_and_release(self) -> None:
        rm = ResourceManager()
        rm.register_resource("shodan", max_concurrency=1)
        assert rm.acquire("shodan", "e1")
        assert not rm.acquire("shodan", "e2")
        rm.release("shodan", "e1")
        assert rm.acquire("shodan", "e2")

    def test_release_all(self) -> None:
        rm = ResourceManager()
        rm.register_resource("vt", max_concurrency=2)
        rm.acquire("vt", "e1")
        rm.acquire("vt", "e2")
        rm.release_all("e1")
        assert rm.is_available("vt")
        rm.release_all("e2")
        assert rm.is_available("vt")

    def test_get_status(self) -> None:
        rm = ResourceManager()
        rm.register_resource("shodan", max_concurrency=2)
        rm.acquire("shodan", "e1")
        status = rm.get_status()
        assert "shodan" in status
        assert status["shodan"]["active"] == 1
        assert status["shodan"]["available"] == 1

    def test_is_available(self) -> None:
        rm = ResourceManager()
        assert rm.is_available("unknown")  # auto-register returns True


# ═══════════════════════════════════════════════════════════════════════════
# EP-5N: ApprovalManager
# ═══════════════════════════════════════════════════════════════════════════


class TestApprovalManager:
    def test_request_approval(self) -> None:
        kernel = ExecutionKernel()
        clock = VirtualClock()
        ctx = kernel.create_context(workflow_id="wf1")
        am = ApprovalManager(kernel, clock)
        ap_id = am.request_approval(ctx, "n1", "Needs review")
        assert ap_id in ctx.approvals

    def test_approve(self) -> None:
        kernel = ExecutionKernel()
        clock = VirtualClock()
        ctx = kernel.create_context(workflow_id="wf1")
        am = ApprovalManager(kernel, clock)
        ap_id = am.request_approval(ctx, "n1")
        assert am.approve(ctx, ap_id)

    def test_reject(self) -> None:
        kernel = ExecutionKernel()
        clock = VirtualClock()
        ctx = kernel.create_context(workflow_id="wf1")
        am = ApprovalManager(kernel, clock)
        ap_id = am.request_approval(ctx, "n1")
        assert am.reject(ctx, ap_id)

    def test_expire(self) -> None:
        kernel = ExecutionKernel()
        clock = VirtualClock()
        ctx = kernel.create_context(workflow_id="wf1")
        am = ApprovalManager(kernel, clock)
        ap_id = am.request_approval(ctx, "n1")
        assert am.expire(ctx, ap_id)

    def test_pending_approvals(self) -> None:
        kernel = ExecutionKernel()
        clock = VirtualClock()
        ctx = kernel.create_context(workflow_id="wf1")
        am = ApprovalManager(kernel, clock)
        am.request_approval(ctx, "n1")
        am.request_approval(ctx, "n2")
        assert len(am.pending_approvals(ctx)) == 2


# ═══════════════════════════════════════════════════════════════════════════
# EP-5O: RuntimeAPI
# ═══════════════════════════════════════════════════════════════════════════


class TestRuntimeAPI:
    def test_start_execution(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        eid = api.start_execution("wf1")
        assert eid
        ctx = kernel.get_context(eid)
        assert ctx is not None
        assert kernel.get_workflow_state(eid) == WorkflowState.EXECUTING

    def test_pause_resume(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        eid = api.start_execution("wf1")
        assert api.pause_execution(eid)
        assert kernel.get_workflow_state(eid) == WorkflowState.PAUSED
        assert api.resume_execution(eid)
        assert kernel.get_workflow_state(eid) == WorkflowState.EXECUTING

    def test_cancel(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        eid = api.start_execution("wf1")
        assert api.cancel_execution(eid)
        assert kernel.get_workflow_state(eid) == WorkflowState.CANCELLED

    def test_get_status(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        eid = api.start_execution("wf1")
        status = api.get_status(eid)
        assert status is not None
        assert status["execution_id"] == eid
        assert status["state"] == "executing"

    def test_get_status_not_found(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        assert api.get_status("nonexistent") is None

    def test_get_metrics(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        eid = api.start_execution("wf1")
        metrics = api.get_metrics(eid)
        assert metrics is not None
        assert isinstance(metrics, dict)

    def test_get_journal(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        eid = api.start_execution("wf1")
        j = api.get_journal(eid)
        assert j is not None
        assert isinstance(j, list)

    def test_cancel_nonexistent(self) -> None:
        kernel = ExecutionKernel()
        api = RuntimeAPI(kernel)
        assert not api.cancel_execution("nonexistent")


# ═══════════════════════════════════════════════════════════════════════════
# Integration: Full pipeline (simulation mode)
# ═══════════════════════════════════════════════════════════════════════════


class TestFullPipeline:
    def test_simple_workflow_simulation(self) -> None:
        clock = VirtualClock(simulation=True)
        kernel = ExecutionKernel(clock=clock)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        api = RuntimeAPI(kernel)

        eid = api.start_execution("wf-simple")

        instructions = [
            BytecodeInstruction(opcode=Opcode.NOP, node_id="start"),
            BytecodeInstruction(
                opcode=Opcode.CALL_CAPABILITY,
                args={"capability": "test:scan", "params": {"url": "x"}},
                node_id="scan",
            ),
            BytecodeInstruction(opcode=Opcode.HALT, node_id="end"),
        ]

        for instr in instructions:
            result = worker.execute_node(eid, instr)
            if not result["success"]:
                break

        status = api.get_status(eid)
        assert status is not None
        journal = api.get_journal(eid)
        assert journal is not None
        assert len(journal) > 0

    def test_parallel_execution_flow(self) -> None:
        clock = VirtualClock(simulation=True)
        kernel = ExecutionKernel(clock=clock)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        api = RuntimeAPI(kernel)

        eid = api.start_execution("wf-parallel")

        instructions = [
            BytecodeInstruction(opcode=Opcode.NOP, node_id="start"),
            BytecodeInstruction(opcode=Opcode.FORK, args={"branches": ["scan1", "scan2"]}, node_id="fork"),
            BytecodeInstruction(
                opcode=Opcode.CALL_CAPABILITY,
                args={"capability": "test:scan", "params": {"target": "a"}},
                node_id="scan1",
            ),
            BytecodeInstruction(
                opcode=Opcode.CALL_CAPABILITY,
                args={"capability": "test:scan", "params": {"target": "b"}},
                node_id="scan2",
            ),
            BytecodeInstruction(opcode=Opcode.JOIN, node_id="join"),
            BytecodeInstruction(opcode=Opcode.HALT, node_id="end"),
        ]

        for instr in instructions:
            result = worker.execute_node(eid, instr)
            if not result["success"]:
                break

        status = api.get_status(eid)
        assert status is not None

    def test_with_checkpoint_and_rollback(self) -> None:
        clock = VirtualClock(simulation=True)
        kernel = ExecutionKernel(clock=clock)
        cm = CheckpointManager(kernel, snapshot_interval=1)
        rollback = RollbackEngine(kernel, cm)
        api = RuntimeAPI(kernel)

        eid = api.start_execution("wf-cp")
        ctx = kernel.get_context(eid)

        # Set initial variable and save checkpoint
        kernel.set_variable(eid, "data", "important")
        cm.increment(eid)
        cm.save_checkpoint(ctx, "cp1")

        # Modify variable after checkpoint
        kernel.set_variable(eid, "data", "modified")

        # Rollback to checkpoint
        rollback.rollback(ctx, to_node_id="cp1")
        assert ctx.get_variable("data") == "important"

    def test_scheduler_with_workers(self) -> None:
        kernel = ExecutionKernel()
        ctx = kernel.create_context(workflow_id="wf-sched")
        kernel.set_workflow_state(ctx.execution_id, WorkflowState.EXECUTING)
        sched = Scheduler(kernel)
        sched.enqueue(ctx.execution_id, "test", priority=5)

        clock = VirtualClock(simulation=True)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        api = RuntimeAPI(kernel)

        task_id = sched.dequeue()
        assert task_id == ctx.execution_id
        sched.assign_worker(task_id, "worker-1")

        instr = BytecodeInstruction(opcode=Opcode.NOP, node_id="n1")
        worker.execute_node(task_id, instr)

        status = api.get_status(task_id)
        assert status is not None

    def test_deterministic_replay(self) -> None:
        clock = VirtualClock(simulation=True)
        kernel = ExecutionKernel(clock=clock)
        dispatcher = CapabilityDispatcher()
        worker = WorkerEngine(kernel, dispatcher, clock)
        api = RuntimeAPI(kernel)

        eid = api.start_execution("wf-replay")

        instructions = [
            BytecodeInstruction(opcode=Opcode.NOP, node_id="start"),
            BytecodeInstruction(opcode=Opcode.WAIT, args={"duration_ms": 50}, node_id="wait"),
            BytecodeInstruction(opcode=Opcode.HALT, node_id="end"),
        ]

        for instr in instructions:
            worker.execute_node(eid, instr)

        journal = api.get_journal(eid)
        assert journal is not None
        assert len(journal) == 3

        assert journal[0]["node_id"] == "start"
        assert journal[1]["node_id"] == "wait"
        assert journal[2]["node_id"] == "end"
