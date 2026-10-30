"""Mission Store — Persistencia SQLite para misiones OWNEX.

Single Source of Truth para el estado de cada misión/workflow.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from database.db import Base, SessionLocal

logger = logging.getLogger("ownex.mission.store")


class MissionStatus(StrEnum):
    """Estados de una misión."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    WAITING_EXTERNAL = "waiting_external"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionType(StrEnum):
    """Tipos de misión según el workflow."""

    SECURITY_PIPELINE = "security_pipeline"
    DEV_BOUNTY = "dev_bounty"
    DIRECT_WORK = "direct_work"
    EXECUTION_QUEUE = "execution_queue"
    DISCOVERY = "discovery"
    RECON = "recon"
    VALIDATION = "validation"
    EVIDENCE = "evidence"
    REPORT = "report"
    SUBMISSION = "submission"
    DELIVERY = "delivery"
    LEARNING = "learning"


@dataclass
class MissionCheckpoint:
    """Checkpoint de una misión para recovery."""

    mission_id: str
    stage: str
    result: dict[str, Any]
    context: dict[str, Any]
    timestamp: str


class MissionModel(Base):
    """Modelo SQLAlchemy para misiones."""

    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String(64), unique=True, nullable=False, index=True)
    mission_type = Column(String(32), nullable=False, index=True)
    opportunity_id = Column(String(64), nullable=True, index=True)
    workflow_id = Column(String(64), nullable=True, index=True)

    status = Column(String(32), nullable=False, default=MissionStatus.PENDING.value, index=True)
    priority = Column(Integer, default=0)
    expected_value_usd = Column(Float, default=0.0)
    actual_value_usd = Column(Float, default=0.0)

    current_stage = Column(String(64), nullable=True)
    stage_order = Column(Integer, default=0)
    total_stages = Column(Integer, default=0)

    # Payload y contexto de la misión
    payload_json = Column(Text, default="{}")
    context_json = Column(Text, default="{}")

    # Checkpoint para recovery
    last_checkpoint_json = Column(Text, default="{}")

    # Retry y error handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_state = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "mission_type": self.mission_type,
            "opportunity_id": self.opportunity_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "priority": self.priority,
            "expected_value_usd": self.expected_value_usd,
            "actual_value_usd": self.actual_value_usd,
            "current_stage": self.current_stage,
            "stage_order": self.stage_order,
            "total_stages": self.total_stages,
            "payload": json.loads(self.payload_json) if self.payload_json else {},
            "context": json.loads(self.context_json) if self.context_json else {},
            "last_checkpoint": json.loads(self.last_checkpoint_json) if self.last_checkpoint_json else {},
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_state": self.error_state,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }


