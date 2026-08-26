"""Core Scheduler — delegates job execution to apps via EventBus.

The scheduler only manages timing. When a job is due, it publishes
a ``scheduler:job_due`` event that the target app handles.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from datetime import datetime
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
        # Hardening spec §12: guard anti-solapamiento + run ledger persistente.
        self._active_runs: set[str] = set()
        from core.scheduler.runs import SchedulerRunLedger

        self._ledger = SchedulerRunLedger()

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
            # Awaitar la cancelación: sin esto el loop puede seguir vivo
            # durante la teardown del event loop (audit P1-1).
            with contextlib.suppress(Exception):
                await asyncio.gather(self._task, return_exceptions=True)
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

    def _job_next_run(self, job: JobDefinition, last_run: float, now: float) -> float:
        """Return the next time a job should run (epoch seconds).

        Cron jobs use the ``cron`` expression from their kwargs; interval
        jobs use ``job.seconds``.
        """
        if job.trigger == "cron":
            cron_expr = job.kwargs.get("cron") or ""
            if not cron_expr:
                return now + job.seconds if job.seconds > 0 else now + 3600
            try:
                from croniter import croniter

                base = datetime.fromtimestamp(last_run or now)
                return croniter(cron_expr, base).get_next(float)
            except Exception:
                logger.warning("Invalid cron %r for %s — falling back to hourly", cron_expr, job.job_id)
                return now + 3600
        seconds = job.seconds or 3600
        return last_run + seconds

    async def _fire_job(self, job_id: str, job: JobDefinition) -> None:
        """Ejecuta un job con guard anti-solapamiento + run ledger (spec §12).

        - Si el mismo job ya está corriendo en este proceso → skip.
        - Si otro proceso sostiene el flock del job → skipped_locked (registrado).
        - Toda corrida queda en el JSONL con job_id/run_id/attempt/status/error.
        """
        from core.scheduler.runs import RunRecord, _default_ledger_path, job_lock

        if job_id in self._active_runs:
            logger.debug("Job %s aún corriendo — skip overlap", job_id)
            return
        self._active_runs.add(job_id)
        try:
            lock_dir = _default_ledger_path().parent / "scheduler_locks"
            with job_lock(job_id, lock_dir) as acquired:
                record = RunRecord(job_id=job_id)
                if not acquired:
                    logger.info("Job %s locked por otro proceso — skipped", job_id)
                    record.status = "skipped_locked"
                    self._ledger.append(record)
                    return
                record.attempt = self._ledger.next_attempt(job_id)
                self._ledger.append(record)  # running
                handler = self._on_job_due
                if handler is None:
                    return
                try:
                    result = handler(job)
                    if asyncio.iscoroutine(result):
                        await result
                    if record is not None:
                        record.status = "success"
                        record.finished_at = time.time()
                        self._ledger.append(record)
                except Exception as exc:
                    logger.exception("Job %s failed (attempt %d)", job_id, record.attempt)
                    record.status = "failed"
                    record.finished_at = time.time()
                    record.error = str(exc)[:500]
                    self._ledger.append(record)
        finally:
            self._active_runs.discard(job_id)

    async def _loop(self) -> None:
        last_run: dict[str, float] = {}

        while self._running:
            now = time.time()
            for job_id, job in list(self._jobs.items()):
                if job.kwargs.get("paused"):
                    continue
                last = last_run.get(job_id, 0)
                if last == 0:
                    last_run[job_id] = now
                    continue
                next_run = self._job_next_run(job, last, now)
                if now >= next_run:
                    last_run[job_id] = now
                    # Fire-and-collect: un job lento ya no bloquea el loop
                    # entero (audit P1-1); el guard evita solapamiento.
                    asyncio.ensure_future(self._fire_job(job_id, job))
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
