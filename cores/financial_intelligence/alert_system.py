"""Real-time Alert System — Automatic pop-ups for errors and human intervention.

This system creates automatic pop-up alerts when:
- Errors occur in critical systems
- Human intervention is required
- System health degrades
- Actions need approval
- Credentials are missing
- Funding is needed

Integrates with NotificationHub and ActionRequired.
Shows real-time pop-ups in frontend via WebSocket.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.notifications.action_required import (
    notify_action_required,
    notify_credentials_missing,
    notify_funding_needed,
    notify_review_required,
    notify_system_stalled,
)
from cores.notifications.hub import Notification, get_hub

logger = logging.getLogger("ownex.alerts")


class AlertType(StrEnum):
    """Types of automatic alerts."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"
    CRITICAL = "critical"


class AlertCategory(StrEnum):
    """Categories of alerts."""

    SYSTEM = "system"
    CREDENTIALS = "credentials"
    FUNDING = "funding"
    APPROVAL = "approval"
    REVIEW = "review"
    HEALTH = "health"
    ERROR = "error"
    AUTO_APPLY = "auto_apply"
    INFINITE_SOURCES = "infinite_sources"
    ULTRA_FAST_INCOME = "ultra_fast_income"


@dataclass
class Alert:
    """A real-time alert for pop-up display."""

    id: str
    type: AlertType
    category: AlertCategory
    title: str
    message: str
    timestamp: str
    severity: str
    priority: str
    requires_action: bool = False
    action_steps: list[str] = field(default_factory=list)
    ui_path: str = ""
    auto_dismiss_after: int = 0  # 0 = no auto-dismiss
    escalated: bool = False
    resolved: bool = False
    resolved_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "category": self.category.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "priority": self.priority,
            "requires_action": self.requires_action,
            "action_steps": self.action_steps,
            "ui_path": self.ui_path,
            "auto_dismiss_after": self.auto_dismiss_after,
            "escalated": self.escalated,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
            "metadata": self.metadata,
        }


