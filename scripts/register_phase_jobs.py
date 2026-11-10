"""Register all FASES F, G, H jobs directly with the LifeScheduler."""

import asyncio
import logging
from datetime import datetime

from core.scheduler.life_scheduler import JobDefinition, JobType, get_life_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orion.register_phases")


# ── FASE F: Weekly Audit Jobs ──────────────────────────────────────────
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


# ── FASE G: Health Snapshot Jobs ───────────────────────────────────────
HEALTH_SNAPSHOT_JOBS = [
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="daily_health_snapshot",
        description="Snapshot diario de salud del sistema - todas las integraciones",
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


# ── FASE H: Expansion & Optimization Jobs ──────────────────────────────
PHASE_H_JOBS = [
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="monthly_source_expansion",
        description="Expansion mensual de fuentes Argentina - nuevos proveedores y elegibilidad",
        interval_seconds=30 * 24 * 3600,  # monthly (~30 days)
        priority=10,
        tags=["monthly", "expansion", "sources", "argentina", "revenue"],
        run_at_startup=True,
    ),
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="revenue_optimization",
        description="Optimización mensual de ingreso neto esperado - ranking y priorización",
        interval_seconds=30 * 24 * 3600,  # monthly (~30 days)
        priority=9,
        tags=["monthly", "optimization", "revenue", "net", "ranking"],
        run_at_startup=True,
    ),
    JobDefinition(
        job_type=JobType.HEALTH_SNAPSHOT,
        name="argentina_quality_update",
        description="Actualización de calidad de fuentes Argentina - validación de condiciones",
        interval_seconds=30 * 24 * 3600,  # monthly (~30 days)
        priority=8,
        tags=["monthly", "quality", "update", "argentina", "sources"],
        run_at_startup=False,
    ),
]


# Executor functions for each job type
async def run_weekly_source_audit(scheduler) -> dict:
    """FASE F: Audit work sources quality and Argentina eligibility."""
    try:
        from core.health.engine import HealthSnapshot, get_health_center

        health = get_health_center()
        snapshot = await health.full_check()

        sources = snapshot.get("sources", {})
        argentina_sources = {k: v for k, v in sources.items() if v.get("region") == "Argentina" or v.get("country") == "AR"}

        quality_issues = []
        for name, info in argentina_sources.items():
            if not info.get("active"):
                quality_issues.append(f"{name}: source inactive")
            if not info.get("last_checked"):
                quality_issues.append(f"{name}: never checked")
            from datetime import datetime, timedelta

            if info.get("last_checked"):
                last = datetime.fromisoformat(info["last_checked"])
                if datetime.utcnow() - last > timedelta(days=7):
                    quality_issues.append(f"{name}: not checked in 7+ days")

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

        logger.info("Weekly source audit: %d Argentina sources, %d issues", len(argentina_sources), len(quality_issues))
        return {"success": True, "argentina_sources": len(argentina_sources), "quality_issues": len(quality_issues)}
    except Exception as e:
        logger.exception("Weekly source audit failed")
        return {"success": False, "message": str(e)}


async def run_weekly_connections_audit(scheduler) -> dict:
    """FASE F: Audit platform connections states and health."""
    try:
        from core.health.engine import HealthSnapshot, get_health_center

        health = get_health_center()
        snapshot = await health.full_check()

        connections = snapshot.get("connections", {})

        state_counts = {}
        for state in ["CONNECTED", "NOT_CONNECTED", "CONNECTING", "EXPIRED", "ERROR", "REVOKED", "MANUAL_SETUP", "UNSUPPORTED"]:
            state_counts[state] = len(connections.get(state, []))

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
            "Weekly connections audit: %d connections across %d states, %d stale issues", sum(state_counts.values()), len(state_counts), len(stale_issues)
        )
        return {"success": True, "state_counts": state_counts, "stale_issues": len(stale_issues)}
    except Exception as e:
        logger.exception("Weekly connections audit failed")
        return {"success": False, "message": str(e)}


async def run_weekly_payout_methods_audit(scheduler) -> dict:
    """FASE F: Audit Argentina payout methods KYC, fees, arrival_days."""
    try:
        from core.cores.financial_intelligence.argentina_payout_methods import get_argentina_methods

        from core.health.engine import HealthSnapshot, get_health_center

        methods = get_argentina_methods()

        kyc_issues = []
        fee_issues = []
        timing_issues = []

        for method_id, method_info in methods.items():
            kyc = method_info.get("kyc_level", "unknown")
            if kyc == "unknown":
                kyc_issues.append(f"{method_id}: kyc_level unknown")

            fee_percent = method_info.get("fee_percent", 0)
            if fee_percent > 10:
                fee_issues.append(f"{method_id}: fee {fee_percent}% > 10%")

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

        h = get_health_center()
        h._persist_snapshot(audit_snapshot)
        logger.info("Weekly payout methods audit: %d methods, %d total issues", len(methods), len(kyc_issues) + len(fee_issues) + len(timing_issues))
        return {"success": True, "total_methods": len(methods), "total_issues": len(kyc_issues) + len(fee_issues) + len(timing_issues)}
    except Exception as e:
        logger.exception("Weekly payout methods audit failed")
        return {"success": False, "message": str(e)}


