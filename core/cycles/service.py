"""Cycle Engine — Service layer for Work Cycle operations."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core.cycles.models import DEFAULT_CYCLES, Base, Cycle, CycleStatus
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.core.cycles")


DB_ID = "cycles"


def _ensure_db() -> Session:
    mgr = get_db_manager()
    if DB_ID not in mgr.list_databases():
        mgr.register(DB_ID, "cycles.db")
        mgr.run_migrations(DB_ID, Base)
    return mgr.get_session(DB_ID)


class CycleService:
    """Service for managing Work Cycles lifecycle."""

    def __init__(self) -> None:
        self._initialized = False

    def _ensure_init(self) -> None:
        if not self._initialized:
            db = _ensure_db()
            existing = db.query(Cycle).count()
            if existing == 0:
                self._seed_defaults(db)
            self._initialized = True

    def _seed_defaults(self, db: Session) -> None:
        """Seed default cycles if database is empty."""
        import json

        for cycle_data in DEFAULT_CYCLES:
            data = dict(cycle_data)
            if isinstance(data.get("config"), dict):
                data["config"] = json.dumps(data["config"])
            cycle = Cycle(**data)
            db.add(cycle)
        db.commit()
        logger.info("Seeded %d default cycles", len(DEFAULT_CYCLES))

    # ── CRUD ─────────────────────────────────────────────────────────

    def create(self, data: dict[str, Any]) -> Cycle:
        self._ensure_init()
        db = _ensure_db()
        try:
            cycle = Cycle(**data)
            db.add(cycle)
            db.commit()
            db.refresh(cycle)
            logger.info("Created cycle: %s (%s)", cycle.name, cycle.slug)
            return cycle
        except Exception as e:
            db.rollback()
            logger.error("Failed to create cycle: %s", e)
            raise

    def get(self, cycle_id: int) -> Cycle | None:
        self._ensure_init()
        db = _ensure_db()
        return db.query(Cycle).filter(Cycle.id == cycle_id).first()

    def get_by_slug(self, slug: str) -> Cycle | None:
        self._ensure_init()
        db = _ensure_db()
        return db.query(Cycle).filter(Cycle.slug == slug).first()

    def list(self, enabled_only: bool = False) -> list[Cycle]:
        self._ensure_init()
        db = _ensure_db()
        q = db.query(Cycle).order_by(Cycle.priority.desc(), Cycle.name.asc())
        if enabled_only:
            q = q.filter(Cycle.enabled.is_(True))
        return q.all()

    def update(self, cycle_id: int, data: dict[str, Any]) -> Cycle | None:
        self._ensure_init()
        db = _ensure_db()
        try:
            cycle = db.query(Cycle).filter(Cycle.id == cycle_id).first()
            if not cycle:
                return None
            for key, value in data.items():
                if hasattr(cycle, key) and key not in ("id", "slug", "created_at"):
                    setattr(cycle, key, value)
            cycle.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(cycle)
            logger.info("Updated cycle: %s", cycle.name)
            return cycle
        except Exception as e:
            db.rollback()
            logger.error("Failed to update cycle %d: %s", cycle_id, e)
            raise

    def delete(self, cycle_id: int) -> bool:
        self._ensure_init()
        db = _ensure_db()
        try:
            cycle = db.query(Cycle).filter(Cycle.id == cycle_id).first()
            if not cycle:
                return False
            db.delete(cycle)
            db.commit()
            logger.info("Deleted cycle: %s", cycle.name)
            return True
        except Exception as e:
            db.rollback()
            logger.error("Failed to delete cycle %d: %s", cycle_id, e)
            return False

    # ── Status Management ───────────────────────────────────────────

    def activate(self, cycle_id: int, next_action: str | None = None) -> Cycle | None:
        """Set cycle to RUNNING status."""
        self._ensure_init()
        db = _ensure_db()
        try:
            cycle = db.query(Cycle).filter(Cycle.id == cycle_id).first()
            if not cycle:
                return None
            cycle.status = CycleStatus.RUNNING.value
            cycle.updated_at = datetime.now(UTC)
            if next_action:
                config = cycle.config_dict
                config["next_action"] = next_action
                cycle.config = json.dumps(config)
            db.commit()
            db.refresh(cycle)
            logger.info("Activated cycle: %s", cycle.name)
            return cycle
        except Exception as e:
            db.rollback()
            logger.error("Failed to activate cycle %d: %s", cycle_id, e)
            raise

    def pause(self, cycle_id: int) -> Cycle | None:
        """Set cycle to PAUSED status."""
        return self.update(cycle_id, {"status": CycleStatus.PAUSED.value})

    def complete(self, cycle_id: int) -> Cycle | None:
        """Set cycle to COMPLETED status."""
        return self.update(cycle_id, {"status": CycleStatus.COMPLETED.value})

    def set_error(self, cycle_id: int, error_msg: str) -> Cycle | None:
        """Set cycle to ERROR status with message."""
        self._ensure_init()
        db = _ensure_db()
        try:
            cycle = db.query(Cycle).filter(Cycle.id == cycle_id).first()
            if not cycle:
                return None
            cycle.status = CycleStatus.ERROR.value
            config = cycle.config_dict
            config["last_error"] = error_msg
            config["error_at"] = datetime.now(UTC).isoformat()
            cycle.config = json.dumps(config)
            cycle.updated_at = datetime.now(UTC)
            db.commit()
            db.refresh(cycle)
            return cycle
        except Exception as e:
            db.rollback()
            logger.error("Failed to set error on cycle %d: %s", cycle_id, e)
            raise

    # ── Metrics ──────────────────────────────────────────────────────

    def get_metrics(self, cycle_id: int) -> dict[str, Any]:
        """Get metrics for a cycle. Placeholder for future metrics aggregation."""
        self._ensure_init()
        cycle = self.get(cycle_id)
        if not cycle:
            return {}
        config = cycle.config_dict
        return {
            "opportunities_found": config.get("opportunities_found", 0),
            "tasks_active": config.get("tasks_active", 0),
            "tasks_completed": config.get("tasks_completed", 0),
            "estimated_value": config.get("estimated_value", 0.0),
            "success_rate": config.get("success_rate", 0.0),
            "last_execution": config.get("last_execution"),
            "next_action": config.get("next_action"),
        }

    def update_metrics(self, cycle_id: int, metrics: dict[str, Any]) -> Cycle | None:
        """Update cycle metrics stored in config."""
        cycle = self.get(cycle_id)
        if not cycle:
            return None
        config = cycle.config_dict
        config.update(metrics)
        cycle.config = json.dumps(config)
        cycle.updated_at = datetime.now(UTC)
        db = _ensure_db()
        db.commit()
        db.refresh(cycle)
        return cycle


# Singleton
_cycle_service: CycleService | None = None


def get_cycle_service() -> CycleService:
    global _cycle_service
    if _cycle_service is None:
        _cycle_service = CycleService()
    return _cycle_service
