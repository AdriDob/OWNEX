"""Cycle Tasks — scheduled tasks for automatic pipeline advancement.

Handlers referenced by scheduler jobs:
   - advance_security_pipeline: auto-advance through pipeline stages
"""

import logging
from typing import Any

from core.cycles.models import Task, TaskStatus
from core.cycles.security import get_security_cycle
from core.database.manager import get_db_manager

logger = logging.getLogger("ownex.cycles.tasks")


def advance_security_pipeline(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-advance the Security Cycle pipeline.

    Called every 30 minutes by the scheduler.
    Checks current stage, attempts to advance if conditions are met.
    """
    security = get_security_cycle()
    cycle = security.ensure_cycle()

    if cycle.status != "running":
        # Try to start the cycle if idle
        if cycle.status in ("idle", "inactive"):
            try:
                cycle = security.start_cycle()
                logger.info("Security cycle auto-started")
            except Exception as e:
                logger.warning("Could not auto-start security cycle: %s", e)
                return {"status": "error", "message": str(e)}
        else:
            return {"status": "skipped", "reason": f"cycle status is {cycle.status}"}

    # Find the next pending task to advance
    mgr = get_db_manager()
    db = mgr.get_session("cycles")

    try:
        pending_tasks = (
            db.query(Task)
            .filter(Task.cycle_id == cycle.id, Task.status == TaskStatus.PENDING.value)
            .order_by(Task.order)
            .all()
        )

        if not pending_tasks:
            # All tasks complete or running — check if any running
            running = db.query(Task).filter(Task.cycle_id == cycle.id, Task.status == TaskStatus.RUNNING.value).first()
            if running:
                return {"status": "in_progress", "current": running.name}
            # Cycle might be done
            completed_count = (
                db.query(Task).filter(Task.cycle_id == cycle.id, Task.status == TaskStatus.COMPLETED.value).count()
            )
            total_count = db.query(Task).filter(Task.cycle_id == cycle.id).count()
            if completed_count == total_count and total_count > 0:
                service = security._cycle_service
                service.complete(cycle.id)
                logger.info("Security cycle completed automatically")
                return {"status": "completed"}
            return {"status": "no_pending_tasks"}

        # Advance the first pending task
        task = pending_tasks[0]
        stage_name = task.name.lower().replace(" ", "_")
        result = security.advance_stage(cycle.id, stage_name)

        if result:
            logger.info("Advanced security cycle to stage: %s", stage_name)
            return {"status": "advanced", "stage": stage_name}
        else:
            logger.warning("Failed to advance to stage: %s", stage_name)
            return {"status": "failed", "stage": stage_name}

    except Exception as e:
        logger.error("Error advancing security pipeline: %s", e)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
