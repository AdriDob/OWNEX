from __future__ import annotations

import logging
from typing import Any

from core.copilot.permissions import AuthorityLevel
from core.execution.compiler import BytecodeInstruction, Opcode
from core.execution.runtime.checkpoint import CheckpointManager
from core.execution.runtime.clock import VirtualClock
from core.execution.runtime.context import RuntimeContext
from core.execution.runtime.dispatcher import CapabilityDispatcher
from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.publisher import ExecutionEventPublisher
from core.execution.runtime.state_machine import NodeState

logger = logging.getLogger("cateye.execution.worker")


class WorkerEngine:
    """Executes a single workflow node.

    A worker:
      1. Takes a node (bytecode instruction)
      2. Resolves the capability (if CAPABILITY type)
      3. Executes via the Dispatcher
      4. Emits events via the Publisher
      5. Records in the Journal via the Kernel
      6. Updates context state
    """

    def __init__(
        self,
        kernel: ExecutionKernel,
        dispatcher: CapabilityDispatcher,
        clock: VirtualClock,
        publisher: ExecutionEventPublisher | None = None,
    ) -> None:
        self.kernel = kernel
        self.dispatcher = dispatcher
        self.clock = clock
        self.publisher = publisher or kernel.publisher

    def execute_node(
        self,
        execution_id: str,
        instruction: BytecodeInstruction,
    ) -> dict[str, Any]:
        """Execute a single bytecode instruction and return result."""
        ctx = self.kernel.get_context(execution_id)
        if not ctx:
            return {"error": f"Context {execution_id} not found", "success": False}

        node_id = instruction.node_id or "unknown"
        opcode = instruction.opcode
        args = instruction.args or {}

        ctx.current_node_id = node_id
        self.kernel.set_node_state(execution_id, node_id, NodeState.READY)
        self.kernel.set_node_state(execution_id, node_id, NodeState.RUNNING)
        self.publisher.node_started(
            execution_id=execution_id,
            node_id=node_id,
            node_type=opcode,
        )

        result: dict[str, Any] = {"success": True, "output": {}}

        try:
            if opcode == Opcode.NOP:
                result = self._handle_nop(ctx, args)
            elif opcode == Opcode.HALT:
                result = self._handle_halt(ctx, execution_id)
            elif opcode == Opcode.CALL_CAPABILITY:
                result = self._handle_capability(ctx, execution_id, node_id, args)
            elif opcode == Opcode.CONDITION:
                result = self._handle_condition(ctx, args)
            elif opcode == Opcode.DECISION:
                result = self._handle_decision(ctx, args)
            elif opcode == Opcode.WAIT:
                result = self._handle_wait(args)
            elif opcode == Opcode.WAIT_EVENT:
                result = self._handle_wait_event(ctx, args)
            elif opcode == Opcode.FORK:
                result = {"success": True, "output": {"branches": args.get("branches", [])}}
            elif opcode == Opcode.JOIN:
                result = {"success": True, "output": {}}
            elif opcode == Opcode.LOOP_START:
                result = self._handle_loop_start(ctx, args)
            elif opcode == Opcode.REQUEST_APPROVAL:
                result = self._handle_approval(ctx, execution_id, node_id, args)
            elif opcode == Opcode.SEND_NOTIFICATION:
                result = {"success": True, "output": {"notification": args.get("channel", "default")}}
            elif opcode == Opcode.CHECKPOINT:
                result = self._handle_checkpoint(ctx, execution_id, node_id, args)
            elif opcode == Opcode.ROLLBACK:
                result = {"success": True, "output": {"to": args.get("checkpoint_id")}}
            elif opcode == Opcode.RETRY:
                result = self._handle_retry(args)
            elif opcode == Opcode.TIMEOUT:
                result = self._handle_timeout(args)
            elif opcode == Opcode.PERSIST:
                result = self._handle_persist(ctx, args)
            else:
                result = {"success": True, "output": {}}

        except Exception as exc:
            logger.exception("[Worker] Node %s failed: %s", node_id, exc)
            result = {"error": str(exc), "success": False}

        node_type = opcode
        duration_ms = result.get("duration_ms", 0.0)
        self.kernel.journal_record(
            execution_id=execution_id,
            node_id=node_id,
            node_type=node_type,
            input_data=dict(args),
            output_data=result.get("output", {}),
            error=result.get("error"),
            duration_ms=duration_ms,
        )
        self.publisher.journal_entry(
            execution_id=execution_id,
            node_id=node_id,
            node_type=node_type,
            entry={
                "input_data": dict(args),
                "output_data": result.get("output", {}),
                "error": result.get("error"),
                "duration_ms": duration_ms,
            },
        )

        # Update state
        if result.get("success"):
            self.kernel.set_node_state(execution_id, node_id, NodeState.COMPLETED)
            self.publisher.node_completed(
                execution_id=execution_id,
                node_id=node_id,
                output=result.get("output", {}),
            )
        else:
            retry_count = ctx.get_node_state(node_id)
            rc = retry_count.retry_count if retry_count else 0
            self.kernel.set_node_state(execution_id, node_id, NodeState.FAILED)
            self.publisher.node_failed(
                execution_id=execution_id,
                node_id=node_id,
                error=result.get("error", "Unknown error"),
                retry_count=rc,
            )

        return result

    # ── Handler implementations ───────────────────────────────────

    @staticmethod
    def _handle_nop(ctx: RuntimeContext, args: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "output": {}}

    @staticmethod
    def _handle_halt(ctx: RuntimeContext, execution_id: str) -> dict[str, Any]:
        return {"success": True, "output": {"execution_id": execution_id, "status": "completed"}}

    def _handle_capability(
        self,
        ctx: RuntimeContext,
        execution_id: str,
        node_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        capability = args.get("capability", "")
        params = args.get("params", {})
        if not capability:
            return {"error": "No capability specified", "success": False}

        return self.dispatcher.dispatch(capability, params, ctx)

    @staticmethod
    def _handle_condition(ctx: RuntimeContext, args: dict[str, Any]) -> dict[str, Any]:
        expression = args.get("expression", "")
        try:
            env = dict(ctx.variables)
            result = bool(eval(expression, {"__builtins__": {}}, env))
            return {
                "success": True,
                "output": {"condition_result": result, "expression": expression},
                "decision": "true" if result else "false",
            }
        except Exception as exc:
            return {"error": f"Condition evaluation failed: {exc}", "success": False}

    @staticmethod
    def _handle_decision(ctx: RuntimeContext, args: dict[str, Any]) -> dict[str, Any]:
        prompt = args.get("prompt", "")
        options = args.get("options", [])
        selected = options[0] if options else "unknown"
        return {
            "success": True,
            "output": {"decision": selected, "prompt": prompt, "options": options},
            "decision": selected,
        }

    def _handle_wait(self, args: dict[str, Any]) -> dict[str, Any]:
        duration_ms = args.get("duration_ms", 1000)
        self.clock.wait(duration_ms)
        return {"success": True, "output": {"waited_ms": duration_ms}, "duration_ms": duration_ms}

    @staticmethod
    def _handle_wait_event(ctx: RuntimeContext, args: dict[str, Any]) -> dict[str, Any]:
        event_type = args.get("event_type", "")
        return {"success": True, "output": {"event_type": event_type, "received": True}}

    @staticmethod
    def _handle_loop_start(ctx: RuntimeContext, args: dict[str, Any]) -> dict[str, Any]:
        iter_input = args.get("iteration_input", "")
        items = ctx.variables.get(iter_input, [])
        return {
            "success": True,
            "output": {"items": items, "count": len(items), "index": 0},
        }

    @staticmethod
    def _handle_approval(
        ctx: RuntimeContext,
        execution_id: str,
        node_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        required_level = args.get("required_level", AuthorityLevel.OPERATOR.value)
        reason = args.get("reason", "")
        return {
            "success": True,
            "output": {
                "required_level": required_level,
                "reason": reason,
                "status": "pending",
                "approval_id": f"ap_{execution_id[:8]}_{node_id[:8]}",
            },
        }

    def _handle_checkpoint(
        self,
        ctx: RuntimeContext,
        execution_id: str,
        node_id: str,
        args: dict[str, Any],
    ) -> dict[str, Any]:
        cm = CheckpointManager(self.kernel, self.publisher)
        cp_id = cm.save_checkpoint(ctx, node_id)
        return {
            "success": True,
            "output": {"checkpoint_id": cp_id, "node_id": node_id},
        }

    @staticmethod
    def _handle_retry(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "output": {
                "max_retries": args.get("max_retries", 3),
                "base_delay_ms": args.get("base_delay_ms", 1000),
            },
        }

    @staticmethod
    def _handle_timeout(args: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "output": {"duration_ms": args.get("duration_ms", 30000)},
        }

    @staticmethod
    def _handle_persist(ctx: RuntimeContext, args: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "output": {"persisted": True}}
