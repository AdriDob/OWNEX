from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.execution.models import Node, Workflow
from core.execution.plan import ExecutionPlan, build_execution_plan
from core.execution.primitives import PrimitiveType

logger = logging.getLogger("orion.core.execution.compiler")


# ── Bytecode instruction set ──────────────────────────────────────
# Each instruction is a step the Runtime state machine can execute.
# No YAML/JSON interpretation at runtime — only bytecode.


@dataclass
class BytecodeInstruction:
    """A single instruction in the compiled bytecode.

    ``opcode`` determines what the Runtime does.
    ``args`` provides the operands.
    ``node_id`` traces back to the original workflow node (for debugging/replay).
    ``line`` is the instruction index for jump targets.
    """

    opcode: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    node_id: str | None = None
    line: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "opcode": self.opcode,
            "args": self.args,
            "node_id": self.node_id,
            "line": self.line,
        }


# ── Opcode constants ──────────────────────────────────────────────


class Opcode:
    """All bytecode opcodes."""

    # ── Control flow ────────────────────────────────────────────
    NOP = "nop"  # no operation
    JUMP = "jump"  # unconditional jump to line
    JUMP_IF = "jump_if"  # jump if condition var is truthy
    JUMP_IF_NOT = "jump_if_not"  # jump if condition var is falsy
    HALT = "halt"  # stop execution
    RETURN = "return"  # return result

    # ── Variables ───────────────────────────────────────────────
    LOAD_CONST = "load_const"  # load a constant value
    LOAD_VAR = "load_var"  # load a variable from context
    STORE_VAR = "store_var"  # store to context variable
    PROJECT = "project"  # extract subset of fields from a variable

    # ── Capabilities ────────────────────────────────────────────
    CALL_CAPABILITY = "call_capability"  # invoke a registered capability

    # ── Timing ─────────────────────────────────────────────────
    WAIT = "wait"  # sleep for duration_ms
    WAIT_EVENT = "wait_event"  # wait for an event from Event Bus

    # ── Parallel ────────────────────────────────────────────────
    FORK = "fork"  # spawn parallel branch
    JOIN = "join"  # wait for all forked branches

    # ── Loops ───────────────────────────────────────────────────
    LOOP_START = "loop_start"  # begin loop over iterable
    LOOP_NEXT = "loop_next"  # advance to next iteration
    LOOP_END = "loop_end"  # end loop

    # ── Human interaction ───────────────────────────────────────
    REQUEST_APPROVAL = "request_approval"  # pause for human approval
    SEND_NOTIFICATION = "send_notification"  # send notification

    # ── Resilience ──────────────────────────────────────────────
    CHECKPOINT = "checkpoint"  # save execution snapshot
    ROLLBACK = "rollback"  # restore to checkpoint
    RETRY = "retry"  # mark retry boundary
    TIMEOUT = "timeout"  # mark timeout boundary
    PERSIST = "persist"  # persist state to database

    # ── Condition / Decision ────────────────────────────────────
    CONDITION = "condition"  # evaluate condition expression
    DECISION = "decision"  # delegate decision to COPILOT

    # ── Data ────────────────────────────────────────────────────
    MERGE = "merge"  # merge multiple parallel results
    CACHE_LOOKUP = "cache_lookup"  # check KG cache
    CACHE_STORE = "cache_store"  # store in KG cache

    ALL = frozenset(
        {
            NOP,
            JUMP,
            JUMP_IF,
            JUMP_IF_NOT,
            HALT,
            RETURN,
            LOAD_CONST,
            LOAD_VAR,
            STORE_VAR,
            PROJECT,
            CALL_CAPABILITY,
            WAIT,
            WAIT_EVENT,
            FORK,
            JOIN,
            LOOP_START,
            LOOP_NEXT,
            LOOP_END,
            REQUEST_APPROVAL,
            SEND_NOTIFICATION,
            CHECKPOINT,
            ROLLBACK,
            RETRY,
            TIMEOUT,
            PERSIST,
            CONDITION,
            DECISION,
            MERGE,
            CACHE_LOOKUP,
            CACHE_STORE,
        }
    )


# ── Compiler output ───────────────────────────────────────────────


@dataclass
class OptimizationLog:
    """Record of a single optimization applied by the compiler."""

    optimizer: str = ""
    description: str = ""
    node_ids_affected: list[str] = field(default_factory=list)
    before: str = ""
    after: str = ""


