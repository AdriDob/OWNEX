"""Content Factory API — visibility over MoneyPrinterTurbo pipeline (read-only).

Generation/publishing run on the factory's own APScheduler
(cores.content_factory.scheduler.get_content_factory_jobs); this router
only exposes status + schedules so Mission Control can see them.
No manual triggers here: video generation is heavy and stays on schedule
or behind explicit Human Gate flows.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/content-factory", tags=["content-factory"])


@router.get("/status")
async def content_factory_status() -> dict[str, Any]:
    """MPT health + material-key state + schedule overview (never raises)."""
    health: dict[str, Any] = {"healthy": False, "reason": "unknown"}
    try:
        from cores.content_factory.scheduler import run_health_check

        try:
            health = await asyncio.wait_for(run_health_check(), timeout=35.0)
        except TimeoutError:
            health = {"healthy": False, "reason": "health_check_timeout"}
    except Exception as exc:
        health = {"healthy": False, "reason": f"check_failed: {type(exc).__name__}"}
    try:
        from cores.setup.checklist import _detect_mpt_material_key

        material = _detect_mpt_material_key()
    except Exception:
        material = {"configured": False, "reason": "detector_unavailable"}
    return {"mpt": health, "material_key": material}


@router.get("/jobs")
async def content_factory_jobs() -> dict[str, Any]:
    """Scheduled factory jobs (generate/publish/analytics/optimize/health)."""
    try:
        from cores.content_factory.scheduler import get_content_factory_jobs

        jobs = []
        for job in get_content_factory_jobs():
            trigger = job.get("trigger")
            jobs.append(
                {
                    "job_id": job.get("job_id", ""),
                    "name": job.get("name", ""),
                    "handler": job.get("handler", ""),
                    "schedule": str(trigger) if trigger is not None else "unknown",
                }
            )
        return {"total": len(jobs), "jobs": jobs}
    except Exception as exc:
        return {"total": 0, "jobs": [], "error": f"jobs_unavailable: {type(exc).__name__}"}
