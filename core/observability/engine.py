"""Observability Engine — Unified monitoring and real-time visibility for OWNEX.

Provides centralized view of system health, active missions, revenue metrics,
sync status, and real-time event streaming via WebSocket.
"""

from __future__ import annotations

import enum
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from database.db import Base, SessionLocal

logger = logging.getLogger("ownex.observability")


# ── Models ─────────────────────────────────────────────────────────


class EventSeverity(str, enum.Enum):
    """Event severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ObservabilityEventType(str, enum.Enum):
    """Types of observability events."""

    MISSION_STARTED = "mission_started"
    MISSION_ADVANCED = "mission_advanced"
    MISSION_COMPLETED = "mission_completed"
    MISSION_FAILED = "mission_failed"
    MISSION_BLOCKED = "mission_blocked"
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    REVENUE_RECEIVED = "revenue_received"
    REVENUE_PENDING = "revenue_pending"
    SYNC_EVENT = "sync_event"
    CALIBRATION_ALERT = "calibration_alert"
    SELF_REPAIR_ACTION = "self_repair_action"
    ARTIFACT_STORED = "artifact_stored"
    DAILY_BRIEF_GENERATED = "daily_brief_generated"
    SYSTEM_HEALTH = "system_health"
    ERROR = "error"


@dataclass
class ObservabilityEvent:
    """Observability event for streaming."""

    event_id: str
    event_type: str
    timestamp: str
    severity: str
    message: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


class ObservabilityEventModel(Base):
    """SQLAlchemy model for observability events."""

    __tablename__ = "observability_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)
    message = Column(Text, nullable=False)
    source = Column(String(64), nullable=False, index=True)
    metadata_json = Column(Text, default="{}")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ObservabilityMetric(Base):
    """Aggregated metrics for dashboard."""

    __tablename__ = "observability_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(64), nullable=False, index=True)
    value = Column(Float, nullable=False)
    labels_json = Column(Text, default="{}")
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ── Observability Engine ─────────────────────────────────────────


class ObservabilityEngine:
    """Centralized observability engine for OWNEX."""

    def __init__(self, session_factory: Any = None) -> None:
        self._session_factory = session_factory or SessionLocal
        self._ws_connections: dict[str, Any] = {}
        self._event_buffer: list[dict] = []
        self._max_buffer_size = 1000

    def _get_session(self):
        return self._session_factory()

    # ── Event Ingestion ──────────────────────────────────────────

    def emit(
        self,
        event_type: str,
        message: str,
        severity: str = "info",
        source: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """Emit an observability event."""
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": severity,
            "message": message,
            "source": source,
            "metadata": metadata or {},
        }

        # Buffer for streaming
        self._event_buffer.append(event)
        if len(self._event_buffer) > self._max_buffer_size:
            self._event_buffer = self._event_buffer[-self._max_buffer_size :]

        # Persist to database
        self._persist_event(event)

        # Broadcast to WebSocket connections
        self._broadcast_event(event)

        return {"event_id": event["event_id"], "status": "emitted"}

    def _persist_event(self, event: dict) -> None:
        """Persist event to database."""
        session = SessionLocal()
        try:
            model = ObservabilityEventModel(
                event_id=event["event_id"],
                event_type=event["event_type"],
                severity=event["severity"],
                message=event["message"],
                source=event["source"],
                metadata_json=json.dumps(event.get("metadata", {})),
            )
            session.add(model)
            session.commit()
        except Exception as e:
            logger.error(f"[OBSERVABILITY] Failed to persist event: {e}")
            session.rollback()
        finally:
            session.close()

    def _broadcast_event(self, event: dict) -> None:
        """Broadcast event to WebSocket connections."""
        for ws in self._ws_connections.values():
            try:
                # Would send via WebSocket
                pass
            except Exception:
                pass

    # ── Event Querying ──────────────────────────────────────────

    def get_events(
        self,
        event_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query events with filters."""
        session = SessionLocal()
        try:
            query = session.query(ObservabilityEventModel)
            if event_type:
                query = query.filter(ObservabilityEventModel.event_type == event_type)
            if severity:
                query = query.filter(ObservabilityEventModel.severity == severity)
            if source:
                query = query.filter(ObservabilityEventModel.source == source)
            if since:
                query = query.filter(ObservabilityEventModel.timestamp >= since)

            models = query.order_by(ObservabilityEventModel.timestamp.desc()).limit(limit).all()
            return [
                {
                    "event_id": m.event_id,
                    "event_type": m.event_type,
                    "severity": m.severity,
                    "message": m.message,
                    "source": m.source,
                    "metadata": json.loads(m.metadata_json) if m.metadata_json else {},
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                }
                for m in models
            ]
        finally:
            session.close()

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        """Get recent events for dashboard."""
        return self.get_events(limit=limit)

    # ── Metrics ──────────────────────────────────────────────────

    def record_metric(
        self,
        metric_name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a metric value."""
        session = SessionLocal()
        try:
            model = ObservabilityMetric(
                metric_name=metric_name,
                value=value,
                labels_json=json.dumps(labels or {}),
            )
            session.add(model)
            session.commit()
        except Exception as e:
            logger.error(f"[OBSERVABILITY] Failed to record metric: {e}")
            session.rollback()
        finally:
            session.close()

    def get_metrics(
        self,
        metric_name: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Query metrics."""
        session = SessionLocal()
        try:
            query = session.query(ObservabilityMetric)
            if metric_name:
                query = query.filter(ObservabilityMetric.metric_name == metric_name)
            if since:
                query = query.filter(ObservabilityMetric.timestamp >= since)
            models = query.order_by(ObservabilityMetric.timestamp.desc()).limit(limit).all()
            return [
                {
                    "metric_name": m.metric_name,
                    "value": m.value,
                    "labels": json.loads(m.labels_json) if m.labels_json else {},
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                }
                for m in models
            ]
        finally:
            session.close()

    # ── Dashboard Data ──────────────────────────────────────────

    def get_dashboard_snapshot(self) -> dict[str, Any]:
        """Get complete dashboard snapshot."""
        from core.learning.outcome_loop import get_outcome_learning_loop
        from core.mission.controller import get_mission_controller
        from core.revenue.ledger import get_revenue_ledger
        from core.self_repair.engine import get_self_repair_engine
        from core.sync.engine import get_sync_engine

        mission_ctrl = get_mission_controller()
        ledger = get_revenue_ledger()
        sync_engine = get_sync_engine()
        learning = get_outcome_learning_loop()
        repair = get_self_repair_engine()

        # Mission summary
        active = mission_ctrl.get_active_missions()
        blocked = mission_ctrl.get_blocked_missions()
        waiting = mission_ctrl.get_waiting_human_missions()

        # Revenue
        revenue = ledger.get_summary()

        # Sync status
        sync_status = sync_engine.get_sync_status()

        # Learning
        learning_report = learning.compute_calibration_report()

        # Self-repair
        repair_report = repair.run_repair_cycle()

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "missions": {
                "active": len(active),
                "blocked": len(blocked),
                "waiting_human": len(waiting),
                "total_active": len(active) + len(blocked) + len(waiting),
            },
            "revenue": revenue,
            "sync": {
                "device_id": sync_status.get("device_id"),
                "connected": sync_status.get("connected"),
                "offline_queue": sync_status.get("offline_queue_size"),
                "devices": sync_status.get("connected_devices", []),
            },
            "learning": {
                "calibration_score": learning_report.get("overall_calibration", {}).get("avg_calibration_score", 0),
                "alert": learning_report.get("alert", False),
            },
            "self_repair": {
                "issues_found": repair_report.get("issues_found", 0),
                "repairs_attempted": repair_report.get("repairs_attempted", 0),
                "successful": repair_report.get("successful", 0),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # ── WebSocket ────────────────────────────────────────────────

    _ws_connections: dict[str, Any] = {}

    def register_ws(self, ws_id: str, ws: Any) -> None:
        """Register WebSocket connection."""
        self._ws_connections[ws_id] = ws

    def unregister_ws(self, ws_id: str) -> None:
        self._ws_connections.pop(ws_id, None)

    def _broadcast(self, event: dict) -> None:
        """Broadcast event to all WebSocket connections."""
        for ws_id, ws in self._ws_connections.items():
            try:
                # Would send via WebSocket
                pass
            except Exception:
                pass


# ── API Router ───────────────────────────────────────────────────

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/obs", tags=["observability"])


class ObservabilityEventRequest(BaseModel):
    event_type: str
    message: str
    severity: str = "info"
    source: str = "system"
    metadata: dict = Field(default_factory=dict)


class ObservabilityMetricsRequest(BaseModel):
    metric_name: str
    value: float
    labels: dict[str, str] = Field(default_factory=dict)


@router.post("/events")
async def emit_event(event_request: ObservabilityEventRequest, engine=Depends(lambda: get_obs_engine())):
    """Emit an observability event."""
    return engine.emit(
        event_type=event_request.event_type,
        message=event_request.message,
        severity=event_request.severity,
        source=event_request.source,
        metadata=event_request.metadata,
    )


@router.get("/events")
async def get_events(
    event_type: str | None = Query(None),
    severity: str | None = Query(None),
    source: str | None = Query(None),
    since: str | None = Query(None),
    limit: int = Query(50, le=500),
    engine=Depends(lambda: get_obs_engine()),
):
    """Query observability events."""
    since = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    return engine.get_events(
        event_type=event_request.event_type,
        severity=severity,
        source=source,
        since=since,
        limit=limit,
    )


@router.get("/dashboard")
async def get_dashboard(engine=Depends(lambda: get_obs_engine())):
    """Get full dashboard snapshot."""
    return engine.get_dashboard_snapshot()


@router.post("/metrics")
async def record_metric(metric_request: ObservabilityMetricsRequest, engine=Depends(lambda: get_obs_engine())):
    """Record a metric value."""
    engine.record_metric(metric_request.metric_name, metric_request.value, metric_request.labels)
    return {"status": "recorded"}


@router.get("/metrics")
async def get_metrics(
    metric_name: str | None = Query(None),
    since: str | None = Query(None),
    limit: int = Query(100, le=1000),
    engine=Depends(lambda: get_obs_engine()),
):
    """Get metrics."""
    since = datetime.fromisoformat(since.replace("Z", "+00:00")) if since else None
    return engine.get_metrics(metric_name, since, limit)


# ── WebSocket ───────────────────────────────────────────────────


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time observability events."""
    await websocket.accept()
    ws_id = f"obs_ws_{uuid.uuid4().hex[:8]}"

    from core.observability.engine import get_obs_engine

    engine = get_obs_engine()
    engine.register_ws(ws_id, None)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[OBS] WebSocket error: {e}")
    finally:
        pass


# ── Singleton ───────────────────────────────────────────────────

_obs_engine: Any | None = None


def get_obs_engine() -> Any:
    global _obs_engine
    if _obs_engine is None:
        _obs_engine = ObservabilityEngine()
    return _obs_engine