@dataclass
class CompiledWorkflow:
    """Final output of the compilation process.

    This is the only thing the Runtime touches.
    No YAML, no JSON interpretation — just bytecode + metadata.
    """

    workflow_id: str = ""
    workflow_name: str = ""
    version: str = "0.1.0"

    # ── Optimized graph ─────────────────────────────────────────
    optimized_workflow: Workflow | None = None

    # ── Execution plan with resolved metadata ───────────────────
    execution_plan: ExecutionPlan | None = None

    # ── Bytecode ────────────────────────────────────────────────
    bytecode: list[BytecodeInstruction] = field(default_factory=list)

    # ── Optimization record ─────────────────────────────────────
    optimizations: list[OptimizationLog] = field(default_factory=list)

    # ── Stats ───────────────────────────────────────────────────
    original_node_count: int = 0
    optimized_node_count: int = 0
    bytecode_count: int = 0
    compilation_ms: float = 0.0

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "version": self.version,
            "execution_plan": self.execution_plan.to_dict() if self.execution_plan else None,
            "bytecode": [i.to_dict() for i in self.bytecode],
            "optimizations": [
                {
                    "optimizer": o.optimizer,
                    "description": o.description,
                    "node_ids_affected": o.node_ids_affected,
                    "before": o.before,
                    "after": o.after,
                }
                for o in self.optimizations
            ],
            "original_node_count": self.original_node_count,
            "optimized_node_count": self.optimized_node_count,
            "bytecode_count": self.bytecode_count,
            "compilation_ms": self.compilation_ms,
            "created_at": self.created_at.isoformat(),
        }


# ── Optimizer base ────────────────────────────────────────────────


class BaseOptimizer:
    """Base class for a compiler optimization pass."""

    name: str = "base"

    def optimize(self, workflow: Workflow, plan: ExecutionPlan | None = None) -> tuple[Workflow, list[OptimizationLog]]:
        """Apply optimization, return (modified_workflow, logs)."""
        raise NotImplementedError


# ── Compiler orchestrator ─────────────────────────────────────────


class ExecutionCompiler:
    """Compiles a validated Workflow into executable bytecode.

    Passes:
    1. Run all optimizer passes (normalize, parallel, fusion, dedup, etc.)
    2. Build ExecutionPlan from optimized workflow
    3. Generate bytecode from optimized workflow
    """

    def __init__(self) -> None:
        self._optimizers: list[BaseOptimizer] = []

    def register(self, optimizer: BaseOptimizer) -> None:
        self._optimizers.append(optimizer)

    def register_all(self, *optimizers: BaseOptimizer) -> None:
        self._optimizers.extend(optimizers)

    def compile(self, workflow: Workflow, existing_plan: ExecutionPlan | None = None) -> CompiledWorkflow:
        import time

        start = time.time()
        all_logs: list[OptimizationLog] = []
        wf = workflow
        original_node_count = len(workflow.nodes)

        # ── Phase 1: Optimize ───────────────────────────────────
        for opt in self._optimizers:
            try:
                wf, logs = opt.optimize(wf, existing_plan)
                all_logs.extend(logs)
            except Exception as exc:
                logger.warning("Optimizer %s failed: %s", opt.name, exc)

        # ── Phase 2: Build ExecutionPlan ─────────────────────────
        node_ids = [n.id for n in wf.nodes]
        plan = build_execution_plan(
            workflow_id=wf.id,
            workflow_name=wf.name,
            node_ids=node_ids,
        )
        plan.validation_score = existing_plan.validation_score if existing_plan else 100.0
        plan.safe = existing_plan.safe if existing_plan else True

        # ── Phase 3: Generate bytecode ───────────────────────────
        bytecode = self._generate_bytecode(wf)
        elapsed = (time.time() - start) * 1000

        return CompiledWorkflow(
            workflow_id=wf.id,
            workflow_name=wf.name,
            optimized_workflow=wf,
            execution_plan=plan,
            bytecode=bytecode,
            optimizations=all_logs,
            original_node_count=original_node_count,
            optimized_node_count=len(wf.nodes),
            bytecode_count=len(bytecode),
            compilation_ms=round(elapsed, 2),
        )

    @staticmethod
    def _generate_bytecode(workflow: Workflow) -> list[BytecodeInstruction]:
        """Compile an optimized workflow graph into linear bytecode.

        Uses a simple topological walk from START through edges.
        """
        node_map = {n.id: n for n in workflow.nodes}
        adjacency: dict[str, list[str]] = {n.id: [] for n in workflow.nodes}
        for edge in workflow.edges:
            if edge.source_id in adjacency:
                adjacency[edge.source_id].append(edge.target_id)

        start_nodes = [n for n in workflow.nodes if n.type == PrimitiveType.START.value]
        if not start_nodes:
            return []

        bc: list[BytecodeInstruction] = []
        visited: set[str] = set()
        stack = [start_nodes[0].id]

        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            node = node_map.get(nid)
            if not node:
                continue

            instrs = _node_to_bytecode(node, nid)
            for inst in instrs:
                inst.line = len(bc)
                bc.append(inst)

            for target in adjacency.get(nid, []):
                if target not in visited:
                    stack.append(target)

        # Ensure we end with HALT
        if not bc or bc[-1].opcode != Opcode.HALT:
            bc.append(BytecodeInstruction(opcode=Opcode.HALT, line=len(bc)))

        return bc

    @classmethod
    def run(cls, workflow: Workflow, plan: ExecutionPlan | None = None) -> CompiledWorkflow:
        """Convenience: create default compiler with all built-in optimizers and compile."""
        compiler = cls()
        _register_builtin_optimizers(compiler)
        return compiler.compile(workflow, plan)


