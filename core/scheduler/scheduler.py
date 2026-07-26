"""Core Scheduler — delegates job execution to apps via EventBus.

The scheduler only manages timing. When a job is due, it publishes
a ``scheduler:job_due`` event that the target app handles.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

from core.interfaces import IScheduler
from core.interfaces.scheduler import JobDefinition

logger = logging.getLogger("orion.core.scheduler")


class CoreScheduler(IScheduler):
    """Central scheduler that publishes events — apps execute their own jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobDefinition] = {}
        self._task: asyncio.Task | None = None
        self._running = False
        self._on_job_due: Callable[[JobDefinition], Any] | None = None

    def set_job_handler(self, handler: Callable[[JobDefinition], Any]) -> None:
        """Set the callback invoked when a job is due (usually EventBus publish)."""
        self._on_job_due = handler

    # ── Lifecycle ────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Core scheduler started (%d jobs)", len(self._jobs))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Core scheduler stopped")

    # ── Job management ───────────────────────────────────────────

    def add_job(self, job: JobDefinition) -> str:
        if job.job_id in self._jobs:
            logger.warning("Job %s already registered — replacing", job.job_id)
        self._jobs[job.job_id] = job
        logger.info("Registered job %s for app %s (interval=%ds)", job.job_id, job.app_id, job.seconds)
        return job.job_id

    def remove_job(self, job_id: str) -> bool:
        return self._jobs.pop(job_id, None) is not None

    def get_jobs(self, app_id: str | None = None) -> list[JobDefinition]:
        if app_id:
            return [j for j in self._jobs.values() if j.app_id == app_id]
        return list(self._jobs.values())

    def pause_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job:
            job.kwargs["paused"] = True
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job:
            job.kwargs.pop("paused", None)
            return True
        return False

    # ── Internal loop ────────────────────────────────────────────

    async def _loop(self) -> None:
        last_run: dict[str, float] = {}

        while self._running:
            now = time.time()
            for job_id, job in list(self._jobs.items()):
                if job.kwargs.get("paused"):
                    continue
                last = last_run.get(job_id, 0)
                if now - last >= job.seconds:
                    last_run[job_id] = now
                    handler = self._on_job_due
                    if handler is not None:
                        try:
                            result = handler(job)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception:
                            logger.exception("Job %s handler failed", job_id)
            await asyncio.sleep(5)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def job_count(self) -> int:
        return len(self._jobs)

    def status(self) -> dict:
        return {
            "running": self._running,
            "jobs": self.job_count,
            "by_app": {app_id: len(self.get_jobs(app_id)) for app_id in {j.app_id for j in self._jobs.values()}},
        }


# ── Singleton ────────────────────────────────────────

_scheduler: CoreScheduler | None = None


def get_core_scheduler() -> CoreScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = CoreScheduler()
    return _scheduler