async def run_daily_health_snapshot(scheduler) -> dict:
    """FASE G: Daily health snapshot persist in DB."""
    try:
        from core.health.engine import get_health_center

        health = get_health_center()
        snapshot = await health.full_check()

        snapshot_count = len(health._snapshots)
        if health._snapshots:
            latest = health._snapshots[-1]
            logger.info("Daily health snapshot #%d: status=%s", snapshot_count, latest.status)

        return {"success": True, "snapshot_status": snapshot.get("overall", {}).get("status", "unknown")}
    except Exception as e:
        logger.exception("Daily health snapshot failed")
        return {"success": False, "message": str(e)}


async def run_hourly_connection_snapshot(scheduler) -> dict:
    """FASE G: Hourly connection snapshot persist in DB."""
    try:
        from core.health.engine import get_health_center

        health = get_health_center()
        snapshot = await health.check("connections")

        snapshot_count = len(health._snapshots)
        logger.info("Hourly connection snapshot #%d: status=%s", snapshot_count, snapshot.status if snapshot else "no snapshot")

        return {"success": True, "snapshot_status": snapshot.status if snapshot else "unknown"}
    except Exception as e:
        logger.exception("Hourly connection snapshot failed")
        return {"success": False, "message": str(e)}


async def run_quarterly_payout_snapshot(scheduler) -> dict:
    """FASE G: Quarterly payout methods snapshot."""
    try:
        from core.cores.financial_intelligence.argentina_payout_methods import get_argentina_methods

        methods = get_argentina_methods()
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
            "Quarterly payout snapshot: %d methods - KYC: %%d%%, Fees: %%d%%, Speed: %%d%%",
            total,
            summary["kyc_good_ratio"],
            summary["low_fee_ratio"],
            summary["fast_arrival_ratio"],
        )

        return {"success": True, "summary": summary}
    except Exception as e:
        logger.exception("Quarterly payout snapshot failed")
        return {"success": False, "message": str(e)}


async def run_monthly_source_expansion(scheduler) -> dict:
    """FASE H: Expandir fuentes Argentina - nuevos proveedores y elegibilidad."""
    try:
        from core.discovery.source_discovery import discover_sources
        from core.source_registry import get_source_registry

        registry = get_source_registry()
        new_sources = await discover_sources(filters={"region": "Argentina", "min_reward": 50})

        current = registry.get_all_sources() if hasattr(registry, "get_all_sources") else []
        argentina_current = [s for s in current if s.get("region") == "Argentina"]

        expansion_opportunities = []
        for source in new_sources:
            source_name = source.get("name", "unknown")
            already_registered = any(s.get("name") == source_name for s in argentina_current)
            if not already_registered:
                expansion_opportunities.append(
                    {
                        "name": source_name,
                        "domain": source.get("domain"),
                        "min_reward": source.get("min_reward"),
                        "category": source.get("category"),
                        "eligibility_score": source.get("eligibility_score", 0),
                    }
                )

        from core.health.engine import HealthSnapshot, get_health_center

        health = get_health_center()
        await health.full_check()
        current_count = len(argentina_current)

        logger.info("Monthly source expansion: %d new opportunities, %d current Argentina sources", len(expansion_opportunities), current_count)

        expansion_snapshot = HealthSnapshot(
            status="green" if expansion_opportunities else "yellow",
            checks={
                "monthly_source_expansion": {
                    "new_opportunities": len(expansion_opportunities),
                    "current_sources": current_count,
                    "expansion_list": expansion_opportunities[:5],
                }
            },
            timestamp=datetime.utcnow().isoformat(),
        )
        health._persist_snapshot(expansion_snapshot)

        return {
            "success": True,
            "new_opportunities": len(expansion_opportunities),
            "current_sources": current_count,
            "expansion_list": expansion_opportunities[:5],
        }
    except Exception as e:
        logger.exception("Monthly source expansion failed")
        return {"success": False, "message": str(e)}


