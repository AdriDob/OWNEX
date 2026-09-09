"""Enhanced 24/7 Scheduler with Circuit Breakers, Backoff, and Health Monitoring.

Enhanced Core Scheduler with:
- Circuit breaker pattern for failing jobs
- Exponential backoff for retries
- Job prioritization
- Health monitoring and alerting
- Graceful degradation
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from cores.interfaces import IScheduler
from cores.interfaces.scheduler import JobDefinition

logger = logging.getLogger("orion.cores.scheduler.v2")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass(frozen=True, slots=True)
class CircuitBreaker:
    """Circuit breaker for a single job."""

    job_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_success_time: float = 0
    next_attempt: float = 0
    threshold: int = 5  # failures before opening
    timeout: float = 60  # seconds before half-open
    success_threshold: int = 2  # successes to close

    def record_success(self) -> CircuitBreaker:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            new_success = self.success_count + 1
            if new_success >= self.success_threshold:
                return CircuitBreaker(
                    job_id=self.job_id,
                    state=CircuitState.CLOSED,
                    failure_count=0,
                    success_count=new_success,
                    last_failure_time=self.last_failure_time,
                    last_success_time=time.time(),
                    next_attempt=0,
                    threshold=self.threshold,
                    timeout=self.timeout,
                    success_threshold=self.success_threshold,
                )
        return CircuitBreaker(
            job_id=self.job_id,
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count + 1,
            last_failure_time=self.last_failure_time,
            last_success_time=time.time(),
            next_attempt=self.next_attempt,
            threshold=self.threshold,
            timeout=self.timeout,
            success_threshold=self.success_threshold,
        )

    def record_failure(self) -> CircuitBreaker:
        """Record a failed call."""
        new_failures = self.failure_count + 1
        new_state = self.state
        if new_failures >= self.threshold and self.state == CircuitState.CLOSED:
            new_state = CircuitState.OPEN
        return CircuitBreaker(
            job_id=self.job_id,
            state=new_state,
            failure_count=new_failures,
            success_count=0,
            last_failure_time=time.time(),
            last_success_time=self.last_success_time,
            next_attempt=time.time() + self.timeout if new_state == CircuitState.OPEN else 0,
            threshold=self.threshold,
            timeout=self.timeout,
            success_threshold=self.success_threshold,
        )

    def can_execute(self) -> bool:
        """Check if job can be executed."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            return time.time() >= self.next_attempt
        # HALF_OPEN - allow one test call
        return True


@dataclass(frozen=True, slots=True)
class BackoffPolicy:
    """Exponential backoff configuration."""

    base_delay: float = 1.0  # seconds
    max_delay: float = 300.0  # 5 minutes
    multiplier: float = 2.0
    jitter: bool = True
    max_retries: int = 3

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed)."""
        import random

        delay = min(self.base_delay * (self.multiplier**attempt), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random()  # 0.5-1.5x jitter
        return delay


@dataclass(frozen=True, slots=True)
class JobHealth:
    """Health status for a job."""

    job_id: str
    is_healthy: bool
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_run: float = 0
    last_success: float = 0
    last_failure: float = 0
    error_message: str = ""
    circuit_breaker: CircuitBreaker | None = None
    total_runs: int = 0
    total_failures: int = 0


class CircuitBreakerRegistry:
    """Manages circuit breakers for all jobs."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, job_id: str) -> CircuitBreaker:
        if job_id not in self._breakers:
            self._breakers[job_id] = CircuitBreaker(job_id=job_id)
        return self._breakers[job_id]

    def record_success(self, job_id: str) -> CircuitBreaker:
        breaker = self.get(job_id)
        new_breaker = breaker.record_success()
        self._breakers[job_id] = new_breaker
        return new_breaker

    def record_failure(self, job_id: str) -> CircuitBreaker:
        breaker = self.get(job_id)
        new_breaker = breaker.record_failure()
        self._breakers[job_id] = new_breaker
        return new_breaker

    def can_execute(self, job_id: str) -> bool:
        return self.get(job_id).can_execute()

    def get_health(self, job_id: str) -> JobHealth:
        breaker = self.get(job_id)
        return JobHealth(
            job_id=job_id,
            is_healthy=breaker.state == CircuitState.CLOSED,
            consecutive_failures=breaker.failure_count,
            consecutive_successes=breaker.success_count,
            last_failure=breaker.last_failure_time,
            last_success=breaker.last_success_time,
            circuit_breaker=breaker,
        )

    def get_all_health(self) -> dict[str, JobHealth]:
        return {job_id: self.get_health(job_id) for job_id in self._breakers}


