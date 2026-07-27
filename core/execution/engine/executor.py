"""Execution Engine v1 — Core execution runtime for OWNEX Work Cycles.

Converts NextBestAction recommendations into executed tasks with full lifecycle:
prepare → execute → verify → report
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ownex.execution.engine")


class TaskPhase(str):
    """Phases of task execution."""

    PREPARE = "prepare"
    EXECUTE = "execute"
    VERIFY = "verify"
    REPORT = "report"


class TaskStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskDefinition:
    """Definition of a task to be executed."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    cycle: str = "security"
    action_type: str = "generic"  # scan, analyze, report, submit, etc.
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "cycle": self.cycle,
            "action_type": self.action_type,
            "payload": self.payload,
            "priority": self.priority,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class TaskExecution:
    """Runtime state of a task execution."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str = ""
    status: str = TaskStatus.PENDING
    phase: str = TaskPhase.PREPARE
    progress: float = 0.0  # 0.0 to 1.0
    current_step: str = ""
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    retry_count: int = 0
    logs: list[str] = field(default_factory=list)

    def add_log(self, message: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.logs.append(f"[{timestamp}] {message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status,
            "phase": self.phase,
            "progress": self.progress,
            "current_step": self.current_step,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
            "logs": self.logs,
        }


class TaskExecutor:
    """Executes a single task through its phases: prepare → execute → verify → report."""

    def __init__(self, timeout_seconds: int = 300):
        self._timeout = timeout_seconds
        self._handlers: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {}

    def register_handler(self, action_type: str, handler: Callable[..., Awaitable[dict[str, Any]]]) -> None:
        """Register a handler for a specific action type."""
        self._handlers[action_type] = handler

    async def execute(self, task: TaskDefinition) -> dict[str, Any]:
        """Execute a task through all phases."""
        execution = TaskExecution(
            id=uuid.uuid4().hex[:12],
            task_id=task.id,
            status=TaskStatus.RUNNING,
            phase=TaskPhase.PREPARE,
            started_at=datetime.now(timezone.utc),
        )

        start_time = time.time()
        output = {}
        error = None

        try:
            # Phase 1: PREPARE
            execution.phase = TaskPhase.PREPARE
            execution.current_step = "preparing"
            execution.progress = 0.1
            await self._log_step(execution, "Preparing task execution")

            # Validate and prepare context
            await self._prepare_context(task)
            await self._log_step(execution, "Context prepared")

            # Phase 2: EXECUTE
            execution.phase = TaskPhase.EXECUTE
            execution.progress = 0.4
            execution.current_step = "executing"
            await self._log_step(execution, "Executing action")

            # Dispatch to registered handler
            handler = self._handlers.get(task.action_type)
            if not handler:
                raise ValueError(f"No handler registered for action type: {task.action_type}")

            result = await asyncio.wait_for(
                handler(task.payload, task.cycle),
                timeout=task.timeout_seconds,
            )
            output = result or {}
            await self._log_step(execution, "Action completed")

            # Phase 3: VERIFY
            execution.phase = TaskPhase.VERIFY
            execution.progress = 0.7
            execution.current_step = "verifying"
            await self._log_step(execution, "Verifying results")

            verification = await self._verify_result(task, output)
            if not verification.get("success", True):
                raise ValueError(f"Verification failed: {verification.get('error', 'Unknown')}")

            await self._log_step(execution, "Verification passed")

            # Phase 4: REPORT
            execution.phase = TaskPhase.REPORT
            execution.progress = 0.9
            execution.current_step = "reporting"
            await self._log_step(execution, "Generating report")

            report = await self._generate_report(task, output, verification)
            output["report"] = report

            await self._log_step(execution, "Report generated")

            # Complete
            execution.status = TaskStatus.COMPLETED
            execution.phase = TaskPhase.REPORT
            execution.progress = 1.0
            execution.current_step = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_ms = (time.time() - start_time) * 1000
            execution.output = output

            return {
                "success": True,
                "execution": execution.to_dict(),
                "output": output,
                "report": report,
            }

        except asyncio.TimeoutError:
            error = f"Task timed out after {task.timeout_seconds}s"
            execution.error = error
            execution.status = TaskStatus.FAILED
            await self._log_step(execution, error)
            return {"success": False, "error": error, "execution": execution.to_dict()}

        except Exception as e:
            error = f"Execution failed: {str(e)}"
            execution.error = error
            execution.status = TaskStatus.FAILED
            await self._log_step(execution, error)

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await self._log_step(execution, f"Retrying (attempt {task.retry_count}/{task.max_retries})")
                await asyncio.sleep(2**task.retry_count)  # Exponential backoff
                return await self.execute(task)

            return {"success": False, "error": error, "execution": execution.to_dict()}

    async def _prepare_context(self, task: TaskDefinition) -> dict[str, Any]:
        """Prepare execution context from task payload and cycle context."""
        return {
            "cycle": task.cycle,
            "action_type": task.action_type,
            "payload": task.payload,
            "metadata": task.metadata,
        }

    async def _verify_result(self, task: TaskDefinition, output: dict) -> dict:
        """Verify execution output. Override for custom verification."""
        return {"success": True}

    async def _generate_report(self, task: TaskDefinition, output: dict, verification: dict) -> dict:
        """Generate execution report."""
        return {
            "task_id": task.id,
            "title": task.title,
            "cycle": task.cycle,
            "action_type": task.action_type,
            "success": True,
            "output_summary": str(output)[:500],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _log_step(self, execution: TaskExecution, message: str) -> None:
        execution.add_log(message)
        logger.info(f"[{execution.id}] {message}")

    def get_handler(self, action_type: str) -> Callable[..., Awaitable[dict[str, Any]]] | None:
        return self._handlers.get(action_type)


class ExecutionEngine:
    """Main execution engine that manages task queue and dispatches to executors."""

    def __init__(self):
        self._executor = TaskExecutor()
        self._running: dict[str, TaskExecution] = {}
        self._task_queue: asyncio.Queue[TaskDefinition] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._running_flag = False

    def register_handler(self, action_type: str, handler: Callable[..., Awaitable[dict[str, Any]]]) -> None:
        """Register a handler for a specific action type."""
        self._executor.register_handler(action_type, handler)

    async def start(self) -> None:
        """Start the execution engine worker."""
        if self._running_flag:
            return
        self._running_flag = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("ExecutionEngine started")

    async def stop(self) -> None:
        """Stop the execution engine."""
        self._running_flag = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
        logger.info("ExecutionEngine stopped")

    async def submit_task(self, task: TaskDefinition) -> str:
        """Submit a task for execution. Returns execution ID."""
        await self._task_queue.put(task)
        logger.info(f"Task submitted: {task.title} ({task.id})")
        return task.id

    async def execute_now(self, task: TaskDefinition) -> dict[str, Any]:
        """Execute a task immediately (bypass queue)."""
        return await self._executor.execute(task)

    async def get_execution_status(self, execution_id: str) -> dict[str, Any] | None:
        """Get status of a running execution."""
        execution = self._running.get(execution_id)
        return execution.to_dict() if execution else None

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        execution = self._running.get(execution_id)
        if execution and execution.status == TaskStatus.RUNNING:
            execution.status = TaskStatus.CANCELLED
            return True
        return False

    async def _worker_loop(self) -> None:
        """Background worker that processes the task queue."""
        while self._running_flag:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                await self._executor.execute(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    def get_running_count(self) -> int:
        return len(self._running)

    def get_queue_size(self) -> int:
        return self._task_queue.qsize()


def create_execution_engine() -> ExecutionEngine:
    """Factory function to create ExecutionEngine with default handlers."""
    engine = ExecutionEngine()

    # Register default handlers
    # from core.execution.engine.security_handlers import register_security_handlers
    # register_security_handlers(engine)

    return engine


def create_task_from_next_action(next_action: dict[str, Any]) -> TaskDefinition:
    """Create a TaskDefinition from a NextBestAction dict."""
    import uuid

    return TaskDefinition(
        id=uuid.uuid4().hex[:12],
        title=next_action.get("title", "Execute Action"),
        description=next_action.get("reason", ""),
        cycle=next_action.get("cycle", "security"),
        action_type="next_action",
        payload={
            "reason": next_action.get("reason", ""),
            "original_action": next_action,
        },
        priority=100,
        timeout_seconds=300,
    )


async def execute_next_action(next_action: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to execute a NextBestAction immediately."""
    engine = create_execution_engine()
    await engine.start()
    try:
        task = create_task_from_next_action(next_action)
        return await engine.execute_now(task)
    finally:
        await engine.stop()
