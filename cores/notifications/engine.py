"""Notification Engine — unified notification system for OWNEX.

This module implements the complete notification architecture:
- Priority Engine (CRITICAL/HIGH/MEDIUM/LOW/INFO)
- Smart Grouping to avoid noise
- Deduplication
- Channel routing (Desktop, Mobile, Watch, In-App)
- User preferences
- Cross-device sync
- Offline support

Architecture:
EVENT → EVENT BUS → NOTIFICATION ENGINE → PRIORITY ENGINE → DEDUPLICATION → GROUPING → USER PREFERENCES → CHANNEL ROUTER
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger("ownex.notifications.engine")


class NotificationPriority(Enum):
    """Priority levels for notifications."""

    CRITICAL = "critical"  # Requires immediate attention
    HIGH = "high"  # Important, should be reviewed soon
    MEDIUM = "medium"  # Useful information requiring eventual attention
    LOW = "low"  # Secondary information
    INFO = "info"  # Historical or context information


class NotificationCategory(Enum):
    """Notification categories for filtering."""

    ALL = "all"
    IMPORTANT = "important"
    OPPORTUNITIES = "opportunities"
    WORK = "work"
    FINANCE = "finance"
    SECURITY = "security"
    AGENTS = "agents"
    SYSTEM = "system"
    ERRORS = "errors"
    ACTION_REQUIRED = "action_required"


@dataclass
class Notification:
    """Enhanced notification with full metadata."""

    # Core fields
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    title: str = ""
    message: str = ""

    # Priority and severity
    priority: NotificationPriority = NotificationPriority.MEDIUM
    severity: str = "info"

    # Category
    category: NotificationCategory = NotificationCategory.SYSTEM

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    read_at: datetime | None = None
    resolved_at: datetime | None = None
    expires_at: datetime | None = None

    # Source and context
    source: str = ""  # Module that created the notification
    source_id: str = ""  # ID of the related entity

    # Related entities
    entity_type: str = ""  # "target", "finding", "report", etc.
    entity_id: str = ""  # ID of the related entity

    # Action
    action_label: str = ""  # Label for the action button
    action_route: str = ""  # Route to navigate to
    action_payload: dict[str, Any] = field(default_factory=dict)

    # Channels
    channels: list[str] = field(default_factory=lambda: ["web"])

    # Grouping
    group_key: str = ""  # Key for grouping related notifications
    group_count: int = 1  # Number of notifications in this group

    # State
    read: bool = False
    resolved: bool = False
    starred: bool = False

    # Deduplication
    dedup_key: str | None = None

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Tags
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API/WebSocket."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "severity": self.severity,
            "category": self.category.value,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "source": self.source,
            "source_id": self.source_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action_label": self.action_label,
            "action_route": self.action_route,
            "action_payload": self.action_payload,
            "channels": self.channels,
            "group_key": self.group_key,
            "group_count": self.group_count,
            "read": self.read,
            "resolved": self.resolved,
            "starred": self.starred,
            "dedup_key": self.dedup_key,
            "metadata": self.metadata,
            "tags": self.tags,
        }


@dataclass
class NotificationPreferences:
    """User notification preferences."""

    # Channel toggles
    desktop_enabled: bool = True
    mobile_enabled: bool = True
    watch_enabled: bool = True
    email_enabled: bool = False  # Disabled by default per new architecture

    # Priority toggles
    critical_enabled: bool = True
    high_enabled: bool = True
    medium_enabled: bool = True
    low_enabled: bool = True
    info_enabled: bool = True

    # Feature toggles
    daily_briefing_enabled: bool = True
    monthly_report_enabled: bool = True

    # Monthly report email
    monthly_report_email: str = ""

    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"  # HH:MM format
    quiet_hours_end: str = "08:00"  # HH:MM format
    quiet_hours_allow_critical: bool = False  # Allow CRITICAL during quiet hours

    # Grouping
    grouping_enabled: bool = True
    grouping_window_seconds: int = 300  # 5 minutes

    # Sound and vibration
    sound_enabled: bool = True
    vibration_enabled: bool = True

    # Badge
    badge_enabled: bool = True

    # Retention
    retention_days: int = 30  # Keep notifications for 30 days

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API."""
        return {
            "desktop_enabled": self.desktop_enabled,
            "mobile_enabled": self.mobile_enabled,
            "watch_enabled": self.watch_enabled,
            "email_enabled": self.email_enabled,
            "critical_enabled": self.critical_enabled,
            "high_enabled": self.high_enabled,
            "medium_enabled": self.medium_enabled,
            "low_enabled": self.low_enabled,
            "info_enabled": self.info_enabled,
            "daily_briefing_enabled": self.daily_briefing_enabled,
            "monthly_report_enabled": self.monthly_report_enabled,
            "monthly_report_email": self.monthly_report_email,
            "quiet_hours_enabled": self.quiet_hours_enabled,
            "quiet_hours_start": self.quiet_hours_start,
            "quiet_hours_end": self.quiet_hours_end,
            "quiet_hours_allow_critical": self.quiet_hours_allow_critical,
            "grouping_enabled": self.grouping_enabled,
            "grouping_window_seconds": self.grouping_window_seconds,
            "sound_enabled": self.sound_enabled,
            "vibration_enabled": self.vibration_enabled,
            "badge_enabled": self.badge_enabled,
            "retention_days": self.retention_days,
        }