async def run_revenue_optimization(scheduler) -> dict:
    """FASE H: Optimización mensual de ingreso neto esperado."""
    try:
        from core.revenue.intelligence import get_revenue_intelligence

        ri = get_revenue_intelligence()
        potential = await ri.get_potential()
        expected = await ri.get_expected()
        approved = await ri.get_approved()
        paid = await ri.get_paid()

        total_potential = sum(p.get("estimated_reward", 0) for p in potential.values())
        total_expected = sum(e.get("estimated_reward", 0) for e in expected.values())
        total_approved = sum(a.get("estimated_reward", 0) for a in approved.values())
        total_paid = sum(pa.get("estimated_reward", 0) for pa in paid.values())

        gap_potential_paid = total_potential - total_paid
        gap_expected_approved = total_expected - total_approved

        optimization_actions = []

        for source_id, source_data in potential.items():
            if source_id not in {a.get("source_id") for a in approved}:
                optimization_actions.append(
                    {
                        "action": "prioritize_approval",
                        "source": source_id,
                        "potential_reward": source_data.get("estimated_reward", 0),
                        "effort": "medium",
                    }
                )

        for source_data in approved:
            source_id = source_data.get("source_id")
            if source_id not in {p.get("source_id") for p in paid}:
                optimization_actions.append(
                    {
                        "action": "process_payment",
                        "source": source_id,
                        "approved_reward": source_data.get("estimated_reward", 0),
                        "effort": "low",
                    }
                )

        summary = {
            "total_potential": total_potential,
            "total_expected": total_expected,
            "total_approved": total_approved,
            "total_paid": total_paid,
            "gap_potential_paid": gap_potential_paid,
            "gap_expected_approved": gap_expected_approved,
            "optimization_actions": len(optimization_actions),
            "top_action": optimization_actions[0] if optimization_actions else None,
        }

        logger.info("Revenue optimization: potential=$%d, expected=$%d, approved=$%d, paid=$%d", total_potential, total_expected, total_approved, total_paid)
        logger.info("Gap potential→paid:=$%d, gap expected→approved:=$%d", gap_potential_paid, gap_expected_approved)
        logger.info("Optimization actions needed: %d", len(optimization_actions))

        from core.health.engine import HealthSnapshot, get_health_center

        revenue_snapshot = HealthSnapshot(
            status="green" if gap_potential_paid < 100 else "yellow",
            checks={"revenue_optimization": summary},
            timestamp=datetime.utcnow().isoformat(),
        )
        health = get_health_center()
        health._persist_snapshot(revenue_snapshot)

        return {"success": True, "summary": summary}
    except Exception as e:
        logger.exception("Revenue optimization failed")
        return {"success": False, "message": str(e)}


async def run_argentina_quality_update(scheduler) -> dict:
    """FASE H: Actualizar calidad de fuentes Argentina."""
    try:
        from core.cores.financial_intelligence.argentina_payout_methods import get_argentina_methods, refresh_methods

        await asyncio.get_event_loop().run_in_executor(None, refresh_methods)
        methods = get_argentina_methods()

        total = len(methods)
        valid_kyc = sum(1 for m in methods.values() if m.get("kyc_level") and m.get("kyc_level") != "unknown")
        reasonable_fees = sum(1 for m in methods.values() if m.get("fee_percent", 99) <= 15)
        acceptable_time = sum(1 for m in methods.values() if m.get("arrival_days", 999) <= 14)

        quality_ratio = {
            "total_methods": total,
            "valid_kyc_ratio": round(valid_kyc / total * 100, 1) if total > 0 else 0,
            "reasonable_fees_ratio": round(reasonable_fees / total * 100, 1) if total > 0 else 0,
            "acceptable_time_ratio": round(acceptable_time / total * 100, 1) if total > 0 else 0,
        }

        logger.info(
            "Argentina quality update: %d methods - KYC: %%d%%, Fees: %%d%%, Time: %%d%%",
            total,
            quality_ratio["valid_kyc_ratio"],
            quality_ratio["reasonable_fees_ratio"],
            quality_ratio["acceptable_time_ratio"],
        )

        from core.health.engine import HealthSnapshot, get_health_center

        quality_snapshot = HealthSnapshot(
            status="green" if all(v >= 80 for v in quality_ratio.values() if v) else "yellow",
            checks={"argentina_quality_update": quality_ratio},
            timestamp=datetime.utcnow().isoformat(),
        )
        health = get_health_center()
        health._persist_snapshot(quality_snapshot)

        return {"success": True, "quality_ratio": quality_ratio}
    except Exception as e:
        logger.exception("Argentina quality update failed")
        return {"success": False, "message": str(e)}


def register_phase_f_jobs(scheduler):
    """Register FASE F weekly audit jobs."""
    for job in WEEKLY_AUDIT_JOBS:
        scheduler.register(job)

    logger.info("FASE F: Registered %d weekly audit jobs", len(WEEKLY_AUDIT_JOBS))


def register_phase_g_jobs(scheduler):
    """Register FASE G health snapshot jobs."""
    for job in HEALTH_SNAPSHOT_JOBS:
        scheduler.register(job)

    logger.info("FASE G: Registered %d health snapshot jobs", len(HEALTH_SNAPSHOT_JOBS))


def register_phase_h_jobs(scheduler):
    """Register FASE H expansion & optimization jobs."""
    for job in PHASE_H_JOBS:
        scheduler.register(job)

    logger.info("FASE H: Registered %d expansion & optimization jobs", len(PHASE_H_JOBS))


async def main():
    scheduler = get_life_scheduler()

    register_phase_f_jobs(scheduler)
    register_phase_g_jobs(scheduler)
    register_phase_h_jobs(scheduler)

    # Verify
    status = scheduler.get_status()
    logger.info("=== Scheduler Status ===")
    logger.info("Running: %s", status.get("running", False))
    logger.info("Total jobs configured: %d", status.get("total_jobs", 0))

    logger.info("=== Phase registration complete ===")


if __name__ == "__main__":
    asyncio.run(main())
