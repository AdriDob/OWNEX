"""Cycle Tasks — scheduled tasks for automatic pipeline advancement.

Handlers referenced by scheduler jobs:
   - advance_security_pipeline: auto-advance through pipeline stages
"""

import logging
from typing import Any

from cores.cycles.models import Task, TaskStatus
from cores.cycles.security import get_security_cycle
from cores.database.manager import get_db_manager

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


def run_daily_delivery_preparation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-prepare delivery packages for all ready WorkBank items.

    Called daily by the scheduler after the Work Bank cycle: iterates items
    flagged ready_to_deliver, builds delivery packages (README/proposal/work
    files), and saves them to disk. The user only needs to review and submit
    — no manual preparation required.
    """
    import asyncio

    try:
        from cores.direct_work_engine.workbank import get_workbank
        from cores.opportunity.executors.assisted_mode import AssistedExecutor

        max_delivery_items: int = 10
        wb = get_workbank()
        ready_items = [i for i in wb.best_ready(limit=200) if i.ready_to_deliver][:max_delivery_items]
        executor = AssistedExecutor(base_executor=None)

        async def _prepare() -> int:
            prepared = 0
            for item in ready_items:
                opportunity = {
                    "platform": str(item.platform),
                    "id": item.id,
                    "title": item.title,
                    "description": item.description or " ".join(item.deliverables),
                    "url": item.url or "",
                }
                pkg = await executor.prepare_work(opportunity)
                await executor.save_work_to_disk(pkg)
                prepared += 1
            return prepared

        prepared = asyncio.run(_prepare())

        # Notify user that packages are ready for submission
        if prepared:
            from cores.notifications.action_required import notify_action_required

            notify_action_required(
                title=f"{prepared} paquetes de entrega listos para submitir",
                reason="Preparación automática completada. Revisar y submitir.",
                impact=f"{prepared} trabajos preparados en ~/ownex/submissions/",
                steps=[
                    "Revisar los paquetes en ~/ownex/submissions/",
                    "Submitir cada trabajo en la plataforma correspondiente",
                    "Marcar como entregado en el dashboard",
                ],
                ui_path="/direct-work",
                category="delivery",
                priority="medium",
                channels=["web", "desktop"],
                subject_id="daily_delivery",
                subject_type="workflow",
            )

        return {
            "status": "ok",
            "prepared_count": prepared,
            "total_ready": len(ready_items),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not auto-prepare delivery: %s", e)
        return {"status": "error", "message": str(e)}