class NotificationEngine:
    """Unified notification engine with priority, grouping, and routing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._notifications: list[Notification] = []
        self._preferences = NotificationPreferences()
        self._dedup_tracker: dict[str, float] = {}
        self._dedup_window: float = 30.0  # seconds
        self._group_buffer: list[Notification] = []
        self._group_window: float = 300.0  # 5 minutes
        self._max_notifications: int = 500

        # Channel handlers
        self._channel_handlers: dict[str, list[Any]] = defaultdict(list)

        # Listeners for real-time updates
        self._listeners: list[Any] = []

    def set_preferences(self, preferences: NotificationPreferences) -> None:
        """Update user preferences."""
        with self._lock:
            self._preferences = preferences
            self._group_window = preferences.grouping_window_seconds
        logger.info("Notification preferences updated")

    def get_preferences(self) -> NotificationPreferences:
        """Get current preferences."""
        return self._preferences

    def should_send(self, notification: Notification) -> bool:
        """Check if notification should be sent based on preferences."""
        prefs = self._preferences

        # Check priority toggle
        priority_enabled = {
            NotificationPriority.CRITICAL: prefs.critical_enabled,
            NotificationPriority.HIGH: prefs.high_enabled,
            NotificationPriority.MEDIUM: prefs.medium_enabled,
            NotificationPriority.LOW: prefs.low_enabled,
            NotificationPriority.INFO: prefs.info_enabled,
        }

        if not priority_enabled.get(notification.priority, True):
            return False

        # Check quiet hours
        if prefs.quiet_hours_enabled:
            now = datetime.now(UTC)
            current_time = now.strftime("%H:%M")

            start = prefs.quiet_hours_start
            end = prefs.quiet_hours_end

            in_quiet_hours = False
            if start <= end:
                in_quiet_hours = start <= current_time <= end
            else:
                in_quiet_hours = current_time >= start or current_time <= end

            if in_quiet_hours:
                if not prefs.quiet_hours_allow_critical:
                    return False
                if notification.priority != NotificationPriority.CRITICAL:
                    return False

        return True

    def is_duplicate(self, notification: Notification) -> bool:
        """Check if notification is a duplicate."""
        if not notification.dedup_key:
            return False

        now = time.time()
        last_seen = self._dedup_tracker.get(notification.dedup_key)

        if last_seen and (now - last_seen) < self._dedup_window:
            return True

        self._dedup_tracker[notification.dedup_key] = now
        return False

    def should_group(self, notification: Notification) -> bool:
        """Check if notification should be grouped with recent ones."""
        if not self._preferences.grouping_enabled:
            return False

        if not notification.group_key:
            return False

        now = time.time()

        # Check if there's a recent notification with the same group key
        for buffered in self._group_buffer:
            if (
                buffered.group_key == notification.group_key
                and (now - buffered.created_at.timestamp()) < self._group_window
            ):
                return True

        return False

    def add_to_group(self, notification: Notification) -> None:
        """Add notification to group buffer."""
        with self._lock:
            self._group_buffer.append(notification)

            # Clean old entries
            now = time.time()
            self._group_buffer = [
                n for n in self._group_buffer if (now - n.created_at.timestamp()) < self._group_window
            ]

    def get_grouped_notifications(self, group_key: str) -> list[Notification]:
        """Get all notifications in a group."""
        with self._lock:
            return [n for n in self._group_buffer if n.group_key == group_key]

    def send(self, notification: Notification) -> Notification | None:
        """Send a notification through the engine."""

        # Check if should send
        if not self.should_send(notification):
            logger.debug("Notification filtered by preferences: %s", notification.id)
            return None

        # Check deduplication
        if self.is_duplicate(notification):
            logger.debug("Notification deduplicated: %s", notification.id)
            return None

        # Check grouping
        if self.should_group(notification):
            self.add_to_group(notification)
            # Create a grouped notification
            grouped = self._create_grouped_notification(notification)
            if grouped:
                notification = grouped

        # Add to history
        with self._lock:
            self._notifications.append(notification)
            if len(self._notifications) > self._max_notifications:
                self._notifications = self._notifications[-self._max_notifications :]

        # Route to channels
        self._route(notification)

        # Notify listeners
        self._notify_listeners(notification)

        logger.info(
            "Notification sent: %s [%s] %s",
            notification.priority.value,
            notification.category.value,
            notification.title,
        )

        return notification

    def _create_grouped_notification(self, notification: Notification) -> Notification | None:
        """Create a grouped notification from multiple notifications."""
        grouped_notifications = self.get_grouped_notifications(notification.group_key)

        if len(grouped_notifications) < 2:
            return None

        # Create a summary notification
        count = len(grouped_notifications)
        titles = [n.title for n in grouped_notifications[:3]]

        summary_title = f"{notification.title}"
        if count > 1:
            summary_title = f"{count} notificaciones: {notification.title}"

        summary_message = f"Resumen de {count} notificaciones relacionadas:\n"
        for i, title in enumerate(titles, 1):
            summary_message += f"{i}. {title}\n"
        if count > 3:
            summary_message += f"... y {count - 3} más"

        return Notification(
            id=f"grouped-{notification.group_key}",
            type=notification.type,
            title=summary_title,
            message=summary_message,
            priority=notification.priority,
            severity=notification.severity,
            category=notification.category,
            source=notification.source,
            source_id=notification.source_id,
            entity_type=notification.entity_type,
            entity_id=notification.entity_id,
            action_label=notification.action_label,
            action_route=notification.action_route,
            channels=notification.channels,
            group_key=notification.group_key,
            group_count=count,
            metadata={**notification.metadata, "grouped_ids": [n.id for n in grouped_notifications]},
        )

    def _route(self, notification: Notification) -> None:
        """Route notification to appropriate channels."""
        prefs = self._preferences

        for channel in notification.channels:
            if channel == "desktop" and not prefs.desktop_enabled:
                continue
            if channel == "mobile" and not prefs.mobile_enabled:
                continue
            if channel == "watch" and not prefs.watch_enabled:
                continue
            if channel == "email" and not prefs.email_enabled:
                continue

            handlers = self._channel_handlers.get(channel, [])
            for handler in handlers:
                try:
                    handler(notification)
                except Exception as exc:
                    logger.warning("Channel handler error for %s: %s", channel, exc)

    def _notify_listeners(self, notification: Notification) -> None:
        """Notify all registered listeners."""
        for listener in self._listeners:
            try:
                listener(notification)
            except Exception as exc:
                logger.warning("Listener error: %s", exc)

    def register_channel_handler(self, channel: str, handler: Any) -> None:
        """Register a handler for a channel."""
        self._channel_handlers[channel].append(handler)
        logger.debug("Registered handler for channel: %s", channel)

    def add_listener(self, listener: Any) -> None:
        """Add a listener for real-time updates."""
        self._listeners.append(listener)

    def get_notifications(
        self,
        category: NotificationCategory | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get notifications with optional filtering."""
        with self._lock:
            notifications = self._notifications.copy()

        # Filter by category
        if category and category != NotificationCategory.ALL:
            notifications = [
                n
                for n in notifications
                if n.category == category
                or (
                    category == NotificationCategory.IMPORTANT
                    and n.priority in (NotificationPriority.CRITICAL, NotificationPriority.HIGH)
                )
            ]

        # Sort by created_at descending
        notifications.sort(key=lambda n: n.created_at, reverse=True)

        # Apply pagination
        return notifications[offset : offset + limit]

    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        with self._lock:
            return sum(1 for n in self._notifications if not n.read)

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        with self._lock:
            for n in self._notifications:
                if n.id == notification_id:
                    n.read = True
                    n.read_at = datetime.now(UTC)
                    return True
        return False

    def mark_all_read(self) -> int:
        """Mark all notifications as read. Returns count of marked notifications."""
        count = 0
        with self._lock:
            for n in self._notifications:
                if not n.read:
                    n.read = True
                    n.read_at = datetime.now(UTC)
                    count += 1
        return count

    def resolve(self, notification_id: str) -> bool:
        """Mark a notification as resolved."""
        with self._lock:
            for n in self._notifications:
                if n.id == notification_id:
                    n.resolved = True
                    n.resolved_at = datetime.now(UTC)
                    return True
        return False

    def remove(self, notification_id: str) -> bool:
        """Remove a notification."""
        with self._lock:
            for i, n in enumerate(self._notifications):
                if n.id == notification_id:
                    self._notifications.pop(i)
                    return True
        return False

    def clear_all(self) -> int:
        """Clear all notifications. Returns count of cleared notifications."""
        with self._lock:
            count = len(self._notifications)
            self._notifications.clear()
        return count

    def cleanup_expired(self) -> int:
        """Remove expired notifications. Returns count of removed notifications."""
        now = datetime.now(UTC)
        removed = 0

        with self._lock:
            expired = [n for n in self._notifications if n.expires_at and n.expires_at < now]
            for n in expired:
                self._notifications.remove(n)
                removed += 1

        return removed

    def get_stats(self) -> dict[str, Any]:
        """Get notification statistics."""
        with self._lock:
            total = len(self._notifications)
            unread = sum(1 for n in self._notifications if not n.read)
            resolved = sum(1 for n in self._notifications if n.resolved)

            by_priority = defaultdict(int)
            by_category = defaultdict(int)

            for n in self._notifications:
                by_priority[n.priority.value] += 1
                by_category[n.category.value] += 1

        return {
            "total": total,
            "unread": unread,
            "resolved": resolved,
            "by_priority": dict(by_priority),
            "by_category": dict(by_category),
        }


# Singleton instance
_engine: NotificationEngine | None = None


def get_notification_engine() -> NotificationEngine:
    """Get or create the global notification engine."""
    global _engine
    if _engine is None:
        _engine = NotificationEngine()
    return _engine
