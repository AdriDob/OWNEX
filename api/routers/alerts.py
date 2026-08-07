"""Alerts API — Endpoints for real-time alert system.

Endpoints:
- GET /api/alerts/status — Current alert system status
- GET /api/alerts/active — Get all active alerts
- POST /api/alerts/create — Create a new alert
- POST /api/alerts/resolve — Resolve an alert
- GET /api/alerts/category/{category} — Get alerts by category
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.financial_intelligence.alert_system import (
    AlertCategory,
    AlertType,
    get_alert_system,
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)


class CreateAlertRequest(BaseModel):
    """Request model for creating an alert."""

    type: str = Field(..., description="Alert type: error, warning, info, success, critical")
    category: str = Field(..., description="Alert category")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: str = Field(default="info", description="Severity: info, warning, error, critical")
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    requires_action: bool = Field(default=False, description="Whether action is required")
    action_steps: list[str] = Field(default_factory=list, description="Steps to resolve")
    ui_path: str = Field(default="", description="UI path to resolve")
    auto_dismiss_after: int = Field(default=0, description="Auto-dismiss after N seconds (0 = no auto-dismiss)")


class ResolveAlertRequest(BaseModel):
    """Request model for resolving an alert."""

    alert_id: str = Field(..., description="Alert ID to resolve")


@router.get("/status")
async def get_alert_status() -> dict[str, Any]:
    """Get current alert system status."""
    try:
        alert_system = get_alert_system()
        return alert_system.get_status()
    except Exception as e:
        logger.error(f"Failed to get alert status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert status: {str(e)}") from e


@router.get("/active")
async def get_active_alerts(include_resolved: bool = False) -> dict[str, Any]:
    """Get all active alerts."""
    try:
        alert_system = get_alert_system()
        alerts = alert_system.get_active_alerts(include_resolved=include_resolved)
        return {
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
        }
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}") from e


@router.post("/create")
async def create_alert(request: CreateAlertRequest) -> dict[str, Any]:
    """Create a new alert."""
    try:
        alert_system = get_alert_system()
        alert = alert_system.create_alert(
            type=AlertType(request.type),
            category=AlertCategory(request.category),
            title=request.title,
            message=request.message,
            severity=request.severity,
            priority=request.priority,
            requires_action=request.requires_action,
            action_steps=request.action_steps,
            ui_path=request.ui_path,
            auto_dismiss_after=request.auto_dismiss_after,
        )
        return {
            "status": "alert_created",
            "alert": alert.to_dict(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}") from e


@router.post("/resolve")
async def resolve_alert(request: ResolveAlertRequest) -> dict[str, Any]:
    """Resolve an alert."""
    try:
        alert_system = get_alert_system()
        alert = alert_system.resolve_alert(request.alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert not found: {request.alert_id}")
        return {
            "status": "alert_resolved",
            "alert": alert.to_dict(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}") from e


@router.get("/category/{category}")
async def get_alerts_by_category(category: str) -> dict[str, Any]:
    """Get alerts by category."""
    try:
        alert_system = get_alert_system()
        try:
            cat = AlertCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}") from None

        alerts = alert_system.get_alerts_by_category(cat)
        return {
            "category": category,
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alerts by category: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts by category: {str(e)}") from e
