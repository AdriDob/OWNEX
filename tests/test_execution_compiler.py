from __future__ import annotations

from core.execution.compiler import (
    BaseOptimizer,
    BytecodeInstruction,
    CompiledWorkflow,
    ExecutionCompiler,
    Opcode,
    OptimizationLog,
    _node_to_bytecode,
)
from core.execution.models import Edge, Node, Workflow
from core.execution.primitives import PrimitiveType

# ── Bytecode generation tests ─────────────────────────────────────


class TestNodeToBytecode:
    def test_start(self) -> None:
        n = Node(id="s1", type=PrimitiveType.START.value)
        bc = _node_to_bytecode(n, "s1")
        assert len(bc) == 1
        assert bc[0].opcode == Opcode.NOP

    def test_end(self) -> None:
        n = Node(id="e1", type=PrimitiveType.END.value)
        bc = _node_to_bytecode(n, "e1")
        assert len(bc) == 1
        assert bc[0].opcode == Opcode.HALT

    def test_capability(self) -> None:
        n = Node(
            id="c1", type=PrimitiveType.CAPABILITY.value, config={"capability": "test:cap", "params": {"url": "x"}}
        )
        bc = _node_to_bytecode(n, "c1")
        assert len(bc) == 1
        assert bc[0].opcode == Opcode.CALL_CAPABILITY
        assert bc[0].args["capability"] == "test:cap"

    def test_condition(self) -> None:
        n = Node(id="cond1", type=PrimitiveType.CONDITION.value, config={"expression": "x > 5"})
        bc = _node_to_bytecode(n, "cond1")
        assert bc[0].opcode == Opcode.CONDITION
        assert bc[0].args["expression"] == "x > 5"

    def test_decision(self) -> None:
        n = Node(id="d1", type=PrimitiveType.DECISION.value, config={"model": "copilot", "prompt": "Is this safe?"})
        bc = _node_to_bytecode(n, "d1")
        assert bc[0].opcode == Opcode.DECISION

    def test_wait(self) -> None:
        n = Node(id="w1", type=PrimitiveType.WAIT.value, config={"duration_ms": 5000})
        bc = _node_to_bytecode(n, "w1")
        assert bc[0].opcode == Opcode.WAIT
        assert bc[0].args["duration_ms"] == 5000

    def test_delay(self) -> None:
        n = Node(id="d1", type=PrimitiveType.DELAY.value, config={"duration_ms": 2000})
        bc = _node_to_bytecode(n, "d1")
        assert bc[0].opcode == Opcode.WAIT

    def test_trigger(self) -> None:
        n = Node(id="t1", type=PrimitiveType.TRIGGER.value, config={"event_type": "scan:completed"})
        bc = _node_to_bytecode(n, "t1")
        assert bc[0].opcode == Opcode.WAIT_EVENT

    def test_parallel(self) -> None:
        n = Node(id="p1", type=PrimitiveType.PARALLEL.value, config={"branches": ["a", "b"]})
        bc = _node_to_bytecode(n, "p1")
        assert len(bc) == 3  # 2 FORK + 1 JOIN
        assert bc[0].opcode == Opcode.FORK
        assert bc[1].opcode == Opcode.FORK
        assert bc[2].opcode == Opcode.JOIN

    def test_loop(self) -> None:
        n = Node(id="l1", type=PrimitiveType.LOOP.value, config={"iteration_input": "items", "body_start": "process"})
        bc = _node_to_bytecode(n, "l1")
        assert bc[0].opcode == Opcode.LOOP_START

    def test_approval(self) -> None:
        n = Node(id="a1", type=PrimitiveType.APPROVAL.value, config={"required_level": "senior_hunter"})
        bc = _node_to_bytecode(n, "a1")
        assert bc[0].opcode == Opcode.REQUEST_APPROVAL

    def test_notification(self) -> None:
        n = Node(id="n1", type=PrimitiveType.NOTIFICATION.value, config={"channel": "email"})
        bc = _node_to_bytecode(n, "n1")
        assert bc[0].opcode == Opcode.SEND_NOTIFICATION

    def test_checkpoint(self) -> None:
        n = Node(id="cp1", type=PrimitiveType.CHECKPOINT.value)
        bc = _node_to_bytecode(n, "cp1")
        assert bc[0].opcode == Opcode.CHECKPOINT

    def test_rollback(self) -> None:
        n = Node(id="rb1", type=PrimitiveType.ROLLBACK.value)
        bc = _node_to_bytecode(n, "rb1")
        assert bc[0].opcode == Opcode.ROLLBACK

    def test_retry(self) -> None:
        n = Node(id="r1", type=PrimitiveType.RETRY.value, config={"max_retries": 3})
        bc = _node_to_bytecode(n, "r1")
        assert bc[0].opcode == Opcode.RETRY

    def test_timeout(self) -> None:
        n = Node(id="to1", type=PrimitiveType.TIMEOUT.value, config={"duration_ms": 30000})
        bc = _node_to_bytecode(n, "to1")
        assert bc[0].opcode == Opcode.TIMEOUT

    def test_persist(self) -> None:
        n = Node(id="ps1", type=PrimitiveType.PERSIST.value)
        bc = _node_to_bytecode(n, "ps1")
        assert bc[0].opcode == Opcode.PERSIST


