"""Vault Cycle — Wealth Management, Capital Allocation, Revenue Tracking.

Coordinates: Monitor -> Analyze -> Allocate -> Execute -> Track -> Learn
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from core.cycles.executive_dashboard import ExecutiveDashboard
from core.cycles.knowledge_capture import KnowledgeCapture, LearningType
from core.cycles.models import Cycle, Task, TaskStatus

logger = logging.getLogger("ownex.cycles.vault")


def _get_cycle_service():
    from core.cycles.service import get_cycle_service

    return get_cycle_service()


class VaultCycle:
    """Vault Cycle — Wealth management, capital allocation, revenue tracking.

    Stages:
    1. MONITOR — portfolio monitoring, revenue tracking, platform balances
    2. ANALYZE — performance analysis, risk assessment, opportunity identification
    3. ALLOCATE — capital allocation, rebalancing, investment decisions
    4. EXECUTE — transaction execution, platform interaction, confirmation
    5. TRACK — position tracking, P&L monitoring, alert management
    6. LEARN — outcome analysis, strategy refinement, pattern extraction
    """

    STAGE_ORDER = [
        "monitor",
        "analyze",
        "allocate",
        "execute",
        "track",
        "learn",
    ]

    def __init__(self) -> None:
        self._cycle_service = _get_cycle_service()
        self._knowledge = KnowledgeCapture()
        self._executive = ExecutiveDashboard()

    def ensure_cycle(self) -> Cycle:
        """Ensure the Vault cycle exists in DB."""
        cycle = self._cycle_service.get_by_slug("vault")
        if not cycle:
            cycle = self._cycle_service.create(
                {
                    "name": "Vault",
                    "slug": "vault",
                    "description": "Wealth management, capital allocation, revenue tracking",
                    "category": "wealth",
                    "enabled": True,
                    "priority": 7,
                    "status": "idle",
                    "config": {
                        "platforms": ["binance", "coinbase", "kraken", "firefly"],
                        "auto_rebalance": False,
                        "risk_threshold": 0.15,
                    },
                }
            )
            logger.info("Created Vault cycle")
        return cycle

    def start_cycle(self) -> Cycle:
        """Start the Vault cycle."""
        cycle = self.ensure_cycle()
        if cycle.status in ("running", "completed"):
            logger.warning("Cycle already running or completed")
            return cycle

        # Create tasks for each stage
        self._create_stage_tasks(cycle.id)

        activated = self._cycle_service.activate(cycle.id, next_action="monitor")
        logger.info("Vault cycle started")
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
            "monitor": 0.25,
            "analyze": 1.0,
            "allocate": 0.5,
            "execute": 0.5,
            "track": 0.25,
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

    def capture_learning(self, operation_id: int) -> Any:
        """Capture knowledge from an operation outcome."""
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


_VAULT_CYCLE: VaultCycle | None = None


def get_vault_cycle() -> VaultCycle:
    """Get the global VaultCycle instance."""
    global _VAULT_CYCLE
    if _VAULT_CYCLE is None:
        _VAULT_CYCLE = VaultCycle()
    return _VAULT_CYCLE


# Register Vault cycle in CycleRegistry
def register_vault_cycle(registry) -> None:
    """Register Vault cycle definition."""
    import contextlib

    from core.cycles.registry import CycleDefinition

    with contextlib.suppress(ValueError):
        registry.register(
            CycleDefinition(
                slug="vault",
                name="Vault",
                description="Wealth management, capital allocation, revenue tracking",
                category="wealth",
                priority=7,
                config={
                    "platforms": ["binance", "coinbase", "kraken", "firefly"],
                    "auto_rebalance": False,
                    "risk_threshold": 0.15,
                },
            )
        )
