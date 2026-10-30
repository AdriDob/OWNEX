"""Daily Action Notification — "Next Best Action" system.

This module generates the primary daily notification that tells the user
exactly what to do right now, with EV, time estimate, and direct action.

The goal is that the user can open OWNEX and immediately know what to do
without interpreting multiple dashboards.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from cores.notifications.engine import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    get_notification_engine,
)

logger = logging.getLogger("ownex.notifications.daily_action")


@dataclass
class DailyAction:
    """A single daily action recommendation."""

    action: str  # What to do
    reason: str  # Why this action
    ev_usd: float  # Expected value in USD
    ev_per_hour: float  # EV per human hour
    time_estimate_minutes: int  # Estimated time in minutes
    priority: str  # high, medium, low
    impact: str  # Economic impact description
    entity_type: str  # "target", "finding", "report", etc.
    entity_id: str  # ID of the related entity
    action_route: str  # Route to navigate to
    action_payload: dict[str, Any] | None = None  # Additional payload

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "ev_usd": self.ev_usd,
            "ev_per_hour": self.ev_per_hour,
            "time_estimate_minutes": self.time_estimate_minutes,
            "priority": self.priority,
            "impact": self.impact,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action_route": self.action_route,
            "action_payload": self.action_payload or {},
        }


class DailyActionEngine:
    """Generates daily action notifications based on system state."""

    def __init__(self) -> None:
        self._engine = get_notification_engine()

    def generate_daily_action(self) -> DailyAction | None:
        """Generate the next best action based on current system state."""

        # This is a simplified implementation
        # In production, this would analyze:
        # - Current opportunities and their EV
        # - Pending tasks and their priority
        # - User's availability and preferences
        # - Historical success rates

        # For now, return a placeholder
        # TODO: Integrate with actual opportunity engine

        return None

    def send_daily_notification(self, action: DailyAction) -> Notification | None:
        """Send a daily action notification."""

        # Format the message
        time_str = f"{action.time_estimate_minutes} min"
        if action.time_estimate_minutes >= 60:
            hours = action.time_estimate_minutes // 60
            mins = action.time_estimate_minutes % 60
            time_str = f"{hours}h {mins}m" if mins else f"{hours}h"

        title = "NEXT BEST ACTION"
        message = f"""{action.action}

EV estimado: ${action.ev_usd:.0f}
Tiempo: ~{time_str}
Motivo: {action.reason}

{action.impact}"""

        # Create notification
        notification = Notification(
            type="daily_action",
            title=title,
            message=message,
            priority=NotificationPriority.HIGH,
            severity="high",
            category=NotificationCategory.IMPORTANT,
            source="daily_action_engine",
            source_id="daily",
            entity_type=action.entity_type,
            entity_id=action.entity_id,
            action_label="Start Now",
            action_route=action.action_route,
            action_payload=action.action_payload or {},
            channels=["web", "desktop"],
            group_key="daily_action",
            metadata={
                "ev_usd": action.ev_usd,
                "ev_per_hour": action.ev_per_hour,
                "time_estimate_minutes": action.time_estimate_minutes,
                "action": action.action,
            },
        )

        return self._engine.send(notification)

    def send_no_action_notification(self) -> Notification:
        """Send notification when no action is required."""

        title = "NO ACTION REQUIRED"
        message = """No higher-value action detected.

OWNEX will continue monitoring for opportunities.

Check back later or review your pending items."""

        notification = Notification(
            type="daily_action",
            title=title,
            message=message,
            priority=NotificationPriority.INFO,
            severity="info",
            category=NotificationCategory.SYSTEM,
            source="daily_action_engine",
            source_id="daily",
            channels=["web"],
            group_key="daily_action",
            metadata={"no_action": True},
        )

        return self._engine.send(notification)

    def send_weekly_summary(self, stats: dict[str, Any]) -> Notification:
        """Send a weekly summary notification."""

        title = "WEEKLY SUMMARY"
        message = f"""Your week in review:

• Opportunities discovered: {stats.get("opportunities_discovered", 0)}
• Actions completed: {stats.get("actions_completed", 0)}
• Total EV generated: ${stats.get("total_ev", 0):.0f}
• Time invested: {stats.get("time_invested_hours", 0):.1f}h
• Success rate: {stats.get("success_rate", 0):.0%}

Keep up the great work!"""

        notification = Notification(
            type="weekly_summary",
            title=title,
            message=message,
            priority=NotificationPriority.MEDIUM,
            severity="info",
            category=NotificationCategory.FINANCE,
            source="daily_action_engine",
            source_id="weekly",
            channels=["web"],
            group_key="weekly_summary",
            metadata=stats,
        )

        return self._engine.send(notification)


# Singleton instance
_daily_action_engine: DailyActionEngine | None = None


def get_daily_action_engine() -> DailyActionEngine:
    """Get or create the daily action engine."""
    global _daily_action_engine
    if _daily_action_engine is None:
        _daily_action_engine = DailyActionEngine()
    return _daily_action_engine
