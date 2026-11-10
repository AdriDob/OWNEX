"""FASE F: Weekly audit job — OWENEX v10 Section"""

import logging
from datetime import datetime

from core.health.engine import HealthSnapshot, get_health_center
from core.scheduler.life_scheduler import JobDefinition, JobType, get_life_scheduler

logger = logging.getLogger("orion.phase_f")

# Weekly audit job definitions
WEEKLY_AUDIT_JOBS = [
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="weekly_source_audit",
        description="Auditoría semanal de fuentes de trabajo Argentina - calidad y elegibilidad",
        interval_seconds=7 * 24 * 3600,  # weekly
        priority=10,
        tags=["weekly", "audit", "sources", "argentina"],
        run_at_startup=True,
    ),
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="weekly_connections_audit",
        description="Auditoría semanal de conexiones de plataforma - estados y salud",
        interval_seconds=7 * 24 * 3600,  # weekly
        priority=9,
        tags=["weekly", "audit", "connections", "platforms"],
        run_at_startup=True,
    ),
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="weekly_payout_methods_audit",
        description="Auditoría semanal de métodos de cobro Argentina - KYC, fees, arrival_days",
        interval_seconds=7 * 24 * 3600,  # weekly
        priority=8,
        tags=["weekly", "audit", "payout", "methods", "argentina"],
        run_at_startup=True,
    ),
]


async def run_weekly_source_audit():
    """FASE F: Audit work sources - quality and Argentina eligibility"""
    try:
        health = get_health_center()
        snapshot = await health.full_check()

        # Check Argentina sources specifically
        sources = snapshot.get("sources", {})
        argentina_sources = {k: v for k, v in sources.items() if v.get("region") == "Argentina" or v.get("country") == "AR"}

        # Quality checks
        quality_issues = []
        for name, info in argentina_sources.items():
            if not info.get("active"):
                quality_issues.append(f"{name}: source inactive")
            if not info.get("last_checked"):
                quality_issues.append(f"{name}: never checked")
            if info.get("last_checked"):
                from datetime import datetime, timedelta

                last = datetime.fromisoformat(info["last_checked"])
                if datetime.utcnow() - last > timedelta(days=7):
                    quality_issues.append(f"{name}: not checked in 7+ days")

        # Persist audit results
        from core.health.engine import HealthSnapshot

        audit_snapshot = HealthSnapshot(
            status="green" if not quality_issues else "yellow",
            checks={
                "weekly_source_audit": {
                    "argentina_sources": len(argentina_sources),
                    "quality_issues": len(quality_issues),
                    "issues_detail": quality_issues,
                }
            },
            timestamp=datetime.utcnow().isoformat(),
        )

        health._persist_snapshot(audit_snapshot)
        logger.info("Weekly source audit completed: %d Argentina sources, %d quality issues", len(argentina_sources), len(quality_issues))

        return {"success": True, "argentina_sources": len(argentina_sources), "quality_issues": len(quality_issues)}
    except Exception as e:
        logger.exception("Weekly source audit failed")
        return {"success": False, "message": str(e)}


async def run_weekly_connections_audit():
    """FASE F: Audit platform connections - states and health"""
    try:
        health = get_health_center()
        snapshot = await health.full_check()

        connections = snapshot.get("connections", {})

        # Count connections by state
        state_counts = {}
        for state in ["CONNECTED", "NOT_CONNECTED", "CONNECTING", "EXPIRED", "ERROR", "REVOKED", "MANUAL_SETUP", "UNSUPPORTED"]:
            state_counts[state] = len(connections.get(state, []))

        # Check for stale connections (EXPIRED + old)
        stale_issues = []
        for state, items in connections.items():
            if state in ["EXPIRED", "ERROR"] and state_counts.get(state, 0) > 0:
                stale_issues.append(f"{state}: {len(items)} connections")

        audit_snapshot = HealthSnapshot(
            status="green" if not stale_issues else "yellow",
            checks={
                "weekly_connections_audit": {
                    "state_counts": state_counts,
                    "stale_issues": len(stale_issues),
                    "issues_detail": stale_issues,
                }
            },
            timestamp=datetime.utcnow().isoformat(),
        )

        health._persist_snapshot(audit_snapshot)
        logger.info(
            "Weekly connections audit completed: %d connections across %d states, %d stale issues",
            sum(state_counts.values()),
            len(state_counts),
            len(stale_issues),
        )

        return {"success": True, "state_counts": state_counts, "stale_issues": len(stale_issues)}
    except Exception as e:
        logger.exception("Weekly connections audit failed")
        return {"success": False, "message": str(e)}


async def run_weekly_payout_methods_audit():
    """FASE F: Audit Argentina payout methods - KYC, fees, arrival_days"""
    try:
        from core.cores.financial_intelligence.argentina_payout_methods import get_argentina_methods

        methods = get_argentina_methods()

        # Quality checks on methods
        kyc_issues = []
        fee_issues = []
        timing_issues = []

        for method_id, method_info in methods.items():
            # KYC level checks
            kyc = method_info.get("kyc_level", "unknown")
            if kyc == "unknown":
                kyc_issues.append(f"{method_id}: kyc_level unknown")

            # Fee checks
            fee_percent = method_info.get("fee_percent", 0)
            if fee_percent > 10:
                fee_issues.append(f"{method_id}: fee {fee_percent}% > 10%")

            # Arrival days checks
            arrival_days = method_info.get("arrival_days", 999)
            if arrival_days > 14:
                timing_issues.append(f"{method_id}: arrival_days {arrival_days} > 14 days")

        audit_snapshot = HealthSnapshot(
            status="green" if not (kyc_issues or fee_issues or timing_issues) else "yellow",
            checks={
                "weekly_payout_methods_audit": {
                    "total_methods": len(methods),
                    "kyc_issues": len(kyc_issues),
                    "fee_issues": len(fee_issues),
                    "timing_issues": len(timing_issues),
                    "issues_detail": kyc_issues + fee_issues + timing_issues,
                }
            },
            timestamp=datetime.utcnow().isoformat(),
        )

        from core.health.engine import get_health_center

        h = get_health_center()
        h._persist_snapshot(audit_snapshot)
        logger.info("Weekly payout methods audit completed: %d methods, %d issues", len(methods), len(kyc_issues) + len(fee_issues) + len(timing_issues))

        return {"success": True, "total_methods": len(methods), "total_issues": len(kyc_issues) + len(fee_issues) + len(timing_issues)}
    except Exception as e:
        logger.exception("Weekly payout methods audit failed")
        return {"success": False, "message": str(e)}


def register_phase_f_jobs():
    """Register all FASE F weekly audit jobs with the LifeScheduler."""

    scheduler = get_life_scheduler()
    for job in WEEKLY_AUDIT_JOBS:
        scheduler.add_job(job)

    # Override executors
    scheduler._jobs["weekly_source_audit"].executor = run_weekly_source_audit
    scheduler._jobs["weekly_connections_audit"].executor = run_weekly_connections_audit
    scheduler._jobs["weekly_payout_methods_audit"].executor = run_weekly_payout_methods_audit

    logger.info("FASE F: Registered %d weekly audit jobs", len(WEEKLY_AUDIT_JOBS))
