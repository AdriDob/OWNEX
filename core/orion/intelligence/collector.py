"""Orion intelligence collector — gather system intelligence and trends."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("ownex.orion.intelligence.collector")


async def collect_intel() -> dict[str, Any]:
    """Collect system intelligence — trends, metrics, and insights.

    Scheduler handler: ``core.orion.intelligence.collector:collect_intel``
    """
    try:
        intel: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Opportunity counts
        try:
            from core.opportunity import get_engine

            engine = get_engine()
            all_opps = engine.get_all()
            intel["opportunities"] = {
                "total": len(all_opps),
                "forge": sum(1 for o in all_opps if getattr(o, "cycle", None) == "forge"),
                "pulse": sum(1 for o in all_opps if getattr(o, "cycle", None) == "pulse"),
            }
        except Exception as e:
            intel["opportunities"] = {"error": str(e)}

        # 2. Revenue estimates
        try:
            intel["revenue"] = {
                "estimated_pending": 0.0,
                "cycle": "forge",
            }
        except Exception as e:
            intel["revenue"] = {"error": str(e)}

        # 3. System uptime
        try:
            with open("/proc/uptime") as f:
                uptime_seconds = float(f.read().split()[0])
            intel["uptime_hours"] = round(uptime_seconds / 3600, 1)
        except Exception:
            intel["uptime_hours"] = 0.0

        # 4. Active jobs from scheduler
        try:
            from core.scheduler.scheduler import get_core_scheduler

            scheduler = get_core_scheduler()
            jobs = scheduler.get_jobs()
            intel["scheduler_jobs"] = len(jobs)
            intel["active_cycles"] = list(set(j.get("app_id") for j in jobs))
        except Exception as e:
            intel["scheduler_jobs"] = 0
            intel["scheduler_error"] = str(e)

        intel["success"] = True
        return intel

    except Exception as e:
        logger.error(f"Intel collection failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