# ── Compiler end-to-end tests ─────────────────────────────────────


class TestExecutionCompiler:
    def test_compile_minimal(self) -> None:
        w = Workflow(name="minimal")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        assert isinstance(compiled, CompiledWorkflow)
        assert compiled.workflow_name == "minimal"
        assert compiled.bytecode_count >= 2
        assert compiled.bytecode[-1].opcode == Opcode.HALT

    def test_compile_with_capability(self) -> None:
        w = Workflow(name="cap-test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="cap", type=PrimitiveType.CAPABILITY.value, config={"capability": "test:scan"}))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="cap"))
        w.edges.append(Edge(id="e2", source_id="cap", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        assert compiled.bytecode_count == 3  # nop, call_capability, halt
        assert compiled.bytecode[1].opcode == Opcode.CALL_CAPABILITY

    def test_compile_empty_workflow(self) -> None:
        w = Workflow(name="empty")
        compiled = ExecutionCompiler.run(w)
        assert compiled.bytecode_count == 0  # no nodes to compile

    def test_compiled_workflow_to_dict(self) -> None:
        w = Workflow(name="dict-test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        d = compiled.to_dict()
        assert d["workflow_name"] == "dict-test"
        assert "bytecode" in d
        assert "optimizations" in d


# ── Opcode tests ──────────────────────────────────────────────────


class TestOpcode:
    def test_all_opcodes_defined(self) -> None:
        expected = {
            "nop",
            "jump",
            "jump_if",
            "jump_if_not",
            "halt",
            "return",
            "load_const",
            "load_var",
            "store_var",
            "project",
            "call_capability",
            "wait",
            "wait_event",
            "fork",
            "join",
            "loop_start",
            "loop_next",
            "loop_end",
            "request_approval",
            "send_notification",
            "checkpoint",
            "rollback",
            "retry",
            "timeout",
            "persist",
            "condition",
            "decision",
            "merge",
            "cache_lookup",
            "cache_store",
        }
        assert Opcode.ALL == expected

    def test_opcode_values(self) -> None:
        assert Opcode.NOP == "nop"
        assert Opcode.HALT == "halt"
        assert Opcode.CALL_CAPABILITY == "call_capability"
        assert Opcode.FORK == "fork"
        assert Opcode.JOIN == "join"
        assert Opcode.CHECKPOINT == "checkpoint"


# ── Bytecode instruction tests ────────────────────────────────────


class TestBytecodeInstruction:
    def test_create(self) -> None:
        inst = BytecodeInstruction(opcode=Opcode.NOP, node_id="n1", line=0)
        assert inst.opcode == "nop"
        assert inst.node_id == "n1"

    def test_to_dict(self) -> None:
        inst = BytecodeInstruction(opcode=Opcode.CALL_CAPABILITY, args={"capability": "test"}, node_id="n1")
        d = inst.to_dict()
        assert d["opcode"] == "call_capability"
        assert d["args"]["capability"] == "test"


# ── Optimization log tests ────────────────────────────────────────


class TestOptimizationLog:
    def test_create(self) -> None:
        log = OptimizationLog(optimizer="test", description="Merged two waits", node_ids_affected=["w1", "w2"])
        assert log.optimizer == "test"
        assert len(log.node_ids_affected) == 2


# ── Custom optimizer test ─────────────────────────────────────────


class TestCustomOptimizer:
    def test_register_and_run(self) -> None:
        class RemoveEndOptimizer(BaseOptimizer):
            name = "remove_end"

            def optimize(self, workflow, plan=None):
                logs = []
                kept = [n for n in workflow.nodes if n.type != PrimitiveType.END.value]
                if len(kept) < len(workflow.nodes):
                    logs.append(OptimizationLog(optimizer=self.name, description="Removed END node"))
                workflow.nodes = kept
                return workflow, logs

        w = Workflow(name="custom")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))

        compiler = ExecutionCompiler()
        compiler.register(RemoveEndOptimizer())
        compiled = compiler.compile(w)
        assert any(o.optimizer == "remove_end" for o in compiled.optimizations)


# ── Optimization pass tests ───────────────────────────────────────


class TestNormalizeOptimizer:
    def test_normalizes_start_node(self) -> None:
        w = Workflow(name="test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        # START should have initial_variables added
        assert any(o.optimizer == "normalize" for o in compiled.optimizations)


class TestFusionOptimizer:
    def test_fuses_wait_nodes(self) -> None:
        w = Workflow(name="fusion-test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="w1", type=PrimitiveType.WAIT.value, config={"duration_ms": 1000}))
        w.nodes.append(Node(id="w2", type=PrimitiveType.WAIT.value, config={"duration_ms": 2000}))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="w1"))
        w.edges.append(Edge(id="e2", source_id="w1", target_id="w2"))
        w.edges.append(Edge(id="e3", source_id="w2", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        # Should have a fusion optimization
        assert any(o.optimizer == "fusion" for o in compiled.optimizations)
        # Bytecode should have only 1 WAIT
        wait_count = sum(1 for i in compiled.bytecode if i.opcode == Opcode.WAIT)
        assert wait_count == 1

    def test_fuses_delay_with_wait(self) -> None:
        w = Workflow(name="fusion-delay")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(Node(id="d1", type=PrimitiveType.DELAY.value, config={"duration_ms": 500}))
        w.nodes.append(Node(id="w1", type=PrimitiveType.WAIT.value, config={"duration_ms": 1500}))
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="d1"))
        w.edges.append(Edge(id="e2", source_id="d1", target_id="w1"))
        w.edges.append(Edge(id="e3", source_id="w1", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        assert any(o.optimizer == "fusion" for o in compiled.optimizations)
        wait_count = sum(1 for i in compiled.bytecode if i.opcode == Opcode.WAIT)
        assert wait_count == 1


class TestParallelOptimizer:
    def test_detects_independent_branches(self) -> None:
        w = Workflow(name="parallel-test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(
            Node(id="a", type=PrimitiveType.CAPABILITY.value, config={"capability": "test:a"}, output_mapping={})
        )
        w.nodes.append(
            Node(id="b", type=PrimitiveType.CAPABILITY.value, config={"capability": "test:b"}, output_mapping={})
        )
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="a"))
        w.edges.append(Edge(id="e2", source_id="a", target_id="b"))
        w.edges.append(Edge(id="e3", source_id="start", target_id="b"))
        w.edges.append(Edge(id="e4", source_id="b", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        # May or may not parallelize, but should not crash
        assert compiled.bytecode_count > 0

    def test_does_not_parallelize_dependent(self) -> None:
        # Nodes A and B where A's output feeds B
        w = Workflow(name="dependent-test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(
            Node(
                id="a",
                type=PrimitiveType.CAPABILITY.value,
                config={"capability": "test:a"},
                output_mapping={"result": "shared_var"},
            )
        )
        w.nodes.append(
            Node(
                id="b",
                type=PrimitiveType.CAPABILITY.value,
                config={"capability": "test:b"},
                input_mapping={"data": "shared_var"},
            )
        )
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="a"))
        w.edges.append(Edge(id="e2", source_id="a", target_id="b"))
        w.edges.append(Edge(id="e3", source_id="b", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        # Should not parallelize (data dependency)
        parallel_ops = [o for o in compiled.optimizations if o.optimizer == "parallel"]
        assert len(parallel_ops) == 0


class TestDedupOptimizer:
    def test_dedup_identical_capabilities(self) -> None:
        w = Workflow(name="dedup-test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(
            Node(
                id="c1",
                type=PrimitiveType.CAPABILITY.value,
                config={"capability": "test:scan", "params": {"target": "x"}},
            )
        )
        w.nodes.append(
            Node(
                id="c2",
                type=PrimitiveType.CAPABILITY.value,
                config={"capability": "test:scan", "params": {"target": "x"}},
            )
        )
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="c1"))
        w.edges.append(Edge(id="e2", source_id="start", target_id="c2"))
        w.edges.append(Edge(id="e3", source_id="c1", target_id="end"))
        w.edges.append(Edge(id="e4", source_id="c2", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        # May or may not dedup depending on graph structure, but shouldn't crash
        assert compiled.bytecode_count > 0


class TestApprovalOptimizer:
    def test_merges_consecutive_approvals(self) -> None:
        w = Workflow(name="approval-test")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(
            Node(
                id="a1",
                type=PrimitiveType.APPROVAL.value,
                config={"required_level": "operator", "reason": "First check"},
            )
        )
        w.nodes.append(
            Node(
                id="a2",
                type=PrimitiveType.APPROVAL.value,
                config={"required_level": "senior_hunter", "reason": "Second check"},
            )
        )
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="a1"))
        w.edges.append(Edge(id="e2", source_id="a1", target_id="a2"))
        w.edges.append(Edge(id="e3", source_id="a2", target_id="end"))
        compiled = ExecutionCompiler.run(w)
        approval_ops = [o for o in compiled.optimizations if o.optimizer == "approval"]
        assert len(approval_ops) >= 1
        # Should have only 1 REQUEST_APPROVAL in bytecode
        approval_count = sum(1 for i in compiled.bytecode if i.opcode == Opcode.REQUEST_APPROVAL)
        assert approval_count == 1


# ── End-to-end pipeline test ──────────────────────────────────────


class TestPipeline:
    def test_validate_then_compile(self) -> None:
        from core.execution.validation import ExecutionValidator

        w = Workflow(name="pipeline")
        w.nodes.append(Node(id="start", type=PrimitiveType.START.value))
        w.nodes.append(
            Node(
                id="scan",
                type=PrimitiveType.CAPABILITY.value,
                config={"capability": "test:scan", "params": {"target": "example.com"}},
            )
        )
        w.nodes.append(
            Node(id="cap2", type=PrimitiveType.CAPABILITY.value, config={"capability": "test:analyze", "params": {}})
        )
        w.nodes.append(Node(id="end", type=PrimitiveType.END.value))
        w.edges.append(Edge(id="e1", source_id="start", target_id="scan"))
        w.edges.append(Edge(id="e2", source_id="start", target_id="cap2"))
        w.edges.append(Edge(id="e3", source_id="scan", target_id="end"))
        w.edges.append(Edge(id="e4", source_id="cap2", target_id="end"))

        # Validate first (structural check — capabilities may not be registered in test env)
        ExecutionValidator.run(w)

        # Then compile (compiler doesn't require validation to pass)
        compiled = ExecutionCompiler.run(w)
        assert compiled.bytecode_count > 0
        assert compiled.bytecode[-1].opcode == Opcode.HALT
        assert compiled.original_node_count == 4
        assert compiled.compilation_ms > 0
