"""Execution Engine — bridges ExecutionQueue state machine with real executors.

Polls queue, executes via platform executors, handles transitions + retries.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from cores.execution_queue import ExecState, ExecutionQueueStore
from cores.opportunity.executors import BaseExecutor, ExecutionResult, get_executors

logger = logging.getLogger("ownex.execution_engine")


@dataclass
class ExecutionJob:
    """A job to execute: queue item + executor mapping."""

    item_id: str
    platform: str
    action: str
    payload: dict[str, Any]
    max_retries: int = 3
    retry_count: int = 0


class ExecutionEngine:
    """Main execution loop: polls queue, routes to executors, manages state."""

    def __init__(
        self,
        queue: ExecutionQueueStore | None = None,
        executors: dict[str, BaseExecutor] | None = None,
        poll_interval_seconds: int = 30,
        max_concurrent: int = 3,
    ) -> None:
        self.queue = queue or ExecutionQueueStore()
        self.executors = executors or get_executors()
        self.poll_interval = poll_interval_seconds
        self.max_concurrent = max_concurrent
        self._running = False
        self._tasks: set[asyncio.Task] = set()
        self._semaphore: asyncio.Semaphore | None = None

    async def start(self) -> None:
        """Start the execution loop."""
        if self._running:
            return
        self._running = True
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        asyncio.create_task(self._run_loop())
        logger.info("ExecutionEngine started (poll=%ss, max_concurrent=%s)", self.poll_interval, self.max_concurrent)

    async def stop(self) -> None:
        """Stop the execution loop gracefully."""
        self._running = False
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("ExecutionEngine stopped")

    async def _run_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._process_pending()
            except Exception as exc:
                logger.error("Execution loop error: %s", exc)
            await asyncio.sleep(self.poll_interval)

    async def _process_pending(self) -> None:
        """Process all QUEUED items up to concurrency limit."""
        queued_ids = self.queue.pending_by_state(ExecState.QUEUED.value)
        if not queued_ids:
            return

        logger.debug("Found %s queued items", len(queued_ids))

        for item_id in queued_ids[: self.max_concurrent]:
            if not self._running:
                break
            await self._execute_item(item_id)

    async def _execute_item(self, item_id: str) -> None:
        """Execute a single queue item via its platform executor."""
        item = self.queue.get(item_id)
        if not item:
            return

        platform = item["payload"].get("platform")
        action = item["payload"].get("action", "execute")
        payload = item.get("payload", {})

        if not platform:
            logger.warning("Item %s has no platform, transitioning to FAILED", item_id)
            self.queue.transition(item_id, ExecState.FAILED)
            return

        executor = self.executors.get(platform)
        if not executor:
            logger.warning("No executor for platform %s, transitioning to BLOCKED", platform)
            self.queue.transition(item_id, ExecState.BLOCKED)
            return

        if not executor.is_enabled():
            logger.info("Executor %s disabled, re-queuing", platform)
            return

        semaphore = self._semaphore or asyncio.Semaphore(self.max_concurrent)
        async with semaphore:
            try:
                # Transition to EXECUTING
                self.queue.transition(item_id, ExecState.EXECUTING)
                logger.info("Executing %s on %s (action=%s)", item_id, platform, action)

                # Execute via platform executor
                result: ExecutionResult = await executor.execute(action, **payload)

                if result.success:
                    # Human gate required (e.g., approval before submit)
                    if result.data and result.data.get("requires_human_approval"):
                        self.queue.transition(item_id, ExecState.WAITING_HUMAN)
                        logger.info("Item %s requires human approval", item_id)
                    else:
                        self.queue.transition(item_id, ExecState.SUBMITTED)
                        logger.info("Item %s submitted successfully", item_id)
                else:
                    # Handle failure with retry logic
                    await self._handle_failure(item_id, result.error or "Unknown error", item)

            except Exception as exc:
                logger.error("Execution failed for %s: %s", item_id, exc)
                await self._handle_failure(item_id, str(exc), item)

    async def _handle_failure(self, item_id: str, error: str, item: dict) -> None:
        """Handle execution failure with retry/backoff."""
        retry_count = item.get("retry_count", 0) + 1
        max_retries = item.get("payload", {}).get("max_retries", 3)

        item["retry_count"] = retry_count
        item["last_error"] = error

        if retry_count >= max_retries:
            self.queue.transition(item_id, ExecState.FAILED)
            logger.error("Item %s failed after %s retries: %s", item_id, retry_count, error)
        else:
            # Re-queue with backoff
            self.queue.transition(item_id, ExecState.QUEUED)
            backoff = min(2**retry_count * 60, 3600)  # 2min, 4min, 8min... max 1h
            logger.warning("Item %s retry %s/%s in %ss: %s", item_id, retry_count, max_retries, backoff, error)
            await asyncio.sleep(backoff)

    def submit_job(self, item_id: str, platform: str, action: str, payload: dict[str, Any] | None = None) -> dict:
        """Add a new job to the queue."""
        job_payload = {"platform": platform, "action": action, **(payload or {})}
        return self.queue.add(item_id, job_payload)

    def approve_human_step(self, item_id: str) -> dict:
        """Approve a WAITING_HUMAN item to move to SUBMITTED."""
        item = self.queue.get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        if ExecState(item["state"]) != ExecState.WAITING_HUMAN:
            raise ValueError(f"Item {item_id} not in WAITING_HUMAN state")
        return self.queue.transition(item_id, ExecState.SUBMITTED)

    def reject_human_step(self, item_id: str, reason: str = "rejected") -> dict:
        """Reject a WAITING_HUMAN item."""
        item = self.queue.get(item_id)
        if not item:
            raise ValueError(f"Item {item_id} not found")
        if ExecState(item["state"]) != ExecState.WAITING_HUMAN:
            raise ValueError(f"Item {item_id} not in WAITING_HUMAN state")
        item["reject_reason"] = reason
        return self.queue.transition(item_id, ExecState.REJECTED)

    def get_stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        states = [s.value for s in ExecState]
        counts = {s: len(self.queue.pending_by_state(s)) for s in states}
        return {
            "total_items": len(self.queue._items),
            "by_state": counts,
            "running": self._running,
            "executors": list(self.executors.keys()),
        }


# Convenience function to get singleton engine
_engine: ExecutionEngine | None = None


def get_execution_engine() -> ExecutionEngine:
    global _engine
    if _engine is None:
        _engine = ExecutionEngine()
    return _engine
