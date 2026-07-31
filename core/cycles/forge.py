"""Forge Cycle — Dev Bounties, OSS Contributions, Code Review Rewards.

Coordinates: Discover → Analyze → Prepare → Submit → Track → Learn
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from core.cycles.executive_dashboard import ExecutiveDashboard
from core.cycles.knowledge_capture import KnowledgeCapture, LearningType
from core.cycles.models import Cycle, Task, TaskStatus

logger = logging.getLogger("ownex.cycles.forge")


def _get_cycle_service():
    from core.cycles.service import get_cycle_service

    return get_cycle_service()


class ForgeCycle:
    """Forge Cycle — Dev bounties, OSS contributions, code review rewards.

    Stages:
    1. DISCOVER — platform scanning, issue detection, bounty listing
    2. ANALYZE — requirement analysis, skill matching, effort estimation
    3. PREPARE — solution design, environment setup, implementation plan
    4. SUBMIT — PR creation, submission, platform-specific formatting
    5. TRACK — review monitoring, feedback handling, iteration
    6. LEARN — knowledge capture from outcome, pattern extraction
    """

    STAGE_ORDER = [
        "discover",
        "analyze",
        "prepare",
        "submit",
        "track",
        "learn",
    ]

    def __init__(self) -> None:
        self._cycle_service = _get_cycle_service()
        self._knowledge = KnowledgeCapture()
        self._executive = ExecutiveDashboard()

    def ensure_cycle(self) -> Cycle:
        """Ensure the Forge cycle exists in DB."""
        cycle = self._cycle_service.get_by_slug("forge")
        if not cycle:
            cycle = self._cycle_service.create(
                {
                    "name": "Forge",
                    "slug": "forge",
                    "description": "Dev bounties, OSS contributions, code review rewards",
                    "category": "development",
                    "enabled": True,
                    "priority": 8,
                    "status": "idle",
                    "config": {"platforms": ["superteam", "opire", "algora", "issuehunt"], "auto_discover": True},
                }
            )
            logger.info("Created Forge cycle")
        return cycle

    def start_cycle(self) -> Cycle:
        """Start the Forge cycle."""
        cycle = self.ensure_cycle()
        if cycle.status in ("running", "completed"):
            logger.warning("Cycle already running or completed")
            return cycle

        # Create tasks for each stage
        self._create_stage_tasks(cycle.id)

        activated = self._cycle_service.activate(cycle.id, next_action="discover")
        logger.info("Forge cycle started")
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
            "discover": 0.5,
            "analyze": 1.0,
            "prepare": 2.0,
            "submit": 1.0,
            "track": 0.5,
            "learn": 0.5,
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

    def capture_learning(self, submission_id: int) -> Any:
        """Capture knowledge from a submission outcome."""
        from database import db as db_mod
        from database.models import Submission

        session = db_mod.SessionLocal()
        try:
            submission = session.query(Submission).filter(Submission.id == submission_id).first()
            if not submission:
                return None

            if submission.status == "accepted":
                return self._knowledge.capture_from_submission(submission)
            elif submission.status in ("rejected", "closed"):
                return self._knowledge.capture_failure(submission, f"Status: {submission.status}")
            return None
        finally:
            session.close()

    def capture_review_learning(self, review_id: int) -> Any:
        """Capture knowledge from a code review."""
        from database import db as db_mod
        from database.models import Review

        session = db_mod.SessionLocal()
        try:
            review = session.query(Review).filter(Review.id == review_id).first()
            if not review:
                return None

            if review.status == "approved":
                return self._knowledge.capture_from_review(review)
            elif review.status in ("changes_requested", "rejected"):
                return self._knowledge.capture_failure(review, f"Status: {review.status}")
            return None
        finally:
            session.close()

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


_FORGE_CYCLE: ForgeCycle | None = None


def get_forge_cycle() -> ForgeCycle:
    """Get the global ForgeCycle instance."""
    global _FORGE_CYCLE
    if _FORGE_CYCLE is None:
        _FORGE_CYCLE = ForgeCycle()
    return _FORGE_CYCLE


# Register Forge cycle in CycleRegistry
def register_forge_cycle(registry) -> None:
    """Register Forge cycle definition."""
    import contextlib

    from core.cycles.registry import CycleDefinition

    with contextlib.suppress(ValueError):
        registry.register(
            CycleDefinition(
                slug="forge",
                name="Forge",
                description="Dev bounties, OSS contributions, code review rewards",
                category="development",
                priority=8,
                config={
                    "platforms": ["superteam", "opire", "algora", "issuehunt"],
                    "auto_discover": True,
                },
            )
        )
