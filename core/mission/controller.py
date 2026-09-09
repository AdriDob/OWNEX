"""Mission Controller — Autoridad central del estado operacional de OWNEX.

El MissionController es el único punto de verdad para:
- Qué misiones está ejecutando OWNEX
- En qué stage está cada una
- Qué falló y por qué
- Qué necesita del usuario
- Qué hacer después
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from core.events.event_bus import get_core_event_bus
from core.mission.store import (
    MissionModel,
    MissionType,
    get_mission_store,
)

logger = logging.getLogger("ownex.mission.controller")


@dataclass
class MissionResult:
    """Resultado de una operación de misión."""

    success: bool
    mission: MissionModel | None = None
    message: str = ""
    error: str | None = None


class MissionController:
    """Controlador central de misiones OWNEX."""

    def __init__(self, store: Any = None) -> None:
        self.store = store or get_mission_store()
        self._bus = get_core_event_bus()

    # ── Mission Lifecycle ────────────────────────────────────────

    def create_mission(
        self,
        mission_type: str | MissionType,
        opportunity_id: str | None = None,
        workflow_id: str | None = None,
        priority: int = 0,
        expected_value_usd: float = 0.0,
        payload: dict | None = None,
        context: dict | None = None,
        total_stages: int = 0,
        max_retries: int = 3,
        mission_id: str | None = None,
    ) -> MissionResult:
        """Crea una nueva misión."""
        m_id = (
            mission_id
            or f"{mission_type.value if isinstance(mission_type, MissionType) else mission_type}_{uuid.uuid4().hex[:8]}"
        )
        m_type = mission_type if isinstance(mission_type, MissionType) else MissionType(mission_type)

        mission = self.store.create(
            mission_id=m_id,
            mission_type=m_type.value,
            opportunity_id=opportunity_id,
            workflow_id=workflow_id,
            priority=priority,
            expected_value_usd=expected_value_usd,
            payload=payload,
            context=context,
            total_stages=total_stages,
            max_retries=max_retries,
        )

        self._emit("mission:created", mission.mission_id, mission_type=m_type.value, opportunity_id=opportunity_id)
        return MissionResult(True, mission, f"Mission {mission.mission_id} created")

    def start_mission(self, mission_id: str) -> MissionResult:
        """Inicia una misión (PENDING → RUNNING)."""
        mission = self.store.start_mission(mission_id)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")

        self._emit("mission:started", mission_id, stage=mission.current_stage)
        return MissionResult(True, mission, f"Mission {mission_id} started")

    def advance_stage(
        self,
        mission_id: str,
        stage: str,
        stage_order: int,
        result: dict | None = None,
        context_update: dict | None = None,
    ) -> MissionResult:
        """Avanza a la siguiente stage y guarda checkpoint."""
        mission = self.store.advance_stage(mission_id, stage, stage_order, result, context_update)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")

        self._emit(
            "mission:stage_advanced",
            mission_id,
            stage=stage,
            stage_order=stage_order,
            result=result,
        )
        return MissionResult(True, mission, f"Advanced to {stage}")

    def complete_mission(
        self, mission_id: str, actual_value_usd: float = 0.0, result: dict | None = None
    ) -> MissionResult:
        """Completa una misión (RUNNING → COMPLETED)."""
        mission = self.store.complete_mission(mission_id, actual_value_usd, result)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")

        self._emit("mission:completed", str(mission_id), actual_value_usd=actual_value_usd, result=result)
        return MissionResult(True, mission, f"Mission {mission_id} completed")

    def fail_mission(self, mission_id: str, error_message: str, error_state: str = "execution") -> MissionResult:
        """Marca misión como FAILED (con retry logic)."""
        mission = self.store.fail_mission(mission_id, error_message, error_state)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")

        self._emit("mission:failed", mission_id, error=error_message, retry_count=mission.retry_count)
        return MissionResult(True, mission, f"Mission {mission_id} failed: {error_message}")

    def block_mission(self, mission_id: str, reason: str) -> MissionResult:
        """Bloquea misión esperando intervención humana/externa."""
        mission = self.store.block_mission(mission_id, reason)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")

        self._emit("mission:blocked", mission_id, reason=reason)
        return MissionResult(True, mission, f"Mission {mission_id} blocked: {reason}")

    def unblock_mission(self, mission_id: str) -> MissionResult:
        """Desbloquea una misión."""
        mission = self.store.unblock_mission(mission_id)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")

        self._emit("mission:unblocked", mission_id)
        return MissionResult(True, mission, f"Mission {mission_id} unblocked")

    def heartbeat(self, mission_id: str) -> MissionResult:
        """Actualiza heartbeat de una misión."""
        mission = self.store.heartbeat(mission_id)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")
        return MissionResult(True, mission, "Heartbeat updated")

    # ── Checkpoints & Recovery ──────────────────────────────────

    def checkpoint(
        self,
        mission_id: str,
        stage: str,
        stage_order: int,
        result: dict,
        context: dict,
    ) -> MissionResult:
        """Guarda checkpoint persistente."""
        mission = self.store.get(mission_id)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")

        self.store.save_checkpoint(mission_id, stage, stage_order, result, context)
        self._emit("mission:checkpoint", mission_id, stage=stage, stage_order=stage_order)
        return MissionResult(True, mission, f"Checkpoint saved for {stage}")

    def restore_from_checkpoint(self, mission_id: str) -> MissionResult:
        """Restaura misión desde último checkpoint."""
        mission = self.store.restore_from_checkpoint(mission_id)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found or no checkpoint")

        self._emit("mission:restored", mission_id, stage=mission.current_stage)
        return MissionResult(True, mission, f"Restored from checkpoint at {mission.current_stage}")

    def recover_stale_missions(self, max_age_hours: float = 2.0) -> list[MissionModel]:
        """Recupera misiones stale (sin heartbeat > max_age_hours)."""
        stale = self.store.get_recoverable_missions(max_age_hours)
        recovered = []
        for mission in stale:
            logger.warning(f"[MISSION] Recovering stale mission {mission.mission_id} (stage: {mission.current_stage})")
            self._emit("mission:recovering", mission.mission_id, last_stage=mission.current_stage)
            # Restore from checkpoint
            self.store.restore_from_checkpoint(mission.mission_id)
            # Re-emit as running
            self._emit("mission:restarted", mission.mission_id, stage=mission.current_stage)
            recovered.append(mission)
        return recovered

    # ── Queries ──────────────────────────────────────────────────

    def get_mission(self, mission_id: str) -> MissionModel | None:
        return self.store.get(mission_id)

    def get_status(self, mission_id: str) -> MissionResult:
        mission = self.store.get(mission_id)
        if not mission:
            return MissionResult(False, None, "", f"Mission {mission_id} not found")
        return MissionResult(True, mission)

    def get_active_missions(self) -> list[MissionModel]:
        return self.store.get_active_missions()

    def get_blocked_missions(self) -> list[MissionModel]:
        return self.store.get_blocked_missions()

    def get_waiting_human_missions(self) -> list[MissionModel]:
        return self.store.get_waiting_human_missions()

    def get_stale_missions(self, max_age_hours: float = 2.0) -> list[MissionModel]:
        return self.store.get_stale_missions(max_age_hours)

    def get_missions_by_opportunity(self, opportunity_id: str) -> list[MissionModel]:
        return self.store.get_missions_by_opportunity(opportunity_id)

    def get_missions_by_workflow(self, workflow_id: str) -> list[MissionModel]:
        return self.store.get_missions_by_workflow(workflow_id)

    def get_all_missions(self) -> list[MissionModel]:
        """Todas las misiones (para dashboard)."""
        session = self.store._get_session()
        try:
            return session.query(MissionModel).order_by(MissionModel.updated_at.desc()).limit(100).all()
        finally:
            session.close()

    def get_mission_summary(self) -> dict[str, Any]:
        """Resumen para dashboard."""
        active = self.get_active_missions()
        blocked = self.get_blocked_missions()
        waiting = self.get_waiting_human_missions()
        stale = self.get_stale_missions()

        return {
            "active_count": len(active),
            "blocked_count": len(blocked),
            "waiting_human_count": len(waiting),
            "stale_count": len(stale),
            "by_status": {
                "running": len([m for m in active if m.status == "running"]),
                "waiting_human": len([m for m in active if m.status == "waiting_human"]),
                "waiting_external": len([m for m in active if m.status == "waiting_external"]),
                "blocked": len(blocked),
            },
            "stale_missions": [
                {
                    "mission_id": m.mission_id,
                    "stage": m.current_stage,
                    "last_heartbeat": m.last_heartbeat.isoformat() if m.last_heartbeat else None,
                }
                for m in stale
            ],
        }

    # ── Event emission ──────────────────────────────────────────

    def _emit(self, event: str, mission_id: Any, **data: Any) -> None:
        self._bus.publish(event, mission_id=str(mission_id), **data)


# ── Singleton ────────────────────────────────────────────────────

_mission_controller: MissionController | None = None


def get_mission_controller() -> MissionController:
    global _mission_controller
    if _mission_controller is None:
        _mission_controller = MissionController()
    return _mission_controller
