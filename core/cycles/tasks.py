"""Cycle Tasks — scheduled tasks for automatic pipeline advancement.

Handlers referenced by scheduler jobs:
   - advance_security_pipeline: auto-advance through pipeline stages
"""

import logging
from typing import Any

from core.cycles.security import get_security_cycle

logger = logging.getLogger("ownex.cycles.tasks")


def run_qa_cycle(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-run the QA Testing cycle.

    Called daily by the scheduler: generates test cases from the current
    targets/endpoints/findings, executes them, and persists the report.
    """
    from core.cycles.qa import get_qa_cycle

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


def run_daily_delivery_preparation(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Auto-prepare delivery packages for all ready WorkBank items.

    Called daily by the scheduler after the Work Bank cycle: iterates items
    flagged ready_to_deliver, builds delivery packages (README/proposal/work
    files), and saves them to disk. The user only needs to review and submit
    — no manual preparation required.
    """
    import asyncio

    try:
        from core.opportunity.executors.assisted_mode import AssistedExecutor
        from cores.direct_work_engine.workbank import get_workbank

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
