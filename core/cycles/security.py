"""Security Cycle — Rastro as a Work Cycle.

Coordinates: Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from core.cycles.executive_dashboard import ExecutiveDashboard
from core.cycles.knowledge_capture import KnowledgeCapture, LearningType
from core.cycles.models import Cycle, Task, TaskStatus

logger = logging.getLogger("ownex.cycles.security")


def _get_cycle_service():
    from core.cycles.service import get_cycle_service

    return get_cycle_service()


class SecurityCycle:
    """Security Cycle — wraps Rastro pipeline as an OWNEX Work Cycle.

    Stages:
    1. RECON — target discovery, asset enumeration
    2. ATTACK_SURFACE — port scan, subdomain, tech detection
    3. HYPOTHESIS — vulnerability hypothesis generation
    4. VALIDATION — PoC execution, verification
    5. EVIDENCE — evidence collection, composer
    6. REPORT — report generation, quality gate
    7. LEARNING — knowledge capture from outcome
    """

    STAGE_ORDER = [
        "recon",
        "attack_surface",
        "hypothesis",
        "validation",
        "evidence",
        "report",
        "learning",
    ]

    def __init__(self) -> None:
        self._cycle_service = _get_cycle_service()
        self._knowledge = KnowledgeCapture()
        self._executive = ExecutiveDashboard()

    def ensure_cycle(self) -> Cycle:
        """Ensure the Security cycle exists in DB."""
        cycle = self._cycle_service.get_by_slug("security")
        if not cycle:
            cycle = self._cycle_service.create(
                {
                    "name": "Security",
                    "slug": "security",
                    "description": "Bug bounty, Rastro, vulnerability research",
                    "category": "offensive",
                    "enabled": True,
                    "priority": 100,
                    "status": "idle",
                    "config": {"rastro_integration": True, "auto_priority": True},
                }
            )
            logger.info("Created Security cycle")
        return cycle

    def start_cycle(self) -> Cycle:
        """Start the Security cycle."""
        cycle = self.ensure_cycle()
        if cycle.status in ("running", "completed"):
            logger.warning("Cycle already running or completed")
            return cycle

        # Create tasks for each stage
        self._create_stage_tasks(cycle.id)

        activated = self._cycle_service.activate(cycle.id, next_action="recon")
        logger.info("Security cycle started")
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
            "recon": 1.0,
            "attack_surface": 2.0,
            "hypothesis": 0.5,
            "validation": 4.0,
            "evidence": 1.0,
            "report": 2.0,
            "learning": 0.5,
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
            current_task.completed_at = datetime.now(timezone.utc)

            # Start next
            if next_task:
                next_task.status = TaskStatus.RUNNING.value
                next_task.started_at = datetime.now(timezone.utc)
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

    def capture_learning(self, finding_id: int) -> Any:
        """Capture knowledge from a finding outcome."""
        from database import db as db_mod
        from database.models import Finding

        session = db_mod.SessionLocal()
        try:
            finding = session.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                return None

            if finding.status == "confirmed":
                return self._knowledge.capture_from_finding(finding)
            elif finding.status in ("rejected", "dismissed"):
                return self._knowledge.capture_failure(finding, f"Status: {finding.status}")
            return None
        finally:
            session.close()

    def capture_payout_learning(self, payout_id: int) -> Any:
        """Capture learning from a confirmed payout."""
        from database import db as db_mod
        from database.models_economic import PayoutRecord

        session = db_mod.SessionLocal()
        try:
            payout = session.query(PayoutRecord).filter(PayoutRecord.id == payout_id).first()
            if not payout or payout.status != "confirmed":
                return None
            return self._knowledge.capture_from_payout(payout)
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

    def get_knowledge_by_vuln(self, vuln_type: str) -> list[dict[str, Any]]:
        return [self._knowledge.to_dict(e) for e in self._knowledge.get_entries_by_vuln_type(vuln_type)]

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


_SECURITY_CYCLE: SecurityCycle | None = None


def get_security_cycle() -> SecurityCycle:
    """Get the global SecurityCycle instance."""
    global _SECURITY_CYCLE
    if _SECURITY_CYCLE is None:
        _SECURITY_CYCLE = SecurityCycle()
    return _SECURITY_CYCLE


# Register Security cycle in CycleRegistry
def register_security_cycle(registry) -> None:
    """Register Security cycle definition."""
    import contextlib

    from core.cycles.registry import CycleDefinition

    with contextlib.suppress(ValueError):
        registry.register(
            CycleDefinition(
                slug="security",
                name="Security",
                description="Bug bounty, vulnerability research, Rastro pipeline",
                category="offensive",
                priority=10,
                config={
                    "source_apps": ["rastro", "aegis"],
                    "auto_priority": True,
                    "stages": ["recon", "attack_surface", "hypothesis", "validation", "evidence", "report", "learning"],
                },
            )
        )
