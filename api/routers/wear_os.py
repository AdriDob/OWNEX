"""Wear OS Router — minimal endpoints for watch companion.

Endpoints:
- GET  /wear-os/notifications     — Get watch notifications
- POST /wear-os/notification      — Send notification to watch
- PUT  /wear-os/notification/:id/read — Mark as read
- GET  /wear-os/approvals         — Get pending approvals
- POST /wear-os/approval/:id      — Respond to approval
- GET  /wear-os/status            — System status for watch
- POST /wear-os/clear-notifications — Clear old notifications
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cores.wear_os.integration import (
    WatchNotificationLevel,
    get_wear_os_integration,
)

logger = logging.getLogger("ownex.api.wear_os")

router = APIRouter(prefix="/wear-os", tags=["wear_os"])


# ── Request Models ────────────────────────────────────────────────────────


class SendNotificationRequest(BaseModel):
    title: str
    message: str
    level: str = "medium"
    requires_action: bool = False
    action_type: str | None = None


class ApprovalResponseRequest(BaseModel):
    approved: bool


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/notifications")
def get_notifications(
    level: str | None = Query(None, description="Filter by level"),
    unread_only: bool = Query(False, description="Only unread"),
    limit: int = Query(20, ge=1, le=50),
) -> list[dict[str, Any]]:
    """Get watch notifications."""
    integration = get_wear_os_integration()

    watch_level = None
    if level:
        try:
            watch_level = WatchNotificationLevel(level)
        except ValueError:
            pass

    notifications = integration.get_notifications(level=watch_level, unread_only=unread_only, limit=limit)
    return [
        {
            "notification_id": n.notification_id,
            "title": n.title,
            "message": n.message,
            "level": n.level,
            "created_at": n.created_at,
            "read": n.read,
            "requires_action": n.requires_action,
            "action_type": n.action_type,
        }
        for n in notifications
    ]


@router.post("/notification")
def send_notification(body: SendNotificationRequest) -> dict[str, Any]:
    """Send a notification to the watch."""
    integration = get_wear_os_integration()

    try:
        level = WatchNotificationLevel(body.level)
    except ValueError:
        level = WatchNotificationLevel.MEDIUM

    notification = integration.send_notification(
        title=body.title,
        message=body.message,
        level=level,
        requires_action=body.requires_action,
        action_type=body.action_type,
    )

    return {
        "success": True,
        "notification_id": notification.notification_id,
    }


@router.put("/notification/{notification_id}/read")
def mark_notification_read(notification_id: str) -> dict[str, str]:
    """Mark a watch notification as read."""
    integration = get_wear_os_integration()
    if not integration.mark_notification_read(notification_id):
        raise HTTPException(404, "Notification not found")
    return {"status": "ok"}


@router.get("/approvals")
def get_pending_approvals() -> list[dict[str, Any]]:
    """Get pending approval requests."""
    integration = get_wear_os_integration()
    approvals = integration.get_pending_approvals()
    return [
        {
            "request_id": a.request_id,
            "title": a.title,
            "description": a.description,
            "workflow_id": a.workflow_id,
            "created_at": a.created_at,
            "responded": a.responded,
            "approved": a.approved,
        }
        for a in approvals
    ]


@router.post("/approval/{request_id}")
def respond_approval(request_id: str, body: ApprovalResponseRequest) -> dict[str, str]:
    """Respond to an approval request."""
    integration = get_wear_os_integration()
    if not integration.respond_approval(request_id, body.approved):
        raise HTTPException(404, "Approval request not found")
    return {"status": "ok"}


@router.get("/status")
def get_status() -> dict[str, Any]:
    """Get system status for watch display."""
    integration = get_wear_os_integration()
    status = integration.get_status()
    return {
        "system_online": status.system_online,
        "scheduler_running": status.scheduler_running,
        "active_workflows": status.active_workflows,
        "pending_approvals": status.pending_approvals,
        "findings_total": status.findings_total,
        "findings_confirmed": status.findings_confirmed,
        "targets_active": status.targets_active,
        "health_score": status.health_score,
        "last_updated": status.last_updated,
    }


@router.post("/clear-notifications")
def clear_notifications(days: int = Query(7, ge=1, le=30)) -> dict[str, Any]:
    """Clear old watch notifications."""
    integration = get_wear_os_integration()
    cleared = integration.clear_old_notifications(days=days)
    return {"success": True, "cleared_count": cleared}