def _node_to_bytecode(node: Node, node_id: str) -> list[BytecodeInstruction]:
    """Convert a single workflow node to one or more bytecode instructions."""
    ptype = node.type

    if ptype == PrimitiveType.START.value:
        return [BytecodeInstruction(opcode=Opcode.NOP, node_id=node_id)]

    if ptype == PrimitiveType.END.value:
        return [BytecodeInstruction(opcode=Opcode.HALT, node_id=node_id)]

    if ptype == PrimitiveType.CAPABILITY.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.CALL_CAPABILITY,
                args={
                    "capability": node.config.get("capability", ""),
                    "params": node.config.get("params", {}),
                    "timeout_ms": node.timeout_ms or node.config.get("timeout_ms", 60000),
                    "input_mapping": node.input_mapping,
                    "output_mapping": node.output_mapping,
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.CONDITION.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.CONDITION,
                args={
                    "expression": node.config.get("expression", ""),
                    "true_target": node.config.get("true_target"),
                    "false_target": node.config.get("false_target"),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.DECISION.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.DECISION,
                args={
                    "model": node.config.get("model", "copilot"),
                    "prompt": node.config.get("prompt", ""),
                    "options": node.config.get("options", []),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.WAIT.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.WAIT,
                args={"duration_ms": node.config.get("duration_ms", 1000)},
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.DELAY.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.WAIT,
                args={"duration_ms": node.config.get("duration_ms", 1000)},
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.TRIGGER.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.WAIT_EVENT,
                args={
                    "event_type": node.config.get("event_type", ""),
                    "timeout_ms": node.config.get("timeout_ms"),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.PARALLEL.value:
        instrs: list[BytecodeInstruction] = []
        branches = node.config.get("branches", [])
        for br_id in branches:
            instrs.append(
                BytecodeInstruction(
                    opcode=Opcode.FORK,
                    args={"branch_id": br_id},
                    node_id=node_id,
                )
            )
        instrs.append(
            BytecodeInstruction(
                opcode=Opcode.JOIN,
                args={},
                node_id=node_id,
            )
        )
        return instrs

    if ptype == PrimitiveType.LOOP.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.LOOP_START,
                args={
                    "iteration_input": node.config.get("iteration_input", ""),
                    "body_start": node.config.get("body_start", ""),
                    "max_iterations": node.config.get("max_iterations", 100),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.APPROVAL.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.REQUEST_APPROVAL,
                args={
                    "required_level": node.config.get("required_level", "operator"),
                    "reason": node.config.get("reason", ""),
                    "timeout_ms": node.config.get("timeout_ms"),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.NOTIFICATION.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.SEND_NOTIFICATION,
                args={
                    "channel": node.config.get("channel", "default"),
                    "title": node.config.get("title", ""),
                    "body": node.config.get("body", ""),
                    "level": node.config.get("level", "info"),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.CHECKPOINT.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.CHECKPOINT,
                args={"label": node.config.get("label", "")},
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.ROLLBACK.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.ROLLBACK,
                args={
                    "to_checkpoint": node.config.get("to_checkpoint"),
                    "strategy": node.config.get("strategy", "restore"),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.RETRY.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.RETRY,
                args={
                    "max_retries": node.config.get("max_retries", 3),
                    "base_delay_ms": node.config.get("base_delay_ms", 1000),
                    "max_delay_ms": node.config.get("max_delay_ms", 60000),
                    "backoff_multiplier": node.config.get("backoff_multiplier", 2.0),
                },
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.TIMEOUT.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.TIMEOUT,
                args={"duration_ms": node.config.get("duration_ms", 30000)},
                node_id=node_id,
            )
        ]

    if ptype == PrimitiveType.PERSIST.value:
        return [
            BytecodeInstruction(
                opcode=Opcode.PERSIST,
                args={},
                node_id=node_id,
            )
        ]

    return [
        BytecodeInstruction(
            opcode=Opcode.NOP,
            args={"original_type": ptype},
            node_id=node_id,
        )
    ]


def _register_builtin_optimizers(compiler: ExecutionCompiler) -> None:
    """Register all built-in optimization passes."""
    from core.execution.optimizers.approval import ApprovalOptimizer
    from core.execution.optimizers.dedup import DedupOptimizer
    from core.execution.optimizers.fusion import FusionOptimizer
    from core.execution.optimizers.normalize import NormalizeOptimizer
    from core.execution.optimizers.parallel import ParallelOptimizer

    compiler.register_all(
        NormalizeOptimizer(),
        FusionOptimizer(),
        DedupOptimizer(),
        ParallelOptimizer(),
        ApprovalOptimizer(),
    )