class RealTimeAlertSystem:
    """System for automatic real-time alerts and pop-ups.

    Monitors system health and generates alerts automatically.
    Integrates with NotificationHub for routing.
    Provides WebSocket feed for frontend pop-ups.
    """

    def __init__(self, state_file: Path = Path("data/alerts_state.json")):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._alerts: list[Alert] = []
        self._alert_listeners: list[callable] = []
        self._lock = threading.Lock()
        self._load_state()

    def _load_state(self) -> None:
        """Load alert state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self._alerts = [
                        Alert(
                            id=a["id"],
                            type=AlertType(a["type"]),
                            category=AlertCategory(a["category"]),
                            title=a["title"],
                            message=a["message"],
                            timestamp=a["timestamp"],
                            severity=a["severity"],
                            priority=a["priority"],
                            requires_action=a.get("requires_action", False),
                            action_steps=a.get("action_steps", []),
                            ui_path=a.get("ui_path", ""),
                            auto_dismiss_after=a.get("auto_dismiss_after", 0),
                            escalated=a.get("escalated", False),
                            resolved=a.get("resolved", False),
                            resolved_at=a.get("resolved_at"),
                            metadata=a.get("metadata", {}),
                        )
                        for a in data.get("alerts", [])
                    ]
                logger.info(f"Loaded {len(self._alerts)} alerts from state")
            except Exception as e:
                logger.warning(f"Failed to load alert state: {e}")

    def _save_state(self) -> None:
        """Save alert state to disk."""
        try:
            data = {
                "alerts": [a.to_dict() for a in self._alerts],
                "last_updated": datetime.now(UTC).isoformat(),
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved alert state")
        except Exception as e:
            logger.error(f"Failed to save alert state: {e}")

    def add_listener(self, listener: callable) -> None:
        """Add a listener for new alerts (e.g., WebSocket broadcaster)."""
        with self._lock:
            self._alert_listeners.append(listener)

    def _notify_listeners(self, alert: Alert) -> None:
        """Notify all listeners of new alert."""
        for listener in self._alert_listeners:
            try:
                listener(alert.to_dict())
            except Exception as e:
                logger.error(f"Alert listener error: {e}")

    def create_alert(
        self,
        type: AlertType,
        category: AlertCategory,
        title: str,
        message: str,
        severity: str = "info",
        priority: str = "medium",
        requires_action: bool = False,
        action_steps: list[str] | None = None,
        ui_path: str = "",
        auto_dismiss_after: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> Alert:
        """Create and broadcast a new alert."""
        alert = Alert(
            id=f"alert-{int(time.time() * 1000)}",
            type=type,
            category=category,
            title=title,
            message=message,
            timestamp=datetime.now(UTC).isoformat(),
            severity=severity,
            priority=priority,
            requires_action=requires_action,
            action_steps=action_steps or [],
            ui_path=ui_path,
            auto_dismiss_after=auto_dismiss_after,
            metadata=metadata or {},
        )

        with self._lock:
            self._alerts.append(alert)
            # Keep only last 100 alerts
            if len(self._alerts) > 100:
                self._alerts = self._alerts[-100:]

        self._save_state()
        self._notify_listeners(alert)

        # Also send to NotificationHub
        notif = Notification(
            id=alert.id,
            type=type.value,
            title=title,
            message=message,
            severity=severity,
            priority=priority,
            channels=["web", "desktop"],
            metadata=alert.to_dict(),
        )
        get_hub().send(notif)

        logger.info(f"[ALERT] {type.value} | {category.value} | {title}")
        return alert

    def create_error_alert(
        self,
        component: str,
        error_message: str,
        context: dict[str, Any] | None = None,
    ) -> Alert:
        """Create an error alert."""
        return self.create_alert(
            type=AlertType.ERROR,
            category=AlertCategory.ERROR,
            title=f"Error in {component}",
            message=error_message,
            severity="error",
            priority="high",
            requires_action=True,
            action_steps=[
                "Check system logs for details",
                "Verify component configuration",
                "Restart component if needed",
            ],
            ui_path="/health",
            metadata={"component": component, "context": context or {}},
        )

    def create_warning_alert(
        self,
        component: str,
        warning_message: str,
        context: dict[str, Any] | None = None,
    ) -> Alert:
        """Create a warning alert."""
        return self.create_alert(
            type=AlertType.WARNING,
            category=AlertCategory.SYSTEM,
            title=f"Warning: {component}",
            message=warning_message,
            severity="warning",
            priority="medium",
            requires_action=False,
            auto_dismiss_after=30,  # 30 seconds
            metadata={"component": component, "context": context or {}},
        )

    def create_action_required_alert(
        self,
        title: str,
        reason: str,
        impact: str,
        steps: list[str],
        ui_path: str,
        category: AlertCategory = AlertCategory.SYSTEM,
        priority: str = "medium",
    ) -> Alert:
        """Create an action-required alert."""
        alert = self.create_alert(
            type=AlertType.CRITICAL if priority == "critical" else AlertType.WARNING,
            category=category,
            title=title,
            message=f"{reason}\n\nImpact: {impact}",
            severity=priority,
            priority=priority,
            requires_action=True,
            action_steps=steps,
            ui_path=ui_path,
            auto_dismiss_after=0,  # No auto-dismiss
        )

        # Also create ActionRequired for persistence
        notify_action_required(
            title=title,
            reason=reason,
            impact=impact,
            steps=steps,
            ui_path=ui_path,
            category=category.value,
            priority=priority,
        )

        return alert

    def resolve_alert(self, alert_id: str) -> Alert | None:
        """Mark an alert as resolved."""
        with self._lock:
            for alert in self._alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    alert.resolved_at = datetime.now(UTC).isoformat()
                    self._save_state()
                    logger.info(f"[ALERT_RESOLVED] {alert_id}")
                    return alert
        return None

    def get_active_alerts(self, include_resolved: bool = False) -> list[Alert]:
        """Get all alerts, optionally including resolved ones."""
        with self._lock:
            if include_resolved:
                return self._alerts.copy()
            return [a for a in self._alerts if not a.resolved]

    def get_alerts_by_category(self, category: AlertCategory) -> list[Alert]:
        """Get alerts by category."""
        with self._lock:
            return [a for a in self._alerts if a.category == category and not a.resolved]

    def get_status(self) -> dict[str, Any]:
        """Get current alert system status."""
        with self._lock:
            active = [a for a in self._alerts if not a.resolved]
            critical = [a for a in active if a.priority == "critical"]
            high = [a for a in active if a.priority == "high"]
            medium = [a for a in active if a.priority == "medium"]
            low = [a for a in active if a.priority == "low"]

            return {
                "total_alerts": len(self._alerts),
                "active_alerts": len(active),
                "resolved_alerts": len(self._alerts) - len(active),
                "by_priority": {
                    "critical": len(critical),
                    "high": len(high),
                    "medium": len(medium),
                    "low": len(low),
                },
                "by_category": {
                    cat.value: len([a for a in active if a.category == cat])
                    for cat in AlertCategory
                },
            }


# Singleton instance
_global_alert_system: RealTimeAlertSystem | None = None


def get_alert_system() -> RealTimeAlertSystem:
    """Get or create the global alert system."""
    global _global_alert_system
    if _global_alert_system is None:
        _global_alert_system = RealTimeAlertSystem()
    return _global_alert_system