class MissionCheckpointModel(Base):
    """Modelo para checkpoints persistentes (historial completo)."""

    __tablename__ = "mission_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(String(64), nullable=False, index=True)
    stage = Column(String(64), nullable=False)
    stage_order = Column(Integer, default=0)
    result_json = Column(Text, default="{}")
    context_json = Column(Text, default="{}")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class MissionStore:
    """Store para misiones — CRUD + checkpoints + queries operacionales."""

    def __init__(self, session_factory: Any = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def _get_session(self):
        return self._session_factory()

    # ── CRUD ────────────────────────────────────────────────────────

    def create(
        self,
        mission_id: str,
        mission_type: str,
        opportunity_id: str | None = None,
        workflow_id: str | None = None,
        priority: int = 0,
        expected_value_usd: float = 0.0,
        payload: dict | None = None,
        context: dict | None = None,
        total_stages: int = 0,
        max_retries: int = 3,
    ) -> MissionModel:
        """Crea una nueva misión."""
        session = self._get_session()
        try:
            mission = MissionModel(
                mission_id=mission_id,
                mission_type=mission_type,
                opportunity_id=opportunity_id,
                workflow_id=workflow_id,
                priority=priority,
                expected_value_usd=expected_value_usd,
                payload_json=json.dumps(payload or {}),
                context_json=json.dumps(context or {}),
                total_stages=total_stages,
                max_retries=max_retries,
                status=MissionStatus.PENDING.value,
            )
            session.add(mission)
            session.commit()
            session.refresh(mission)
            logger.info(f"[MISSION] Created {mission_id} ({mission_type})")
            return mission
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, mission_id: str) -> MissionModel | None:
        """Obtiene una misión por mission_id."""
        session = self._get_session()
        try:
            return session.query(MissionModel).filter(MissionModel.mission_id == mission_id).first()
        finally:
            session.close()

    def get_by_id(self, id: int) -> MissionModel | None:
        session = self._get_session()
        try:
            return session.query(MissionModel).filter(MissionModel.id == id).first()
        finally:
            session.close()

    def update(self, mission_id: str, **kwargs) -> MissionModel | None:
        """Actualiza campos de una misión."""
        session = self._get_session()
        try:
            mission = session.query(MissionModel).filter(MissionModel.mission_id == mission_id).first()
            if not mission:
                return None
            for key, value in kwargs.items():
                if hasattr(mission, key):
                    if key in ("payload", "context", "last_checkpoint") and isinstance(value, dict):
                        setattr(mission, f"{key}_json", json.dumps(value))
                    else:
                        setattr(mission, key, value)
            session.commit()
            session.refresh(mission)
            return mission
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, mission_id: str) -> bool:
        session = self._get_session()
        try:
            mission = session.query(MissionModel).filter(MissionModel.mission_id == mission_id).first()
            if not mission:
                return False
            session.delete(mission)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ── State transitions ──────────────────────────────────────────

    def start_mission(self, mission_id: str) -> MissionModel | None:
        """Marca misión como RUNNING."""
        return self.update(
            mission_id,
            status=MissionStatus.RUNNING.value,
            started_at=datetime.now(UTC),
            last_heartbeat=datetime.now(UTC),
        )

    def advance_stage(
        self,
        mission_id: str,
        stage: str,
        stage_order: int,
        result: dict | None = None,
        context_update: dict | None = None,
    ) -> MissionModel | None:
        """Avanza a la siguiente stage y guarda checkpoint."""
        mission = self.get(mission_id)
        if not mission:
            return None

        # Update context
        context = json.loads(mission.context_json) if mission.context_json else {}
        if context_update:
            context.update(context_update)

        # Build checkpoint
        checkpoint = {
            "stage": stage,
            "stage_order": stage_order,
            "result": result or {},
            "context": context,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        return self.update(
            mission_id,
            status=MissionStatus.RUNNING.value,
            current_stage=stage,
            stage_order=stage_order,
            context_json=json.dumps(context),
            last_checkpoint_json=json.dumps(checkpoint),
            last_heartbeat=datetime.now(UTC),
        )

    def complete_mission(
        self, mission_id: str, actual_value_usd: float = 0.0, result: dict | None = None
    ) -> MissionModel | None:
        """Marca misión como COMPLETED."""
        mission = self.get(mission_id)
        if not mission:
            return None
        context = json.loads(mission.context_json) if mission.context_json else {}
        context["final_result"] = result or {}
        return self.update(
            mission_id,
            status=MissionStatus.COMPLETED.value,
            completed_at=datetime.now(UTC),
            actual_value_usd=actual_value_usd,
            context_json=json.dumps(context),
        )

    def fail_mission(self, mission_id: str, error_message: str, error_state: str = "execution") -> MissionModel | None:
        """Marca misión como FAILED."""
        mission = self.get(mission_id)
        if not mission:
            return None

        new_retry = mission.retry_count + 1
        if new_retry >= mission.max_retries:
            status = MissionStatus.FAILED.value
        else:
            status = MissionStatus.PENDING.value  # will be retried

        return self.update(
            mission_id,
            status=status,
            retry_count=new_retry,
            error_state=error_state,
            error_message=error_message,
            last_heartbeat=datetime.now(UTC),
        )

    def block_mission(self, mission_id: str, reason: str) -> MissionModel | None:
        """Marca misión como BLOCKED (waiting human/external)."""
        return self.update(
            mission_id,
            status=MissionStatus.BLOCKED.value,
            error_state="blocked",
            error_message=reason,
            last_heartbeat=datetime.now(UTC),
        )

    def unblock_mission(self, mission_id: str) -> MissionModel | None:
        """Desbloquea una misión."""
        return self.update(
            mission_id,
            status=MissionStatus.RUNNING.value,
            error_state=None,
            error_message=None,
            last_heartbeat=datetime.now(UTC),
        )

    def heartbeat(self, mission_id: str) -> MissionModel | None:
        """Actualiza last_heartbeat."""
        return self.update(mission_id, last_heartbeat=datetime.now(UTC))

    # ── Checkpoints ────────────────────────────────────────────────

    def save_checkpoint(
        self,
        mission_id: str,
        stage: str,
        stage_order: int,
        result: dict,
        context: dict,
    ) -> MissionCheckpointModel:
        """Guarda un checkpoint persistente (historial completo)."""
        session = self._get_session()
        try:
            checkpoint = MissionCheckpointModel(
                mission_id=mission_id,
                stage=stage,
                stage_order=stage_order,
                result_json=json.dumps(result),
                context_json=json.dumps(context),
            )
            session.add(checkpoint)
            session.commit()
            session.refresh(checkpoint)
            return checkpoint
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_checkpoints(self, mission_id: str) -> list[MissionCheckpointModel]:
        """Obtiene todos los checkpoints de una misión."""
        session = self._get_session()
        try:
            return (
                session.query(MissionCheckpointModel)
                .filter(MissionCheckpointModel.mission_id == mission_id)
                .order_by(MissionCheckpointModel.stage_order)
                .all()
            )
        finally:
            session.close()

    def get_latest_checkpoint(self, mission_id: str) -> MissionCheckpointModel | None:
        """Obtiene el último checkpoint de una misión."""
        session = self._get_session()
        try:
            return (
                session.query(MissionCheckpointModel)
                .filter(MissionCheckpointModel.mission_id == mission_id)
                .order_by(MissionCheckpointModel.stage_order.desc())
                .first()
            )
        finally:
            session.close()

    # ── Queries operacionales ──────────────────────────────────────

    def get_active_missions(self) -> list[MissionModel]:
        """Misiones RUNNING, WAITING_HUMAN, WAITING_EXTERNAL, BLOCKED."""
        session = self._get_session()
        try:
            return (
                session.query(MissionModel)
                .filter(
                    MissionModel.status.in_(
                        [
                            MissionStatus.RUNNING.value,
                            MissionStatus.WAITING_HUMAN.value,
                            MissionStatus.WAITING_EXTERNAL.value,
                            MissionStatus.BLOCKED.value,
                        ]
                    )
                )
                .order_by(MissionModel.priority.desc(), MissionModel.updated_at.desc())
                .all()
            )
        finally:
            session.close()

    def get_missions_by_status(self, status: MissionStatus) -> list[MissionModel]:
        session = self._get_session()
        try:
            return session.query(MissionModel).filter(MissionModel.status == status.value).all()
        finally:
            session.close()

    def get_blocked_missions(self) -> list[MissionModel]:
        return self.get_missions_by_status(MissionStatus.BLOCKED)

    def get_waiting_human_missions(self) -> list[MissionModel]:
        return self.get_missions_by_status(MissionStatus.WAITING_HUMAN)

    def get_stale_missions(self, max_age_hours: float = 2.0) -> list[MissionModel]:
        """Misiones RUNNING sin heartbeat > max_age_hours."""
        session = self._get_session()
        try:
            cutoff = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
            return (
                session.query(MissionModel)
                .filter(
                    MissionModel.status == MissionStatus.RUNNING.value,
                    MissionModel.last_heartbeat.isnot(None),
                )
                .all()
            )
        finally:
            session.close()

    def get_missions_by_opportunity(self, opportunity_id: str) -> list[MissionModel]:
        session = self._get_session()
        try:
            return session.query(MissionModel).filter(MissionModel.opportunity_id == opportunity_id).all()
        finally:
            session.close()

    def get_missions_by_workflow(self, workflow_id: str) -> list[MissionModel]:
        session = self._get_session()
        try:
            return session.query(MissionModel).filter(MissionModel.workflow_id == workflow_id).all()
        finally:
            session.close()

    # ── Recovery ───────────────────────────────────────────────────

    def get_recoverable_missions(self, max_age_hours: float = 2.0) -> list[MissionModel]:
        """Misiones que pueden recuperarse (stale running o failed con retries)."""
        session = self._get_session()
        try:
            cutoff = datetime.now(UTC).timestamp() - (max_age_hours * 3600)
            missions = (
                session.query(MissionModel)
                .filter(
                    MissionModel.status.in_([MissionStatus.RUNNING.value, MissionStatus.FAILED.value]),
                    MissionModel.last_heartbeat.isnot(None),
                )
                .all()
            )
            return [m for m in missions if m.last_heartbeat and m.last_heartbeat.timestamp() < cutoff]
        finally:
            session.close()

    def restore_from_checkpoint(self, mission_id: str) -> MissionModel | None:
        """Restaura una misión desde su último checkpoint."""
        mission = self.get(mission_id)
        if not mission:
            return None

        checkpoint = self.get_latest_checkpoint(mission_id)
        if not checkpoint:
            return mission

        context = json.loads(checkpoint.context_json) if checkpoint.context_json else {}
        result = json.loads(checkpoint.result_json) if checkpoint.result_json else {}

        return self.update(
            mission_id,
            status=MissionStatus.RUNNING.value,
            current_stage=checkpoint.stage,
            stage_order=checkpoint.stage_order,
            context_json=json.dumps(context),
            last_heartbeat=datetime.now(UTC),
        )


# ── Singleton ──────────────────────────────────────────────────────

_mission_store: MissionStore | None = None


def get_mission_store() -> MissionStore:
    global _mission_store
    if _mission_store is None:
        _mission_store = MissionStore()
    return _mission_store
