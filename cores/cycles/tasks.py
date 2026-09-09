"""Cycle Tasks — scheduled tasks for automatic pipeline advancement.

Handlers referenced by scheduler jobs:
   - advance_security_pipeline: auto-advance through pipeline stages
   - auto_start_security_cycle: ensure the security cycle is running
   - auto_submit_pending_findings: sweep confirmed findings through the
     AutoSubmitPipeline elite gate (every 30 min)
   - run_daily_market_evolution: refresh the MarketKnowledgeBase
   - run_daily_task_refresh: auto-complete resolved daily milestones
   - run_qa_cycle: run the QA testing cycle
   - run_daily_evolution_report: persist the daily optimization report
   - run_daily_delivery_preparation: prepare delivery packages for review
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


def auto_submit_pending_findings(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-submit confirmed findings that pass the Quality Gate.

    Called every 30 minutes by the scheduler. Scans for findings with status
    ``confirmed`` that are not yet attached to a submitted/pending report,
    runs the AutoSubmitPipeline elite gate on each (severity, confidence,
    quality, evidence, repro steps + rate limit), and submits elite-quality
    findings to their target platform. Findings below the bar are queued for
    human review by the pipeline itself — nothing is silently dropped.
    """
    import json

    try:
        from cores.auto_submit.pipeline import get_auto_submit_pipeline
        from database import db, models

        session = db.SessionLocal()
        try:
            confirmed = (
                session.query(models.Finding)
                .filter(models.Finding.status == "confirmed")
                .order_by(models.Finding.id)
                .all()
            )
            submitted_ids: set[int] = set()
            for (raw_ids,) in (
                session.query(models.Report.finding_ids)
                .filter(models.Report.status.in_(["submitted", "pending"]))
                .all()
            ):
                if not raw_ids:
                    continue
                try:
                    parsed = json.loads(raw_ids)
                except (TypeError, ValueError):
                    continue
                if isinstance(parsed, list):
                    submitted_ids.update(int(i) for i in parsed if isinstance(i, int))
        finally:
            session.close()

        pending = [f for f in confirmed if int(f.id) not in submitted_ids]
        if not pending:
            return {"status": "ok", "scanned": len(confirmed), "actions": [], "message": "nothing to submit"}

        pipeline = get_auto_submit_pipeline()
        actions: list[dict[str, Any]] = []
        for finding in pending:
            try:
                result = pipeline.on_finding_confirmed(int(finding.id))
                actions.append(
                    {
                        "finding_id": finding.id,
                        "action": result.get("action"),
                        "score": result.get("score"),
                        "platform": result.get("platform"),
                    }
                )
                logger.info("[AUTO-SUBMIT-SWEEP] Finding %s → %s", finding.id, result.get("action"))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[AUTO-SUBMIT-SWEEP] Finding %s failed: %s", finding.id, exc)
                actions.append({"finding_id": finding.id, "action": "error", "error": str(exc)})

        return {
            "status": "ok",
            "scanned": len(confirmed),
            "actions": actions,
            "message": f"processed {len(actions)} confirmed findings",
        }
    except Exception as e:  # noqa: BLE001
        logger.error("Auto-submit sweep failed: %s", e)
        return {"status": "error", "message": str(e)}


def run_daily_market_evolution(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-run the Market Evolution Engine daily.

    Called by the scheduler as part of the Direct Work cycle: analyzes the
    curated platform sources, computes OVOS scores, updates the persistent
    MarketKnowledgeBase, retires stale platforms, and persists the report.
    """
    try:
        from cores.direct_work_engine.market_evolution import get_market_evolution_engine

        engine = get_market_evolution_engine()
        report = engine.analyze()
        return {
            "status": "ok",
            "platforms_analyzed": report.get("platforms_analyzed", 0),
            "new_ecosystems": report.get("new_ecosystems_discovered", 0),
            "retired": report.get("rejected_platforms", 0),
            "best_recommendation": report.get("best_recommendation"),
            "friction_summary": report.get("friction_summary", {}),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not auto-run market evolution: %s", e)
        return {"status": "error", "message": str(e)}


def run_daily_task_refresh(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Refresh the daily task board and auto-complete resolved milestones.

    Called daily by the scheduler at 07:00: auto-marks tasks as done when their
    underlying milestone is already achieved in the system state, then refreshes
    the board so the operator always has an up-to-date action list.
    """
    try:
        from cores.daily_tasks import get_daily_task_board

        board = get_daily_task_board()
        auto_done = board.complete_done_from_state()
        tasks = board.get_tasks(force_refresh=True)
        return {
            "status": "ok",
            "auto_done": auto_done.get("auto_done", 0),
            "day": tasks.get("day", 0),
            "pending": tasks.get("total", 0) - tasks.get("done", 0),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not refresh daily tasks: %s", e)
        return {"status": "error", "message": str(e)}


def run_qa_cycle(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-run the QA Testing cycle.

    Called daily by the scheduler: generates test cases from the current
    targets/endpoints/findings, executes them, and persists the report.
    """
    from cores.cycles.qa import get_qa_cycle

    qa = get_qa_cycle()
    cycle = qa.ensure_cycle()

    if cycle.status in ("running",):
        return {"status": "skipped", "reason": "QA cycle already running"}

    try:
        result = qa.run_full_qa_cycle()
        return {
            "status": "ok",
            "cycle_id": result.get("cycle_id"),
            "tests": result.get("report", {}).get("total_tests", 0),
            "pass_rate": result.get("report", {}).get("pass_rate"),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not auto-run QA cycle: %s", e)
        return {"status": "error", "message": str(e)}


def run_daily_evolution_report(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-run the Daily Optimization Report and persist it.

    Called every day by the scheduler after the Work Bank cycle: the system
    audits itself (improvements, performance, automation, problems, next
    actions) and stores the snapshot + digest for trend history.
    """
    from cores.direct_work_engine.maximum_potential import (
        get_evolution_report,
        save_daily_report,
    )

    try:
        report = get_evolution_report()
        path = save_daily_report(report)
        return {
            "status": "ok",
            "report_path": path,
            "digest": report.get("digest", {}).get("text", ""),
            "trend": report.get("trend", {}),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not auto-run evolution report: %s", e)
        return {"status": "error", "message": str(e)}


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
