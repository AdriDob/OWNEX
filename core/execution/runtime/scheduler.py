from __future__ import annotations

import heapq
import logging
from dataclasses import dataclass, field

from core.execution.runtime.kernel import ExecutionKernel
from core.execution.runtime.state_machine import WorkflowState

logger = logging.getLogger("ownex.execution.scheduler")


@dataclass(order=True)
class _ReadyTask:
    priority: int
    execution_id: str = field(compare=False)
    workflow_name: str = field(compare=False)


class Scheduler:
    """Decides what to execute next. Never executes.

    Pipeline:
      READY → Priority Queue → Dependency Resolver
             → Resource Checker → Worker Assignment
    """

    def __init__(self, kernel: ExecutionKernel) -> None:
        self.kernel = kernel
        self._queue: list[_ReadyTask] = []
        self._pending: dict[str, _ReadyTask] = {}
        self._routing: dict[str, str] = {}

    def enqueue(
        self,
        execution_id: str,
        workflow_name: str = "",
        priority: int = 0,
    ) -> None:
        task = _ReadyTask(priority=priority, execution_id=execution_id, workflow_name=workflow_name)
        heapq.heappush(self._queue, task)
        self._pending[execution_id] = task
        logger.info("[Scheduler] Enqueued %s (priority=%d)", execution_id, priority)

    def dequeue(self) -> str | None:
        while self._queue:
            task = heapq.heappop(self._queue)
            ctx = self.kernel.get_context(task.execution_id)
            wf_state = self.kernel.get_workflow_state(task.execution_id)
            if wf_state == WorkflowState.EXECUTING and ctx:
                self._pending.pop(task.execution_id, None)
                return task.execution_id
        return None

    def peek(self) -> str | None:
        if self._queue:
            return self._queue[0].execution_id
        return None

    def cancel(self, execution_id: str) -> bool:
        task = self._pending.pop(execution_id, None)
        if task:
            self._queue = [t for t in self._queue if t.execution_id != execution_id]
            heapq.heapify(self._queue)
            return True
        return False

    def assign_worker(self, execution_id: str, worker_id: str) -> None:
        self._routing[execution_id] = worker_id

    def get_assigned_worker(self, execution_id: str) -> str | None:
        return self._routing.get(execution_id)

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        self._queue.clear()
        self._pending.clear()
        self._routing.clear()
