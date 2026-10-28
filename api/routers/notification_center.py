"""Notification Center API — unified notification management.

Endpoints:
- GET /api/notifications/center — Get notifications with filtering
- GET /api/notifications/center/stats — Get notification statistics
- PUT /api/notifications/center/{id}/read — Mark notification as read
- PUT /api/notifications/center/read-all — Mark all as read
- PUT /api/notifications/center/{id}/resolve — Mark notification as resolved
- DELETE /api/notifications/center/{id} — Delete notification
- DELETE /api/notifications/center — Clear all notifications
- GET /api/notifications/center/preferences — Get user preferences
- PUT /api/notifications/center/preferences — Update user preferences
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cores.notifications.engine import (
    NotificationCategory,
    get_notification_engine,
)

logger = logging.getLogger("ownex.api.notifications")

router = APIRouter(prefix="/api/notifications/center", tags=["notification_center"])


# ── Request/Response Models ────────────────────────────────────────


class MarkReadRequest(BaseModel):
    """Request to mark notification as read."""

    pass


class MarkAllReadRequest(BaseModel):
    """Request to mark all notifications as read."""

    pass


class ResolveRequest(BaseModel):
    """Request to mark notification as resolved."""

    pass


class PreferencesRequest(BaseModel):
    """Request to update notification preferences."""

    desktop_enabled: bool | None = None
    mobile_enabled: bool | None = None
    watch_enabled: bool | None = None
    email_enabled: bool | None = None
    critical_enabled: bool | None = None
    high_enabled: bool | None = None
    medium_enabled: bool | None = None
    low_enabled: bool | None = None
    info_enabled: bool | None = None
    daily_briefing_enabled: bool | None = None
    monthly_report_enabled: bool | None = None
    monthly_report_email: str | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    quiet_hours_allow_critical: bool | None = None
    grouping_enabled: bool | None = None
    grouping_window_seconds: int | None = None
    sound_enabled: bool | None = None
    vibration_enabled: bool | None = None
    badge_enabled: bool | None = None
    retention_days: int | None = None


class NotificationResponse(BaseModel):
    """Response for a single notification."""

    id: str
    type: str
    title: str
    message: str
    priority: str
    severity: str
    category: str
    created_at: str
    read_at: str | None
    resolved_at: str | None
    expires_at: str | None
    source: str
    source_id: str
    entity_type: str
    entity_id: str
    action_label: str
    action_route: str
    action_payload: dict[str, Any]
    channels: list[str]
    group_key: str
    group_count: int
    read: bool
    resolved: bool
    starred: bool
    metadata: dict[str, Any]
    tags: list[str]


class NotificationsListResponse(BaseModel):
    """Response for notifications list."""

    notifications: list[NotificationResponse]
    total: int
    unread: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    """Response for notification statistics."""

    total: int
    unread: int
    resolved: int
    by_priority: dict[str, int]
    by_category: dict[str, int]


class PreferencesResponse(BaseModel):
    """Response for notification preferences."""

    desktop_enabled: bool
    mobile_enabled: bool
    watch_enabled: bool
    email_enabled: bool
    critical_enabled: bool
    high_enabled: bool
    medium_enabled: bool
    low_enabled: bool
    info_enabled: bool
    daily_briefing_enabled: bool
    monthly_report_enabled: bool
    monthly_report_email: str
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    quiet_hours_allow_critical: bool
    grouping_enabled: bool
    grouping_window_seconds: int
    sound_enabled: bool
    vibration_enabled: bool
    badge_enabled: bool
    retention_days: int


# ── Endpoints ─────────────────────────────────────────────────────


@router.get("")
async def get_notifications(
    category: str = Query("all", description="Filter by category"),
    limit: int = Query(50, ge=1, le=200, description="Number of notifications to return"),
    page: int = Query(1, ge=1, description="Page number"),
) -> NotificationsListResponse:
    """Get notifications with filtering and pagination."""
    engine = get_notification_engine()

    # Parse category
    try:
        cat = NotificationCategory(category)
    except ValueError:
        cat = NotificationCategory.ALL

    # Calculate offset
    offset = (page - 1) * limit

    # Get notifications
    notifications = engine.get_notifications(category=cat, limit=limit, offset=offset)

    # Get total count
    all_notifications = engine.get_notifications(category=cat, limit=10000)
    total = len(all_notifications)
    unread = engine.get_unread_count()

    return NotificationsListResponse(
        notifications=[NotificationResponse(**n.to_dict()) for n in notifications],
        total=total,
        unread=unread,
        page=page,
        page_size=limit,
    )


@router.get("/stats")
async def get_stats() -> StatsResponse:
    """Get notification statistics."""
    engine = get_notification_engine()
    stats = engine.get_stats()

    return StatsResponse(
        total=stats["total"],
        unread=stats["unread"],
        resolved=stats["resolved"],
        by_priority=stats["by_priority"],
        by_category=stats["by_category"],
    )


@router.put("/{notification_id}/read")
async def mark_read(notification_id: str) -> dict[str, str]:
    """Mark a notification as read."""
    engine = get_notification_engine()

    if not engine.mark_read(notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "ok", "message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_read() -> dict[str, Any]:
    """Mark all notifications as read."""
    engine = get_notification_engine()
    count = engine.mark_all_read()

    return {"status": "ok", "message": f"Marked {count} notifications as read", "count": count}


@router.put("/{notification_id}/resolve")
async def resolve(notification_id: str) -> dict[str, str]:
    """Mark a notification as resolved."""
    engine = get_notification_engine()

    if not engine.resolve(notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "ok", "message": "Notification resolved"}


@router.delete("/{notification_id}")
async def delete(notification_id: str) -> dict[str, str]:
    """Delete a notification."""
    engine = get_notification_engine()

    if not engine.remove(notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"status": "ok", "message": "Notification deleted"}


@router.delete("")
async def clear_all() -> dict[str, Any]:
    """Clear all notifications."""
    engine = get_notification_engine()
    count = engine.clear_all()

    return {"status": "ok", "message": f"Cleared {count} notifications", "count": count}


@router.get("/preferences")
async def get_preferences() -> PreferencesResponse:
    """Get notification preferences."""
    engine = get_notification_engine()
    prefs = engine.get_preferences()

    return PreferencesResponse(**prefs.to_dict())


@router.put("/preferences")
async def update_preferences(request: PreferencesRequest) -> PreferencesResponse:
    """Update notification preferences."""
    engine = get_notification_engine()
    prefs = engine.get_preferences()

    # Update only provided fields
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(prefs, key):
            setattr(prefs, key, value)

    engine.set_preferences(prefs)

    return PreferencesResponse(**prefs.to_dict())
