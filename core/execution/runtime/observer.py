from __future__ import annotations

import logging
from typing import Any

from core.execution.runtime.integration import ExecutionEventBusBridge

logger = logging.getLogger("cateye.execution.observer")


class CopilotExecutionObserver:
    """COPILOT watches every execution, learns, and improves.

    Listens to execution events and:
    1. On completion — extracts metrics, stores in COPILOT memory
    2. On failure — suggests improvements
    3. Accumulates learning about capability performance
    4. Stores execution patterns in Unified Memory

    This is the bridge between execution and intelligence:
    COPILOT no longer just *responds* — it *observes, understands, decides, acts, learns*.
    """

    def __init__(self, bridge: ExecutionEventBusBridge) -> None:
        self._bridge = bridge
        self._memory: Any = None
        self._copilot: Any = None
        self._execution_history: list[dict[str, Any]] = []
        self._capability_stats: dict[str, dict[str, float]] = {}

    def _get_memory(self) -> Any:
        if self._memory is None:
            try:
                from core.memory.store import get_memory_store

                self._memory = get_memory_store()
            except ImportError:
                logger.warning("[Observer] Unified Memory not available")
                self._memory = _NullMemory()
        return self._memory

    def _get_copilot(self) -> Any:
        if self._copilot is None:
            try:
                from core.copilot.agent import CopilotAgent

                self._copilot = CopilotAgent()
            except ImportError:
                logger.warning("[Observer] COPILOT not available")
                self._copilot = _NullCopilot()
        return self._copilot

    def subscribe(self) -> None:
        self._bridge.subscribe_to_execution_events(self._handle_event)

    def _handle_event(self, event_type: str, data: dict[str, Any]) -> None:
        if event_type == "execution:workflow:started":
            self._on_execution_start(data)
        elif event_type == "execution:workflow:completed":
            self._on_execution_completed(data)
        elif event_type == "execution:workflow:failed":
            self._on_execution_failed(data)

    def _on_execution_start(self, data: dict[str, Any]) -> None:
        execution_id = data.get("execution_id")
        workflow_id = data.get("workflow_id")
        logger.info("[Observer] Execution started: %s / %s", workflow_id, execution_id)

    def _on_execution_completed(self, data: dict[str, Any]) -> None:
        execution_id = data.get("execution_id")
        result = data.get("result", {})
        workflow_id = data.get("workflow_id", result.get("workflow_id", "unknown"))

        record = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "completed",
            "result": result,
        }
        self._execution_history.append(record)

        # Store in COPILOT memory
        memory = self._get_memory()
        memory.store(
            namespace="copilot",
            key=f"execution:{execution_id}",
            content=f"Workflow {workflow_id} completed successfully",
            tags=["execution", "completed", workflow_id],
            priority=5,
        )

        copilot = self._get_copilot()
        copilot.remember_observation(
            event="execution_completed",
            workflow_id=workflow_id,
            execution_id=execution_id,
            result_summary=str(result),
        )

        self._update_capability_stats(result)
        logger.info("[Observer] Learned from execution %s", execution_id)

    def _on_execution_failed(self, data: dict[str, Any]) -> None:
        execution_id = data.get("execution_id")
        error = data.get("error", "unknown")
        workflow_id = data.get("workflow_id", "unknown")

        record = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": "failed",
            "error": error,
        }
        self._execution_history.append(record)

        memory = self._get_memory()
        memory.store(
            namespace="copilot",
            key=f"execution:{execution_id}",
            content=f"Workflow {workflow_id} failed: {error}",
            tags=["execution", "failed", workflow_id],
            priority=8,
        )

        copilot = self._get_copilot()
        copilot.remember_observation(
            event="execution_failed",
            workflow_id=workflow_id,
            execution_id=execution_id,
            error=error,
        )

        logger.info("[Observer] Recorded failure: %s — %s", execution_id, error)

    def _update_capability_stats(self, result: dict[str, Any]) -> None:
        output = result.get("output", {})
        if not output:
            return
        for key, val in output.items():
            if key not in self._capability_stats:
                self._capability_stats[key] = {"calls": 0, "failures": 0, "total_cost": 0.0}
            self._capability_stats[key]["calls"] += 1
            cost = val.get("cost_usd", 0) if isinstance(val, dict) else 0
            self._capability_stats[key]["total_cost"] += cost

    def get_execution_history(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._execution_history[-limit:]

    def get_capability_stats(self) -> dict[str, dict[str, float]]:
        return dict(self._capability_stats)


class _NullMemory:
    def store(self, **kwargs: Any) -> None:
        pass

    def query(self, **kwargs: Any) -> list:
        return []


class _NullCopilot:
    def remember_observation(self, **kwargs: Any) -> None:
        pass
