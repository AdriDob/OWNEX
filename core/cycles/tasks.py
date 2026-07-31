"""Cycle Tasks — scheduled tasks for automatic pipeline advancement.

Handlers referenced by scheduler jobs:
   - advance_security_pipeline: auto-advance through pipeline stages
"""

import logging
from typing import Any

from core.cycles.security import get_security_cycle

logger = logging.getLogger("ownex.cycles.tasks")


def auto_start_security_cycle(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-start the Security Cycle if it is idle/inactive.

    Called every 2 hours by the scheduler.
    """
    security = get_security_cycle()
    cycle = security.ensure_cycle()

    if cycle.status in ("idle", "inactive"):
        try:
            cycle = security.start_cycle()
            logger.info("Security cycle auto-started by scheduler")
            return {"status": "started", "cycle_id": cycle.id}
        except Exception as e:
            logger.warning("Could not auto-start security cycle: %s", e)
            return {"status": "error", "message": str(e)}

    return {"status": "skipped", "reason": f"cycle status is {cycle.status}"}


def advance_security_pipeline(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-advance the Security Cycle pipeline.

    Called every 30 minutes by the scheduler. Runs the full 7-stage
    pipeline end-to-end, connecting the stage executors with the DB cycle.
    """
    security = get_security_cycle()
    cycle = security.ensure_cycle()

    if cycle.status not in ("running", "idle", "inactive"):
        return {"status": "skipped", "reason": f"cycle status is {cycle.status}"}

    try:
        result = security.run_pipeline({"mode": "auto"})
        return {
            "status": "ok",
            "overall": result.get("overall"),
            "stages_completed": result.get("stages_completed"),
            "stages_total": result.get("stages_total"),
            "cycle_id": result.get("cycle_id"),
        }
    except Exception as e:
        logger.error("Error advancing security pipeline: %s", e)
        return {"status": "error", "message": str(e)}
