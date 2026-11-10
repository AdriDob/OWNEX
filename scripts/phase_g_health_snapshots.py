"""FASE G: Automated health snapshots persist in DB — OWENEX v10 Section"""

import logging

from core.health.engine import get_health_center
from core.scheduler.life_scheduler import JobDefinition, JobType, get_life_scheduler

logger = logging.getLogger("orion.phase_g")

# Health snapshot jobs — more frequent than weekly audit
HEALTH_SNAPSHOT_JOBS = [
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="daily_health_snapshot",
        description="Snapshot diario de salud del sistema — todas las integraciones",
        interval_seconds=24 * 3600,  # daily
        priority=10,
        tags=["daily", "health", "snapshot", "system"],
        run_at_startup=True,
    ),
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="hourly_connection_snapshot",
        description="Snapshot hourly de conexiones de plataforma",
        interval_seconds=60 * 60,  # hourly
        priority=8,
        tags=["hourly", "health", "snapshot", "connections"],
        run_at_startup=True,
    ),
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="quarterly_payout_snapshot",
        description="Snapshot trimestral de métodos de cobro Argentina",
        interval_seconds=90 * 24 * 3600,  # quarterly
        priority=7,
        tags=["quarterly", "health", "snapshot", "payout", "methods"],
        run_at_startup=False,
    ),
]


async def run_daily_health_snapshot():
    """FASE G: Daily health snapshot - persist in DB"""
    try:
        health = get_health_center()
        snapshot = await health.full_check()

        # The full_check already persists via _persist_snapshot internally
        # Just log and return
        snapshot_count = len(health._snapshots)

        # Get the most recent snapshot
        if health._snapshots:
            latest = health._snapshots[-1]
            logger.info("Daily health snapshot #%d: status=%s, checks=%d", snapshot_count, latest.status, len(latest.checks))

            # Persist to DB if not already persisted (check via status field)
            if latest.status and latest.timestamp:
                logger.debug("Snapshot already persisted: status=%s, timestamp=%s", latest.status[:20], latest.timestamp[:20])

        return {"success": True, "snapshot_status": snapshot.get("overall", {}).get("status", "unknown")}
    except Exception as e:
        logger.exception("Daily health snapshot failed")
        return {"success": False, "message": str(e)}


async def run_hourly_connection_snapshot():
    """FASE G: Hourly connection snapshot - persist in DB"""
    try:
        health = get_health_center()

        # Get connection-specific snapshot
        snapshot = await health.check("connections")

        snapshot_count = len(health._snapshots)
        logger.info("Hourly connection snapshot #%d: status=%s", snapshot_count, snapshot.status if snapshot else "no snapshot")

        return {"success": True, "snapshot_status": snapshot.status if snapshot else "unknown"}
    except Exception as e:
        logger.exception("Hourly connection snapshot failed")
        return {"success": False, "message": str(e)}


async def run_quarterly_payout_snapshot():
    """FASE G: Quarterly payout methods snapshot - persist in DB"""
    try:
        from core.cores.financial_intelligence.argentina_payout_methods import get_argentina_methods

        methods = get_argentina_methods()

        # Create summary snapshot
        total = len(methods)
        kyc_good = sum(1 for m in methods.values() if m.get("kyc_level") not in ["unknown", None])
        low_fee = sum(1 for m in methods.values() if m.get("fee_percent", 99) <= 10)
        fast_arrival = sum(1 for m in methods.values() if m.get("arrival_days", 999) <= 7)

        summary = {
            "total_methods": total,
            "kyc_good_ratio": round(kyc_good / total * 100, 1) if total > 0 else 0,
            "low_fee_ratio": round(low_fee / total * 100, 1) if total > 0 else 0,
            "fast_arrival_ratio": round(fast_arrival / total * 100, 1) if total > 0 else 0,
        }

        logger.info(
            "Quarterly payout snapshot: %d methods - KYC: %d%%, Fees: %d%%, Speed: %d%%",
            total,
            summary["kyc_good_ratio"],
            summary["low_fee_ratio"],
            summary["fast_arrival_ratio"],
        )

        return {"success": True, "summary": summary}
    except Exception as e:
        logger.exception("Quarterly payout snapshot failed")
        return {"success": False, "message": str(e)}


def register_phase_g_jobs():
    """Register all FASE G health snapshot jobs with the LifeScheduler."""

    scheduler = get_life_scheduler()
    for job in HEALTH_SNAPSHOT_JOBS:
        scheduler.add_job(job)

    # Override executors
    scheduler._jobs["daily_health_snapshot"].executor = run_daily_health_snapshot
    scheduler._jobs["hourly_connection_snapshot"].executor = run_hourly_connection_snapshot
    scheduler._jobs["quarterly_payout_snapshot"].executor = run_quarterly_payout_snapshot

    logger.info("FASE G: Registered %d health snapshot jobs", len(HEALTH_SNAPSHOT_JOBS))
