from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from core.execution.compiler import CompiledWorkflow, Opcode
from core.execution.runtime.clock import VirtualClock
from core.execution.runtime.dispatcher import CapabilityDispatcher
from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.state_machine import WorkflowState
from core.execution.runtime.worker import WorkerEngine

logger = logging.getLogger("ownex.execution.simulation")


@dataclass
class SimulationReport:
    workflow_id: str = ""
    workflow_name: str = ""
    duration_ms: float = 0.0
    node_count: int = 0
    capability_calls: int = 0
    api_calls: int = 0
    estimated_cost_usd: float = 0.0
    tokens_used: int = 0
    expected_findings: int = 0
    retries: int = 0
    failures: int = 0
    risk_score: float = 0.0
    risk_level: str = "low"
    simulation_seconds: float = 0.0
    events_published: int = 0
    log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "duration_ms": self.duration_ms,
            "node_count": self.node_count,
            "capability_calls": self.capability_calls,
            "api_calls": self.api_calls,
            "estimated_cost_usd": self.estimated_cost_usd,
            "tokens_used": self.tokens_used,
            "expected_findings": self.expected_findings,
            "retries": self.retries,
            "failures": self.failures,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "simulation_seconds": self.simulation_seconds,
            "events_published": self.events_published,
        }


def _make_fake_execute(cost_per_call: float, tokens_per_call: int) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    """Factory: returns a fake capability executor for simulation mode."""

    def execute(capability: str, params: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": True,
            "simulated": True,
            "capability": capability,
            "cost_usd": cost_per_call,
            "tokens_used": tokens_per_call,
            "api_calls": 0,
            "data": {"simulated": True, "params": params},
        }
        if "finding" in capability or "vuln" in capability or "scan" in capability:
            result["findings"] = [
                {"name": f"Simulated finding from {capability}", "severity": "medium"},
            ]
            result["finding_count"] = 1
        return result

    return execute


class SimulationRuntime:
    """Deterministic execution in simulation mode.

    - No real APIs called
    - No money spent
    - No external systems modified
    - Results are reproducible
    - Produces a SimulationReport

    Usage:
        sim = SimulationRuntime()
        report = sim.run(workflow, compiled)
        logger.info(report.to_dict())
    """

    def __init__(
        self,
        kernel: ExecutionKernel | None = None,
        dispatcher: CapabilityDispatcher | None = None,
        clock: VirtualClock | None = None,
        cost_per_call: float = 0.0,
        tokens_per_call: int = 0,
    ) -> None:
        self.clock = clock or VirtualClock(simulation=True)
        self.kernel = kernel or ExecutionKernel(clock=self.clock)

        fake_execute = _make_fake_execute(cost_per_call, tokens_per_call)
        self.dispatcher = dispatcher or CapabilityDispatcher(execute_fn=fake_execute)

        self.worker = WorkerEngine(self.kernel, self.dispatcher, self.clock)

    def run(
        self,
        compiled: CompiledWorkflow,
        execution_id: str | None = None,
    ) -> SimulationReport:
        report = SimulationReport(
            workflow_id=compiled.workflow_id,
            workflow_name=compiled.workflow_name,
            simulation_seconds=0.0,
        )

        eid = (
            execution_id
            or self.kernel.create_context(
                workflow_id=compiled.workflow_id,
            ).execution_id
        )

        ctx = self.kernel.get_context(eid)
        if not ctx:
            msg = f"Context {eid} not found"
            raise RuntimeError(msg)

        self.kernel.set_workflow_state(eid, WorkflowState.EXECUTING)
        self.kernel.publisher.execution_started(eid, compiled.workflow_id)

        t0 = self.clock.now()

        for inst in compiled.bytecode:
            if self.clock.simulation:
                self.clock.wait(1)  # simulate processing time

            result = self.worker.execute_node(eid, inst)

            if inst.opcode == Opcode.CALL_CAPABILITY:
                report.capability_calls += 1
                findings = result.get("output", {}).get("findings", [])
                report.expected_findings += len(findings)

            if not result.get("success"):
                report.failures += 1
                report.log.append(f"[FAIL] Node {inst.node_id}: {result.get('error')}")
            else:
                report.log.append(f"[OK] Node {inst.node_id} ({inst.opcode})")

            # Track costs
            if result.get("cost_usd"):
                report.estimated_cost_usd += result.get("cost_usd", 0)
            if result.get("tokens_used"):
                report.tokens_used += result.get("tokens_used", 0)

        report.duration_ms = (self.clock.now() - t0) * 1000
        report.simulation_seconds = report.duration_ms / 1000
        report.node_count = compiled.bytecode_count

        # Risk calculation
        if report.failures > 0:
            report.risk_score = min(1.0, report.failures / max(1, report.node_count))
        if report.risk_score > 0.5:
            report.risk_level = "high"
        elif report.risk_score > 0.2:
            report.risk_level = "medium"

        # Count events
        if ctx:
            report.events_published = len(ctx.events)

        self.kernel.set_workflow_state(eid, WorkflowState.FINISHED)
        self.kernel.publisher.execution_completed(eid, report.to_dict())

        logger.info(
            "[Simulation] %s: %d nodes, %.1fms, %d findings, $%.4f cost, risk=%s",
            compiled.workflow_name,
            report.node_count,
            report.duration_ms,
            report.expected_findings,
            report.estimated_cost_usd,
            report.risk_level,
        )

        return report

    @classmethod
    def run_workflow(
        cls,
        compiled: CompiledWorkflow,
        cost_per_call: float = 0.0,
        tokens_per_call: int = 0,
    ) -> SimulationReport:
        sim = cls(cost_per_call=cost_per_call, tokens_per_call=tokens_per_call)
        return sim.run(compiled)