class BackoffManager:
    """Manages retry backoff for failed jobs."""

    def __init__(self, policy: BackoffPolicy | None = None):
        self.policy = policy or BackoffPolicy()
        self._attempts: dict[str, int] = {}

    def record_attempt(self, job_id: str) -> int:
        """Record an attempt and return current attempt number."""
        self._attempts[job_id] = self._attempts.get(job_id, 0) + 1
        return self._attempts[job_id]

    def get_delay(self, job_id: str) -> float:
        """Get delay before next retry."""
        attempt = self._attempts.get(job_id, 0)
        return self.policy.get_delay(attempt)

    def reset(self, job_id: str):
        """Reset attempt counter on success."""
        if job_id in self._attempts:
            del self._attempts[job_id]

    def get_next_retry_time(self, job_id: str) -> float:
        """Get absolute timestamp for next retry."""
        delay = self.get_delay(job_id)
        return time.time() + delay


class EnhancedScheduler(IScheduler):
    """
    Enhanced 24/7 Scheduler with circuit breakers, backoff, and health monitoring.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobDefinition] = {}
        self._task: asyncio.Task | None = None
        self._running = False
        self._on_job_due: Callable[[JobDefinition], Any] | None = None
        self._active_runs: set[str] = set()

        # Health & resilience
        self.circuit_breakers = CircuitBreakerRegistry()
        self.backoff_manager = BackoffManager()
        self._job_health: dict[str, JobHealth] = {}
        self._last_run: dict[str, float] = {}
        self._next_retry: dict[str, float] = {}

        # Metrics
        self._total_jobs_run = 0
        self._total_failures = 0
        self._start_time = time.time()

        # Persistence
        from cores.scheduler.runs import SchedulerRunLedger

        self._ledger = SchedulerRunLedger()

    def set_job_handler(self, handler: Callable[[JobDefinition], Any]) -> None:
        self._on_job_due = handler

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Enhanced scheduler started (%d jobs)", len(self._jobs))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(Exception):
                await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        logger.info("Enhanced scheduler stopped")

    def add_job(self, job: JobDefinition) -> str:
        if job.job_id in self._jobs:
            logger.warning("Job %s already registered — replacing", job.job_id)
        self._jobs[job.job_id] = job
        logger.info("Registered job %s for app %s", job.job_id, job.app_id)
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
            self.backoff_manager.reset(job_id)
            return True
        return False

    def _job_next_run(self, job: JobDefinition, last_run: float, now: float) -> float:
        if job.trigger == "cron":
            cron_expr = job.kwargs.get("cron") or ""
            if not cron_expr:
                return now + (job.seconds or 3600)
            try:
                from croniter import croniter

                base = datetime.fromtimestamp(last_run or now)
                return croniter(cron_expr, base).get_next(float)
            except Exception:
                logger.warning("Invalid cron %r for %s — falling back to hourly", cron_expr, job.job_id)
                return now + 3600
        seconds = job.seconds or 3600
        return last_run + seconds

    def _should_run_job(self, job_id: str, job: JobDefinition, now: float) -> bool:
        """Check if job should run considering circuit breaker and backoff."""
        # Check paused
        if job.kwargs.get("paused"):
            return False

        # Check circuit breaker
        if not self.circuit_breakers.can_execute(job_id):
            return False

        # Check backoff
        next_retry = self._next_retry.get(job_id, 0)
        if now < next_retry:
            return False

        # Check cron/interval timing
        last = self._last_run.get(job_id, 0)
        if last == 0:
            return True  # First run
        next_run = self._job_next_run(job, self._last_run[job_id], now)
        return now >= next_run

    async def _fire_job(self, job_id: str, job: JobDefinition) -> None:
        """Execute job with full resilience patterns."""
        from cores.scheduler.runs import RunRecord, _get_default_ledger_path, job_lock

        if job_id in self._active_runs:
            logger.debug("Job %s already running — skip overlap", job_id)
            return

        self._active_runs.add(job_id)

        # Record attempt
        attempt = self.backoff_manager.record_attempt(job_id)
        next_retry = self.backoff_manager.get_next_retry_time(job_id)
        self._next_retry[job_id] = next_retry

        try:
            lock_dir = _get_default_ledger_path().parent / "scheduler_locks"
            with job_lock(job_id, lock_dir) as acquired:
                record = RunRecord(job_id=job_id, attempt=attempt)
                if not acquired:
                    logger.info("Job %s locked by another process — skipped", job_id)
                    record.status = "skipped_locked"
                    self._ledger.append(record)
                    return

                self._ledger.append(record)  # running

                handler = self._on_job_due
                if handler is None:
                    return

                try:
                    result = handler(job)
                    if asyncio.iscoroutine(result):
                        await result

                    # Success
                    self.circuit_breakers.record_success(job_id)
                    self.backoff_manager.reset(job_id)
                    self._last_run[job_id] = time.time()

                    record.status = "success"
                    record.finished_at = time.time()
                    self._ledger.append(record)
                    logger.info("Job %s completed successfully (attempt %d)", job_id, attempt)

                except Exception as exc:
                    # Failure
                    self.circuit_breakers.record_failure(job_id)
                    record.status = "failed"
                    record.finished_at = time.time()
                    record.error = str(exc)[:500]
                    self._ledger.append(record)
                    logger.exception("Job %s failed (attempt %d): %s", job_id, attempt, exc)

                    # Schedule retry with backoff
                    delay = self.backoff_manager.get_delay(job_id)
                    self._next_retry[job_id] = time.time() + delay

        finally:
            self._active_runs.discard(job_id)

    async def _loop(self) -> None:
        """Main scheduler loop with health monitoring."""
        while self._running:
            now = time.time()

            # Check each job
            for job_id, job in list(self._jobs.items()):
                if self._should_run_job(job_id, job, now):
                    self._last_run[job_id] = now
                    asyncio.ensure_future(self._fire_job(job_id, job))

            # Health check every 30 seconds
            if int(now) % 30 == 0:
                self._health_check()

            await asyncio.sleep(5)

    def _health_check(self) -> None:
        """Periodic health check - log unhealthy jobs."""
        for job_id in self._jobs:
            health = self.circuit_breakers.get_health(job_id)
            if not health.is_healthy:
                logger.warning(
                    "Job %s unhealthy: state=%s, failures=%d, last_error=%s",
                    job_id,
                    health.circuit_breaker.state if health.circuit_breaker else "unknown",
                    health.consecutive_failures,
                    health.error_message,
                )

    def get_health_report(self) -> dict[str, Any]:
        """Get comprehensive health report."""
        return {
            "running": self._running,
            "uptime_seconds": time.time() - self._start_time,
            "total_jobs": len(self._jobs),
            "jobs_by_app": {app_id: len(self.get_jobs(app_id)) for app_id in {j.app_id for j in self._jobs.values()}},
            "circuit_breakers": {job_id: cb.state.value for job_id, cb in self.circuit_breakers._breakers.items()},
            "backoff_status": {
                job_id: self.backoff_manager.get_delay(job_id)
                for job_id in self._jobs
                if job_id in self.backoff_manager._attempts
            },
            "active_runs": list(self._active_runs),
            "total_runs": self._total_jobs_run,
            "total_failures": self._total_failures,
        }

    def get_job_health(self, job_id: str) -> dict[str, Any] | None:
        if job_id not in self._jobs:
            return None
        health = self.circuit_breakers.get_health(job_id)
        return {
            "job_id": health.job_id,
            "is_healthy": health.is_healthy,
            "consecutive_failures": health.consecutive_failures,
            "consecutive_successes": health.consecutive_successes,
            "last_run": health.last_run,
            "last_success": health.last_success,
            "last_failure": health.last_failure,
            "error_message": health.error_message,
            "circuit_breaker_state": health.circuit_breaker.state.value if health.circuit_breaker else "unknown",
            "total_runs": health.total_runs,
            "total_failures": health.total_failures,
        }

    async def trigger_job_manual(self, job_id: str) -> dict[str, Any]:
        """Manually trigger a job (bypasses scheduling)."""
        job = self._jobs.get(job_id)
        if not job:
            return {"success": False, "error": "Job not found"}

        if job_id in self._active_runs:
            return {"success": False, "error": "Job already running"}

        try:
            await self._fire_job(job_id, self._jobs[job_id])
            return {"success": True, "message": "Job triggered manually"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}


# Backward compatibility
CoreScheduler = EnhancedScheduler

# Singleton
_scheduler: EnhancedScheduler | None = None


def get_scheduler() -> EnhancedScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = EnhancedScheduler()
    return _scheduler
