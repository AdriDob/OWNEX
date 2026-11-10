"""FASE H: Argentina sources expansion & monthly revenue optimization — OWENEX v10"""

import asyncio
import logging
from datetime import datetime

from core.health.engine import get_health_center
from core.scheduler.life_scheduler import JobDefinition, JobType, get_life_scheduler

logger = logging.getLogger("orion.phase_h")

# Phase H jobs - source expansion and revenue optimization
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


async def run_monthly_source_expansion():
    """FASE H: Expandir fuentes Argentina - nuevos proveedores y elegibilidad"""
    try:
        from core.discovery.source_discovery import discover_sources
        from core.source_registry import get_source_registry

        registry = get_source_registry()

        # Discover new Argentina-eligible sources
        new_sources = await discover_sources(filters={"region": "Argentina", "min_reward": 50})

        # Check current registered sources
        current = registry.get_all_sources() if hasattr(registry, "get_all_sources") else []
        argentina_current = [s for s in current if s.get("region") == "Argentina"]

        # Identify expansion opportunities
        expansion_opportunities = []
        for source in new_sources:
            source_name = source.get("name", "unknown")
            # Check if already registered
            already_registered = any(s.get("name") == source_name for s in argentina_current)
            if not already_registered:
                expansion_opportunities.append(
                    {
                        "name": source_name,
                        "domain": source.get("domain"),
                        "min_reward": source.get("min_reward"),
                        "category": source.get("category"),
                        " eligibility_score": source.get("eligibility_score", 0),
                    }
                )

        # Log expansion summary
        health = get_health_center()
        await health.full_check()
        current_count = len(argentina_current)

        logger.info("Monthly source expansion: %d new opportunities, %d current Argentina sources", len(expansion_opportunities), current_count)

        # Persist expansion data
        from core.health.engine import HealthSnapshot

        expansion_snapshot = HealthSnapshot(
            status="green" if expansion_opportunities else "yellow",
            checks={
                "monthly_source_expansion": {
                    "new_opportunities": len(expansion_opportunities),
                    "current_sources": current_count,
                    "expansion_list": expansion_opportunities[:5],  # top 5
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


async def run_revenue_optimization():
    """FASE H: Optimización mensual de ingreso neto esperado"""
    try:
        from core.revenue.intelligence import get_revenue_intelligence

        ri = get_revenue_intelligence()

        # Get current intelligence
        potential = await ri.get_potential()
        expected = await ri.get_expected()
        approved = await ri.get_approved()
        paid = await ri.get_paid()

        # Calculate optimization opportunities
        total_potential = sum(p.get("estimated_reward", 0) for p in potential.values())
        total_expected = sum(e.get("estimated_reward", 0) for e in expected.values())
        total_approved = sum(a.get("estimated_reward", 0) for a in approved.values())
        total_paid = sum(pa.get("estimated_reward", 0) for pa in paid.values())

        # Optimization: identify gap between potential and paid
        gap_potential_paid = total_potential - total_paid
        gap_expected_approved = total_expected - total_approved

        # Priority ranking: sources that move from potential → approved → paid
        optimization_actions = []

        # Sources in potential but not approved
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

        # Sources approved but not paid
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

        logger.info(
            "Revenue optimization summary: potential=$%d, expected=$%d, approved=$%d, paid=$%d", total_potential, total_expected, total_approved, total_paid
        )
        logger.info("Gap potential→paid:=$%d, gap expected→approved:=$%d", gap_potential_paid, gap_expected_approved)
        logger.info("Optimization actions needed: %d", len(optimization_actions))

        # Persist revenue snapshot
        from core.health.engine import HealthSnapshot

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


async def run_argentina_quality_update():
    """FASE H: Actualizar calidad de fuentes Argentina - validación de condiciones"""
    try:
        from core.cores.financial_intelligence.argentina_payout_methods import get_argentina_methods, refresh_methods

        # Refresh the methods database
        await asyncio.get_event_loop().run_in_executor(None, refresh_methods)

        methods = get_argentina_methods()

        # Quality metrics
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
            "Argentina quality update: %d methods - KYC: %d%%, Fees: %d%%, Time: %d%%",
            total,
            quality_ratio["valid_kyc_ratio"],
            quality_ratio["reasonable_fees_ratio"],
            quality_ratio["acceptable_time_ratio"],
        )

        # Persist quality snapshot
        from core.health.engine import HealthSnapshot

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


def register_phase_h_jobs():
    """Register all FASE H expansion & optimization jobs with the LifeScheduler."""

    scheduler = get_life_scheduler()
    for job in PHASE_H_JOBS:
        scheduler.add_job(job)

    # Override executors
    scheduler._jobs["monthly_source_expansion"].executor = run_monthly_source_expansion
    scheduler._jobs["revenue_optimization"].executor = run_revenue_optimization
    scheduler._jobs["argentina_quality_update"].executor = run_argentina_quality_update

    logger.info("FASE H: Registered %d expansion & optimization jobs", len(PHASE_H_JOBS))
