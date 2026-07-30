"""
Life Scheduler — orquestador único de todos los jobs de valor en ORION.

Extiende el patrón del ScanScheduler a dominios no-bug-bounty:
inversión, finanzas personales, trabajo, salud del sistema, aprendizaje.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.health.engine import get_health_center
from core.memory.store import get_unified_memory
from cores.events.event_bus import get_event_bus
from cores.events.types import EventType

logger = logging.getLogger("orion.life_scheduler")


class JobType(str, Enum):
    """Tipos de jobs que el Life Scheduler puede ejecutar."""

    # Bug Bounty (existentes, wrapped)
    BB_DISCOVER = "bb_discover"
    BB_RECON = "bb_recon"
    BB_HYPOTHESIS = "bb_hypothesis"
    BB_PROMOTE = "bb_promote"
    BB_VALIDATE = "bb_validate"
    BB_REPORT = "bb_report"
    BB_AI_BOUNTY = "bb_ai_bounty"

    # Financial / Investment
    INVESTMENT_PRICE_UPDATE = "investment_price_update"
    INVESTMENT_REBALANCE_CHECK = "investment_rebalance_check"
    INVESTMENT_GOAL_TRACK = "investment_goal_track"
    INVESTMENT_TAX_ESTIMATE = "investment_tax_estimate"

    # Personal Finance
    FINANCE_EXPENSE_IMPORT = "finance_expense_import"
    FINANCE_SUBSCRIPTION_CHECK = "finance_subscription_check"
    FINANCE_BUDGET_ALERT = "finance_budget_alert"
    FINANCE_INVOICE_GENERATE = "finance_invoice_generate"

    # Work / Productivity
    WORK_DAILY_BRIEFING = "work_daily_briefing"
    WORK_ACTIVITY_LOG = "work_activity_log"
    WORK_DECISION_JOURNAL = "work_decision_journal"
    WORK_PRIORITY_RECALC = "work_priority_recalc"

    # System Health
    HEALTH_FULL_CHECK = "health_full_check"
    HEALTH_SNAPSHOT = "health_snapshot"

    # Learning / Knowledge
    KNOWLEDGE_SYNC = "knowledge_sync"
    KNOWLEDGE_GRAPH_UPDATE = "knowledge_graph_update"

    # Maintenance
    MAINT_DB_CLEANUP = "maint_db_cleanup"
    MAINT_LOG_ROTATION = "maint_log_rotation"
    MAINT_WAL_CHECKPOINT = "maint_wal_checkpoint"


@dataclass
class JobDefinition:
    """Definición declarativa de un job."""

    job_type: JobType
    name: str
    description: str
    interval_seconds: int
    enabled: bool = True
    priority: int = 0  # mayor = más importante
    depends_on: list[JobType] = field(default_factory=list)
    run_at_startup: bool = False
    max_concurrent: int = 1
    timeout_seconds: int = 300
    tags: list[str] = field(default_factory=list)

    # Función ejecutora (se asigna en registro)
    executor: Callable[[], Awaitable[JobResult]] | None = None


@dataclass
class JobResult:
    """Resultado de ejecución de un job."""

    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    next_run_override: float | None = None  # para reprogramar dinámicamente
    events_published: list[dict] = field(default_factory=list)


class LifeScheduler:
    """
    Orquestador único de todos los jobs de valor.

    Principios:
    - Single process, asyncio-based
    - Priority queue con dependencias
    - EventBus para observabilidad total
    - HealthCenter para auto-protección
    - UnifiedMemory para estado persistente
    - COPILOT para decisiones adaptativas (futuro)
    """

    def __init__(self):
        self._jobs: dict[JobType, JobDefinition] = {}
        self._running: bool = False
        self._main_task: asyncio.Task | None = None
        self._job_tasks: dict[JobType, asyncio.Task] = {}
        self._last_run: dict[JobType, float] = {}
        self._job_stats: dict[JobType, dict] = {}
        self._paused_jobs: set[JobType] = set()

        # Integraciones (lazy init)
        self._event_bus = None
        self._health = None
        self._memory = None

    # ── Integraciones lazy ────────────────────────────────────────

    @property
    def _bus(self):
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus

    @property
    def _health_center(self):
        if self._health is None:
            self._health = get_health_center()
        return self._health

    @property
    def _mem(self):
        if self._memory is None:
            self._memory = get_unified_memory()
        return self._memory

    # ── Registro de jobs ──────────────────────────────────────────

    def register(self, job_def: JobDefinition) -> None:
        """Registra un job. Debe llamarse antes de start()."""
        if job_def.job_type in self._jobs:
            logger.warning("Job %s ya registrado, sobrescribiendo", job_def.job_type)
        self._jobs[job_def.job_type] = job_def
        self._job_stats[job_def.job_type] = {
            "runs": 0,
            "successes": 0,
            "failures": 0,
            "last_duration": 0.0,
            "avg_duration": 0.0,
        }
        logger.info(
            "[LifeScheduler] Registered job: %s (%s every %ds, priority=%d)",
            job_def.name,
            job_def.job_type.value,
            job_def.interval_seconds,
            job_def.priority,
        )

    def register_executor(self, job_type: JobType, executor: Callable[[], Awaitable[JobResult]]) -> None:
        """Asigna la función ejecutora a un job ya registrado."""
        if job_type not in self._jobs:
            raise ValueError(f"Job {job_type} no registrado. Llama register() primero.")
        self._jobs[job_type].executor = executor

    # ── Control ───────────────────────────────────────────────────

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        # Ejecutar jobs con run_at_startup
        for job_type, job_def in self._jobs.items():
            if job_def.run_at_startup and job_def.enabled:
                asyncio.create_task(self._run_job_once(job_type, "startup"))

        self._main_task = asyncio.create_task(self._main_loop())
        logger.info("[LifeScheduler] Started with %d jobs", len(self._jobs))

    async def stop(self) -> None:
        self._running = False
        if self._main_task:
            self._main_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._main_task
        # Cancelar jobs en ejecución
        for task in self._job_tasks.values():
            task.cancel()
        logger.info("[LifeScheduler] Stopped")

    def pause_job(self, job_type: JobType) -> None:
        self._paused_jobs.add(job_type)
        logger.info("[LifeScheduler] Paused job: %s", job_type)

    def resume_job(self, job_type: JobType) -> None:
        self._paused_jobs.discard(job_type)
        logger.info("[LifeScheduler] Resumed job: %s", job_type)

    # ── Loop principal ────────────────────────────────────────────

    async def _main_loop(self) -> None:
        while self._running:
            try:
                now = time.time()

                # Health gate: si sistema crítico falla, solo jobs esenciales
                if not await self._should_run_any_job():
                    await asyncio.sleep(60)
                    continue

                # Evaluar qué jobs deben correr
                due_jobs = self._get_due_jobs(now)

                # Resolver dependencias y priorizar
                ready_jobs = self._resolve_dependencies(due_jobs)

                # Lanzar jobs (respetando max_concurrent)
                for job_type in ready_jobs:
                    if job_type not in self._job_tasks or self._job_tasks[job_type].done():
                        self._job_tasks[job_type] = asyncio.create_task(self._run_job_once(job_type, "scheduled"))

                # Limpiar tasks completadas
                self._cleanup_completed_tasks()

                await asyncio.sleep(30)  # tick cada 30s

            except Exception as e:
                logger.exception("[LifeScheduler] Main loop error: %s", e)
                await asyncio.sleep(60)

    async def _should_run_any_job(self) -> bool:
        """Health gate: si sistema en rojo, solo jobs de health/maint."""
        try:
            snapshot = self._health_center.run_all()
            if snapshot.status == "red":
                essential_prefixes = ("health_", "maint_")
                return any(
                    job_type.value.startswith(prefix)
                    for job_type, job_def in self._jobs.items()
                    if job_def.enabled
                    for prefix in essential_prefixes
                )
        except Exception as e:
            logger.warning("[LifeScheduler] Health check failed, allowing all jobs: %s", e)
        return True

    def _get_due_jobs(self, now: float) -> list[JobType]:
        due = []
        for job_type, job_def in self._jobs.items():
            if not job_def.enabled or job_type in self._paused_jobs:
                continue
            last = self._last_run.get(job_type, 0)
            if now - last >= job_def.interval_seconds:
                due.append(job_type)
        return due

    def _resolve_dependencies(self, due_jobs: list[JobType]) -> list[JobType]:
        """Ordena jobs por prioridad y dependencias (topological-ish)."""

        def sort_key(jt: JobType):
            job = self._jobs[jt]
            deps_satisfied = all(
                self._last_run.get(dep, 0) > 0  # dependency ran at least once
                for dep in job.depends_on
            )
            return (-job.priority, 0 if deps_satisfied else 1, job.interval_seconds)

        return sorted(due_jobs, key=sort_key)

    # ── Ejecución de job individual ───────────────────────────────

    async def _run_job_once(self, job_type: JobType, trigger: str) -> None:
        job_def = self._jobs[job_type]
        if job_def.executor is None:
            logger.warning("[LifeScheduler] No executor for %s", job_type)
            return

        run_id = str(uuid.uuid4())[:8]
        start = time.time()

        logger.info("[LifeScheduler] ▶ %s [%s] (trigger=%s)", job_def.name, run_id, trigger)

        # Evento inicio
        self._bus.publish(
            EventType.JOB_STARTED.value,
            payload={
                "job_type": job_type.value,
                "job_name": job_def.name,
                "run_id": run_id,
                "trigger": trigger,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            correlation_id=run_id,
        )

        try:
            # Timeout wrapper
            result = await asyncio.wait_for(job_def.executor(), timeout=job_def.timeout_seconds)

            duration = time.time() - start
            self._last_run[job_type] = time.time()

            # Actualizar stats
            stats = self._job_stats[job_type]
            stats["runs"] += 1
            if result.success:
                stats["successes"] += 1
            else:
                stats["failures"] += 1
            stats["last_duration"] = duration
            stats["avg_duration"] = (stats["avg_duration"] * (stats["runs"] - 1) + duration) / stats["runs"]

            # Persistir en memoria
            self._mem.store(
                namespace="scheduler",
                key=f"job_stats:{job_type.value}",
                content="",
                metadata=stats,
                tags=["scheduler", "stats", job_type.value],
            )

            # Publicar eventos del resultado
            for event in result.events_published:
                self._bus.publish(
                    event["type"],
                    payload=event["payload"],
                    correlation_id=run_id,
                )

            # Reprogramar si next_run_override
            if result.next_run_override:
                self._last_run[job_type] = result.next_run_override - job_def.interval_seconds

            logger.info(
                "[LifeScheduler] %s %s [%s] %.2fs — %s",
                "✓" if result.success else "✗",
                job_def.name,
                run_id,
                duration,
                result.message,
            )

        except TimeoutError:
            logger.error("[LifeScheduler] ✗ %s [%s] TIMEOUT after %ds", job_def.name, run_id, job_def.timeout_seconds)
            self._bus.publish(
                EventType.JOB_FAILED.value,
                payload={"job_type": job_type.value, "error": "timeout", "run_id": run_id},
                correlation_id=run_id,
            )
        except Exception as e:
            logger.exception("[LifeScheduler] ✗ %s [%s] ERROR: %s", job_def.name, run_id, e)
            self._bus.publish(
                EventType.JOB_FAILED.value,
                payload={"job_type": job_type.value, "error": str(e), "run_id": run_id},
                correlation_id=run_id,
            )

    def _cleanup_completed_tasks(self) -> None:
        done = [jt for jt, task in self._job_tasks.items() if task.done()]
        for jt in done:
            self._job_tasks.pop(jt, None)

    # ── API pública ───────────────────────────────────────────────

    def get_status(self) -> dict:
        now = time.time()
        return {
            "running": self._running,
            "total_jobs": len(self._jobs),
            "enabled_jobs": sum(1 for j in self._jobs.values() if j.enabled),
            "paused_jobs": list(self._paused_jobs),
            "running_jobs": list(self._job_tasks.keys()),
            "jobs": {
                jt.value: {
                    "name": jd.name,
                    "enabled": jd.enabled,
                    "interval": jd.interval_seconds,
                    "priority": jd.priority,
                    "last_run_ago": now - self._last_run.get(jt, 0) if jt in self._last_run else None,
                    "next_run_in": max(0, jd.interval_seconds - (now - self._last_run.get(jt, 0)))
                    if jt in self._last_run
                    else 0,
                    "stats": self._job_stats.get(jt, {}),
                    "tags": jd.tags,
                    "depends_on": [d.value for d in jd.depends_on],
                }
                for jt, jd in self._jobs.items()
            },
        }

    async def trigger_job(self, job_type: JobType) -> JobResult:
        """Ejecuta un job bajo demanda (manual)."""
        if job_type not in self._jobs:
            raise ValueError(f"Unknown job: {job_type}")
        job_def = self._jobs[job_type]
        if job_def.executor is None:
            return JobResult(success=False, message="No executor registered")

        run_id = str(uuid.uuid4())[:8]
        logger.info("[LifeScheduler] Manual trigger: %s [%s]", job_def.name, run_id)
        return await job_def.executor()


# ── Singleton global ──────────────────────────────────────────────

_life_scheduler: LifeScheduler | None = None


def get_life_scheduler() -> LifeScheduler:
    global _life_scheduler
    if _life_scheduler is None:
        _life_scheduler = LifeScheduler()
    return _life_scheduler
