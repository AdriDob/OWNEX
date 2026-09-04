"""Observability API — Unified monitoring and real-time visibility for OWNEX."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from core.observability.engine import ObservabilityEngine, get_obs_engine

logger = logging.getLogger("ownex.api.obs")

router = APIRouter(prefix="/api/obs", tags=["observability"])


class EmitEventRequest(BaseModel):
    event_type: str = Field(..., description="Event type")
    message: str = Field(..., description="Event message")
    severity: str = Field("info", description="Severity: info, warning, error, critical")
    source: str = Field("system", description="Source module")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event metadata")


class EmitMetricRequest(BaseModel):
    metric_name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    labels: dict[str, str] = Field(default_factory=dict, description="Metric labels")


def _get_engine() -> ObservabilityEngine:
    return get_obs_engine()


@router.post("/events")
async def emit_event(
    request: EmitEventRequest,
    engine: ObservabilityEngine = Depends(_get_engine),
) -> dict:
    """Emit an observability event."""
    return engine.emit(
        event_type=request.event_type,
        message=request.message,
        severity=request.severity,
        source=request.source,
        metadata=request.metadata,
    )


@router.get("/events")
async def get_events(
    event_type: str | None = Query(None, description="Filter by event type"),
    severity: str | None = Query(None, description="Filter by severity"),
    source: str | None = Query(None, description="Filter by source"),
    limit: int = Query(50, le=500, description="Limit results"),
    engine: ObservabilityEngine = Depends(_get_engine),
) -> list[dict]:
    """Query observability events."""
    return engine.get_events(
        event_type=event_type,
        severity=severity,
        source=source,
        limit=limit,
    )


@router.get("/dashboard")
async def get_dashboard(
    engine: ObservabilityEngine = Depends(_get_engine),
) -> dict:
    """Get complete dashboard snapshot (missions, revenue, sync, learning, self-repair)."""
    return engine.get_dashboard_snapshot()


@router.post("/metrics")
async def record_metric(
    request: EmitMetricRequest,
    engine: ObservabilityEngine = Depends(_get_engine),
) -> dict:
    """Record a metric value."""
    engine.record_metric(request.metric_name, request.value, request.labels)
    return {"status": "recorded"}


@router.get("/metrics")
async def get_metrics(
    metric_name: str | None = Query(None, description="Filter by metric name"),
    limit: int = Query(100, le=1000, description="Limit results"),
    engine: ObservabilityEngine = Depends(_get_engine),
) -> list[dict]:
    """Get metrics."""
    return engine.get_metrics(metric_name=metric_name, limit=limit)


@router.get("/health")
async def health(
    engine: ObservabilityEngine = Depends(_get_engine),
) -> dict:
    """Observability system health check."""
    return {
        "status": "ok",
        "engine": "observability",
        "events_buffer_size": len(engine._event_buffer),
    }
