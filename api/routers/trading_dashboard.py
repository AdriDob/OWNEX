"""Trading Dashboard — Monitors the state of 25 autonomous trading jobs."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.scheduler.jobs import get_trading_jobs

router = APIRouter(prefix="/api/trading", tags=["trading_dashboard"])


@router.get("/dashboard/status", summary="Estado de los 25 jobs de trading automático")
def trading_dashboard_status() -> JSONResponse:
    """Return the status of all 25 autonomous trading jobs as JSON."""

    jobs = get_trading_jobs()

    result = {
        "total_jobs": len(jobs),
        "jobs": [],
        "summary": {
            "by_type": {},
            "by_cycle": {},
            "enabled": 0,
            "disabled": 0,
        },
    }

    for job in jobs:
        md = job.metadata or {}
        # enabled is not a direct attribute of JobDefinition;
        # it's set when registered with LifeScheduler. Default to True.
        job_enabled = job.metadata.get("enabled", True) if md else True

        job_info = {
            "job_id": job.job_id,
            "handler": job.handler,
            "app_id": job.app_id,
            "trigger": job.trigger,
            "seconds": job.seconds,
            "metadata": md,
            "enabled": job_enabled,
        }
        result["jobs"].append(job_info)

        # Summary counts
        jtype = md.get("type", "unknown")
        jcycle = md.get("cycle", "unknown")
        result["summary"]["by_type"][jtype] = result["summary"]["by_type"].get(jtype, 0) + 1
        result["summary"]["by_cycle"][jcycle] = result["summary"]["by_cycle"].get(jcycle, 0) + 1
        if job_enabled:
            result["summary"]["enabled"] += 1
        else:
            result["summary"]["disabled"] += 1

    # Sort jobs by job_id for consistent ordering
    result["jobs"].sort(key=lambda j: j["job_id"])

    return JSONResponse(content=result)


@router.get("/dashboard/summary", summary="Resumen ejecutivo de jobs de trading")
def trading_dashboard_summary() -> JSONResponse:
    """Executive summary of trading job status as JSON."""

    jobs = get_trading_jobs()

    # Count by type and cycle
    by_type = {}
    by_cycle = {}
    enabled = 0
    disabled = 0

    for job in jobs:
        md = job.metadata or {}
        jtype = md.get("type", "unknown")
        jcycle = md.get("cycle", "unknown")

        by_type[jtype] = by_type.get(jtype, 0) + 1
        by_cycle[jcycle] = by_cycle.get(jcycle, 0) + 1
        # enabled defaults to True if not set
        if md.get("enabled", True) if md else True:
            enabled += 1
        else:
            disabled += 1

    # Categorize by functionality
    categories = {
        "risk_safety": ["trading_risk_check"],
        "backtest_pipeline": [f"trading_backtest_phase{i}" for i in range(1, 9)],
        "validation_pipeline": [
            "trading_validation_oos",
            "trading_validation_martingale",
            "trading_validation_slippage",
            "trading_validation_survivorship",
            "trading_validation_sample",
        ],
        "regime_allocation": ["trading_regime_detection", "trading_auto_allocation"],
        "portfolio": ["trading_rebalance_daily"],
        "capital_ladder": ["trading_capital_ladder_check"],
        "kill_switch": ["trading_kill_switch_monitor"],
        "paper_auto_advance": ["trading_paper_auto_advance"],
        "copy_opt": ["trading_copy_optimization"],
        "live_monitor": ["trading_live_monitor"],
        "revenue_tracking": ["trading_revenue_tracking"],
        "discovery": ["trading_dna_update", "trading_discovery"],
    }

    category_counts = {}
    for category, job_ids in categories.items():
        count = sum(1 for j in jobs if j.job_id in job_ids)
        if count > 0:
            category_counts[category] = count

    result = {
        "total_jobs": len(jobs),
        "enabled": enabled,
        "disabled": disabled,
        "by_type": by_type,
        "by_cycle": by_cycle,
        "categories": category_counts,
        "job_ids": [j.job_id for j in jobs],
    }

    return JSONResponse(content=result)
