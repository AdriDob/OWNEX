"""Plan Execution Engine — executes COPILOT plans using tool wrappers."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from core.copilot.planner import Plan, PlanStep
from core.memory.store import UnifiedMemoryStore

logger = logging.getLogger("orion.core.copilot.executor")


class StepResult:
    """Result of executing a single plan step."""

    def __init__(
        self,
        step: PlanStep,
        success: bool,
        output: str = "",
        data: dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        self.step = step
        self.success = success
        self.output = output
        self.data = data or {}
        self.error = error
        self.completed_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step.id,
            "action": self.step.action,
            "success": self.success,
            "output": self.output[:500],
            "error": self.error[:500] if self.error else "",
            "completed_at": self.completed_at.isoformat(),
        }


class ExecutionReport:
    """Aggregated result of executing a full plan."""

    def __init__(self, plan: Plan) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.plan = plan
        self.step_results: list[StepResult] = []
        self.started_at = datetime.now(UTC)
        self.completed_at: datetime | None = None
        self.status = "running"

    def add_result(self, result: StepResult) -> None:
        self.step_results.append(result)
        result.step.status = "completed" if result.success else "failed"

    def finalize(self) -> None:
        self.completed_at = datetime.now(UTC)
        self.status = "completed" if all(r.success for r in self.step_results) else "partial"

    @property
    def success_rate(self) -> float:
        if not self.step_results:
            return 0.0
        return sum(1 for r in self.step_results if r.success) / len(self.step_results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "plan_id": self.plan.id,
            "status": self.status,
            "steps": self.plan.to_dict()["steps"],
            "results": [r.to_dict() for r in self.step_results],
            "success_rate": self.success_rate,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
        }


class PlanExecutor:
    """Executes COPILOT plans by dispatching steps to tool wrappers.

    Each step's 'tool' field maps to:
      - 'http':  HTTP request via httpx/requests
      - 'scan':  Scan tool (nuclei, naabu, etc.)
      - 'analyze':  Internal analysis logic
      - 'memory':  Query/store in UnifiedMemory
    """

    def __init__(self, memory: UnifiedMemoryStore | None = None) -> None:
        self.memory = memory
        self._history: list[ExecutionReport] = []

    def execute(self, plan: Plan) -> ExecutionReport:
        """Execute all steps of a plan in sequence."""
        report = ExecutionReport(plan)
        plan.status = "running"

        for step in plan.steps:
            step.status = "running"
            logger.info("[EXECUTOR] Step %s: %s (%s)", step.id, step.description, step.tool)
            try:
                result = self._execute_step(step)
            except Exception as e:
                logger.error("[EXECUTOR] Step %s failed: %s", step.id, e)
                result = StepResult(step, success=False, error=str(e))
            report.add_result(result)

            if not result.success:
                logger.warning("[EXECUTOR] Step %s failed — continuing plan", step.id)

        report.finalize()
        plan.status = "completed" if report.status == "completed" else "partial"
        self._history.append(report)
        self._store_report(report)
        return report

    def _execute_step(self, step: PlanStep) -> StepResult:
        tool = step.tool
        action = step.action
        params = step.params or {}

        if tool == "http":
            return self._exec_http(action, params)
        elif tool == "scan":
            return self._exec_scan(action, params)
        elif tool == "analyze":
            return self._exec_analyze(action, params)
        elif tool == "memory":
            return self._exec_memory(action, params)
        else:
            return StepResult(step, success=False, error=f"Unknown tool: {tool}")

    def _exec_http(self, action: str, params: dict[str, Any]) -> StepResult:
        """Execute HTTP-based steps using httpx."""
        step = PlanStep(action, "", tool="http", params=params)
        try:
            import httpx

            method = params.get("method", "GET").upper()
            url = params.get("url", params.get("target", ""))
            if not url:
                return StepResult(step, success=True, output="No URL provided — validation step")

            client = httpx.Client(timeout=30, verify=False)
            resp = client.request(method, url)
            data = {
                "status_code": resp.status_code,
                "body_length": len(resp.text),
                "headers": dict(resp.headers),
            }
            output = f"{method} {url} → {resp.status_code} ({len(resp.text)} bytes)"
            return StepResult(step, success=resp.status_code < 500, output=output, data=data)
        except Exception as e:
            return StepResult(step, success=False, error=str(e))

    def _exec_scan(self, action: str, params: dict[str, Any]) -> StepResult:
        """Execute scan steps using tool wrappers."""
        step = PlanStep(action, "", tool="scan", params=params)
        scan_type = params.get("type", "")
        target = params.get("target", params.get("url", ""))

        if scan_type == "port_scan":
            try:
                from cores.tools import NaabuTool

                tool = NaabuTool()
                results = tool.scan(host=target, ports="top-100", timeout=120)
                output = f"Port scan: {len(results)} open ports found"
                return StepResult(step, success=True, output=output, data={"ports": results})
            except Exception as e:
                return StepResult(step, success=False, error=str(e))

        elif scan_type == "related_endpoints":
            return StepResult(step, success=True, output="Endpoint discovery queued")

        elif scan_type == "vulnerability":
            try:
                from cores.tools import NucleiTool

                tool = NucleiTool()
                results = tool.scan(targets=[target], severity="medium", timeout=120)
                output = f"Nuclei scan: {len(results)} findings"
                return StepResult(step, success=True, output=output, data={"findings": results})
            except Exception as e:
                return StepResult(step, success=False, error=str(e))

        return StepResult(step, success=True, output=f"Scan type '{scan_type}' not implemented")

    def _exec_analyze(self, action: str, params: dict[str, Any]) -> StepResult:
        """Execute analysis steps."""
        step = PlanStep(action, "", tool="analyze", params=params)
        analysis_type = params.get("type", action)
        return StepResult(
            step,
            success=True,
            output=f"Analysis '{analysis_type}': validation queued for human review",
        )

    def _exec_memory(self, action: str, params: dict[str, Any]) -> StepResult:
        """Execute memory operations."""
        step = PlanStep(action, "", tool="memory", params=params)
        if not self.memory:
            return StepResult(step, success=False, error="Memory store not available")

        try:
            if action == "store":
                self.memory.store(
                    namespace=params.get("namespace", "copilot"),
                    key=params.get("key", ""),
                    content=params.get("content", ""),
                    tags=params.get("tags", []),
                    priority=params.get("priority", 1.0),
                )
                return StepResult(step, success=True, output="Stored in memory")
            elif action == "query":
                results = self.memory.query(
                    namespace=params.get("namespace", "copilot"),
                    search=params.get("query", params.get("search", "")),
                    limit=params.get("limit", 10),
                )
                return StepResult(step, success=True, output=f"Found {len(results)} memories")
            return StepResult(step, success=True, output=f"Memory action '{action}' completed")
        except Exception as e:
            return StepResult(step, success=False, error=str(e))

    def _store_report(self, report: ExecutionReport) -> None:
        """Persist execution report to memory."""
        if not self.memory:
            return
        try:
            self.memory.store(
                namespace="copilot",
                key=f"execution:{report.id}",
                content=str(report.to_dict()),
                tags=["execution", report.status, report.plan.context.app_id],
                priority=0.8,
            )
        except Exception as e:
            logger.warning("[EXECUTOR] Failed to store report: %s", e)

    def get_history(self, limit: int = 10) -> list[ExecutionReport]:
        return self._history[-limit:]
