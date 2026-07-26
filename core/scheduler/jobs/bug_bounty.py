"""
Bug Bounty Jobs — wrapper del ScanScheduler existente como jobs del LifeScheduler.

Reutiliza la lógica probada de api/scheduler.py expuesta como jobs individuales.
"""

from __future__ import annotations

import logging

from core.scheduler.life_scheduler import JobDefinition, JobResult, JobType, get_life_scheduler

logger = logging.getLogger("orion.scheduler.jobs.bug_bounty")

# Referencia al ScanScheduler existente (se inyecta en register_bb_jobs)
_scan_scheduler = None


def set_scan_scheduler(scheduler) -> None:
    """Inyecta la instancia del ScanScheduler (para testing y boot)."""
    global _scan_scheduler
    _scan_scheduler = scheduler


def get_scan_scheduler():
    return _scan_scheduler


async def _run_bb_stage(stage_method: str) -> JobResult:
    """Ejecuta un stage del ScanScheduler por nombre."""
    if _scan_scheduler is None:
        return JobResult(False, "ScanScheduler not initialized")

    if not hasattr(_scan_scheduler, stage_method):
        return JobResult(False, f"Stage {stage_method} not found")

    try:
        method = getattr(_scan_scheduler, stage_method)
        await method()
        return JobResult(True, f"{stage_method} completed")
    except Exception as e:
        logger.exception("BB stage %s failed", stage_method)
        return JobResult(False, f"{stage_method} failed: {e}")


# ── Executors individuales ────────────────────────────────────────

async def bb_discover() -> JobResult:
    return await _run_bb_stage("_stage_discover")


async def bb_recon() -> JobResult:
    return await _run_bb_stage("_stage_recon")


async def bb_hypothesis() -> JobResult:
    return await _run_bb_stage("_stage_hypothesis")


async def bb_promote() -> JobResult:
    return await _run_bb_stage("_stage_promote")


async def bb_validate() -> JobResult:
    return await _run_bb_stage("_stage_validate")


async def bb_report() -> JobResult:
    return await _run_bb_stage("_stage_report")


async def bb_ai_bounty() -> JobResult:
    return await _run_bb_stage("_stage_ai_bounty")


# ── Registro ──────────────────────────────────────────────────────

def register_bb_jobs(scan_scheduler=None) -> None:
    """
    Registra los stages del pipeline BB como jobs individuales en LifeScheduler.

    Args:
        scan_scheduler: Instancia de ScanScheduler (opcional, se puede inyectar después con set_scan_scheduler)
    """
    if scan_scheduler:
        set_scan_scheduler(scan_scheduler)

    scheduler = get_life_scheduler()

    # DISCOVER - cada 1h, prioridad alta (fuente de todo)
    scheduler.register(JobDefinition(
        job_type=JobType.BB_DISCOVER,
        name="Bug Bounty: Discover Programs",
        description="Scrape public platforms for new programs",
        interval_seconds=3600,  # 1h
        priority=100,
        run_at_startup=True,
        tags=["bugbounty", "discover", "revenue", "source"],
        executor=bb_discover,
    ))

    # RECON - cada 30min, depende de discover
    scheduler.register(JobDefinition(
        job_type=JobType.BB_RECON,
        name="Bug Bounty: Recon Scan",
        description="Run recon on prioritized targets",
        interval_seconds=1800,  # 30min
        priority=90,
        depends_on=[JobType.BB_DISCOVER],
        tags=["bugbounty", "recon", "revenue", "active"],
        executor=bb_recon,
    ))

    # HYPOTHESIS - cada 15min, depende de recon
    scheduler.register(JobDefinition(
        job_type=JobType.BB_HYPOTHESIS,
        name="Bug Bounty: Generate Hypotheses",
        description="Generate vulnerability hypotheses from recon data",
        interval_seconds=900,  # 15min
        priority=85,
        depends_on=[JobType.BB_RECON],
        tags=["bugbounty", "hypothesis", "intelligence"],
        executor=bb_hypothesis,
    ))

    # PROMOTE - cada 10min, depende de hypothesis
    scheduler.register(JobDefinition(
        job_type=JobType.BB_PROMOTE,
        name="Bug Bounty: Promote Hypotheses",
        description="Test hypotheses against real endpoints (probe)",
        interval_seconds=600,  # 10min
        priority=80,
        depends_on=[JobType.BB_HYPOTHESIS],
        tags=["bugbounty", "promote", "validation", "active"],
        executor=bb_promote,
    ))

    # VALIDATE - cada 2h, depende de promote
    scheduler.register(JobDefinition(
        job_type=JobType.BB_VALIDATE,
        name="Bug Bounty: Validate Findings",
        description="Run controlled validation on promoted findings",
        interval_seconds=7200,  # 2h
        priority=75,
        depends_on=[JobType.BB_PROMOTE],
        timeout_seconds=600,  # 10min timeout para validación
        tags=["bugbounty", "validate", "evidence", "critical"],
        executor=bb_validate,
    ))

    # REPORT - cada 1h, depende de validate
    scheduler.register(JobDefinition(
        job_type=JobType.BB_REPORT,
        name="Bug Bounty: Generate Reports",
        description="Generate reports for confirmed findings",
        interval_seconds=3600,  # 1h
        priority=70,
        depends_on=[JobType.BB_VALIDATE],
        tags=["bugbounty", "report", "delivery", "revenue"],
        executor=bb_report,
    ))

    # AI BOUNTY - cada 2h, independiente
    scheduler.register(JobDefinition(
        job_type=JobType.BB_AI_BOUNTY,
        name="Bug Bounty: AI Bounty Programs",
        description="Check AI bounty programs for opportunities",
        interval_seconds=7200,  # 2h
        priority=60,
        tags=["bugbounty", "ai", "specialized"],
        executor=bb_ai_bounty,
    ))

    logger.info("[BB Jobs] Registered 7 bug bounty jobs in LifeScheduler")
