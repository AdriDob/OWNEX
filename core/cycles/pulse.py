"""Pulse Cycle -- AI Training, Data Annotation, Microtask Platforms.

Coordinates: Scan -> Match -> Prepare -> Execute -> Submit -> Learn
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from core.cycles.executive_dashboard import ExecutiveDashboard
from core.cycles.knowledge_capture import KnowledgeCapture, LearningType
from core.cycles.models import Cycle, Task, TaskStatus

logger = logging.getLogger("ownex.cycles.pulse")


def _get_cycle_service():
    from core.cycles.service import get_cycle_service

    return get_cycle_service()


class PulseCycle:
    """Pulse Cycle -- AI training, data annotation, microtask platforms.

    Stages:
    1. SCAN -- platform monitoring, task discovery, skill matching
    2. MATCH -- qualification check, priority scoring, effort estimation
    3. PREPARE -- environment setup, data preparation, guideline review
    4. EXECUTE -- task completion, quality assurance, time tracking
    5. SUBMIT -- submission, platform formatting, receipt confirmation
    6. LEARN -- outcome analysis, skill improvement, platform optimization
    """

    STAGE_ORDER = [
        "scan",
        "match",
        "prepare",
        "execute",
        "submit",
        "learn",
    ]

    def __init__(self) -> None:
        self._cycle_service = _get_cycle_service()
        self._knowledge = KnowledgeCapture()
        self._executive = ExecutiveDashboard()

    def ensure_cycle(self) -> Cycle:
        """Ensure the Pulse cycle exists in DB."""
        cycle = self._cycle_service.get_by_slug("pulse")
        if not cycle:
            cycle = self._cycle_service.create(
                {
                    "name": "Pulse",
                    "slug": "pulse",
                    "description": "AI training, data annotation, microtask platforms",
                    "category": "ai_work",
                    "enabled": True,
                    "priority": 6,
                    "status": "idle",
                    "config": {
                        "platforms": ["outlier", "dataannotation", "mindrift", "remotasks"],
                        "skill_match": True,
                    },
                }
            )
            logger.info("Created Pulse cycle")
        return cycle

    def start_cycle(self) -> Cycle:
        """Start the Pulse cycle."""
        cycle = self.ensure_cycle()
        if cycle.status in ("running", "completed"):
            logger.warning("Cycle already running or completed")
            return cycle

        # Create tasks for each stage
        self._create_stage_tasks(cycle.id)

        activated = self._cycle_service.activate(cycle.id, next_action="scan")
        logger.info("Pulse cycle started")
        return activated

    def _create_stage_tasks(self, cycle_id: int) -> list[Task]:
        """Create tasks for each pipeline stage."""
        from core.database.manager import get_db_manager

        mgr = get_db_manager()
        db_session = mgr.get_session("cycles")

        tasks = []
        for i, stage in enumerate(self.STAGE_ORDER):
            task = Task(
                cycle_id=cycle_id,
                name=stage.replace("_", " ").title(),
                description=f"Pipeline stage: {stage}",
                status=TaskStatus.PENDING.value,
                priority=100 - i,
                order=i,
                estimated_hours=self._estimate_hours(stage),
            )
            db_session.add(task)
            tasks.append(task)

        db_session.commit()
        for t in tasks:
            db_session.refresh(t)
        return tasks

    def _estimate_hours(self, stage: str) -> float:
        estimates = {
            "scan": 0.25,
            "match": 0.5,
            "prepare": 0.5,
            "execute": 2.0,
            "submit": 0.25,
            "learn": 0.25,
        }
        return estimates.get(stage, 1.0)

    def advance_stage(self, cycle_id: int, stage: str, result: dict[str, Any] | None = None) -> Task | None:
        """Mark a stage complete and advance to next."""
        from core.database.manager import get_db_manager

        mgr = get_db_manager()
        db_session = mgr.get_session("cycles")

        try:
            # Find current task
            tasks = db_session.query(Task).filter(Task.cycle_id == cycle_id).order_by(Task.order).all()
            current_task = None
            next_task = None

            for i, t in enumerate(tasks):
                if t.name.lower().replace(" ", "_") == stage:
                    current_task = t
                    if i + 1 < len(tasks):
                        next_task = tasks[i + 1]
                    break

            if not current_task:
                logger.warning("Stage %s not found in cycle %d", stage, cycle_id)
                return None

            # Complete current
            current_task.status = TaskStatus.COMPLETED.value
            current_task.result = json.dumps(result or {})
            current_task.completed_at = datetime.now(UTC)

            # Start next
            if next_task:
                next_task.status = TaskStatus.RUNNING.value
                next_task.started_at = datetime.now(UTC)
                # Update cycle next_action
                cycle = self._cycle_service.get(cycle_id)
                if cycle:
                    cycle.config_dict.update({"next_action": next_task.name.lower().replace(" ", "_")})
                    cycle.config = json.dumps(cycle.config_dict)

            db_session.commit()
            if current_task:
                db_session.refresh(current_task)
            logger.info("Advanced from %s to %s", stage, next_task.name if next_task else "COMPLETED")
            return current_task

        except Exception as e:
            db_session.rollback()
            logger.error("Failed to advance stage: %s", e)
            raise
        finally:
            db_session.close()

    def capture_learning(self, task_id: int) -> Any:
        """Capture knowledge from a task outcome - stores as failure analysis."""
        return None

    def get_dashboard(self) -> dict[str, Any]:
        """Get CEO dashboard view."""
        return self._executive.get_ceo_view()

    def get_knowledge(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent knowledge entries."""
        return [self._knowledge.to_dict(e) for e in self._knowledge.get_entries(limit)]

    def get_knowledge_by_type(self, type_: LearningType) -> list[dict[str, Any]]:
        return [self._knowledge.to_dict(e) for e in self._knowledge.get_entries_by_type(type_)]

    def get_knowledge_by_platform(self, platform: str) -> list[dict[str, Any]]:
        return [self._knowledge.to_dict(e) for e in self._knowledge.get_entries_by_platform(platform)]

    def get_cycle_status(self) -> dict[str, Any]:
        """Get current cycle status with tasks."""
        cycle = self.ensure_cycle()
        tasks = self._cycle_service.get_metrics(cycle.id)
        return {
            "cycle": {"id": cycle.id, "name": cycle.name, "status": cycle.status},
            "stages": self.STAGE_ORDER,
            "metrics": tasks,
        }


_PULSE_CYCLE: PulseCycle | None = None


def get_pulse_cycle() -> PulseCycle:
    """Get the global PulseCycle instance."""
    global _PULSE_CYCLE
    if _PULSE_CYCLE is None:
        _PULSE_CYCLE = PulseCycle()
    return _PULSE_CYCLE


# Register Pulse cycle in CycleRegistry
def register_pulse_cycle(registry) -> None:
    """Register Pulse cycle definition."""
    import contextlib

    from core.cycles.registry import CycleDefinition

    with contextlib.suppress(ValueError):
        registry.register(
            CycleDefinition(
                slug="pulse",
                name="Pulse",
                description="AI training, data annotation, microtask platforms",
                category="ai_work",
                priority=6,
                config={
                    "platforms": ["outlier", "dataannotation", "mindrift", "remotasks"],
                    "skill_match": True,
                },
            )
        )
