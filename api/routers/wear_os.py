"""API Router for Wear OS Integration."""

from typing import Any

from fastapi import APIRouter, HTTPException

from cores.wear_os.integration import (
    WatchNotificationLevel,
    get_wear_os_integration,
)

router = APIRouter(prefix="/wear-os", tags=["wear-os"])


@router.get("/status")
async def get_watch_status():
    """Get watch status."""
    integration = get_wear_os_integration()
    status = integration.get_status()
    return status.__dict__


@router.post("/notification")
async def send_notification(payload: dict[str, Any]):
    """Send notification to watch."""
    integration = get_wear_os_integration()

    title = payload.get("title")
    message = payload.get("message")
    level = WatchNotificationLevel(payload.get("level", "medium"))
    requires_action = payload.get("requires_action", False)
    action_type = payload.get("action_type")

    if not title or not message:
        raise HTTPException(status_code=400, detail="title and message are required")

    notification = integration.send_notification(
        title=title,
        message=message,
        level=level,
        requires_action=requires_action,
        action_type=action_type,
    )

    return notification.__dict__


@router.get("/notifications")
async def get_notifications(
    level: str | None = None,
    unread_only: bool = False,
    limit: int = 20,
):
    """Get watch notifications."""
    integration = get_wear_os_integration()

    notification_level = WatchNotificationLevel(level) if level else None
    notifications = integration.get_notifications(
        level=notification_level,
        unread_only=unread_only,
        limit=limit,
    )

    return [n.__dict__ for n in notifications]


@router.put("/notification/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    """Mark notification as read."""
    integration = get_wear_os_integration()
    success = integration.mark_notification_read(notification_id)

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True}


@router.post("/approval-request")
async def request_approval(payload: dict[str, Any]):
    """Request approval from watch."""
    integration = get_wear_os_integration()

    title = payload.get("title")
    description = payload.get("description")
    workflow_id = payload.get("workflow_id")

    if not title or not description:
        raise HTTPException(status_code=400, detail="title and description are required")

    request = integration.request_approval(
        title=title,
        description=description,
        workflow_id=workflow_id,
    )

    return request.__dict__


@router.get("/approvals/pending")
async def get_pending_approvals():
    """Get pending approvals."""
    integration = get_wear_os_integration()
    approvals = integration.get_pending_approvals()
    return [a.__dict__ for a in approvals]


@router.post("/approval/{request_id}/respond")
async def respond_approval(request_id: str, payload: dict[str, Any]):
    """Respond to approval request."""
    integration = get_wear_os_integration()

    approved = payload.get("approved")
    if approved is None:
        raise HTTPException(status_code=400, detail="approved is required")

    success = integration.respond_approval(request_id, approved)

    if not success:
        raise HTTPException(status_code=404, detail="Approval request not found")

    return {"success": True, "approved": approved}


@router.post("/clear-notifications")
async def clear_old_notifications(payload: dict[str, Any]):
    """Clear old notifications."""
    integration = get_wear_os_integration()

    days = payload.get("days", 7)
    cleared = integration.clear_old_notifications(days)

    return {"success": True, "cleared_count": cleared}
