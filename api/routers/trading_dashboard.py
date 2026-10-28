"""Trading Dashboard — Monitors the state of 25 autonomous trading jobs."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from cores.scheduler.jobs import get_trading_jobs

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
