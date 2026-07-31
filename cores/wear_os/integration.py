"""Wear OS Smartwatch Integration for OWNEX OMEGA.

Sistema de integración con Wear OS para:
- Notificaciones críticas
- Aprobaciones rápidas
- Estado del sistema
- MERLIN mini
- Sincronización con Companion móvil
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger("ownex.wear_os")


class WatchEventType(StrEnum):
    """Tipos de eventos del reloj."""
    NOTIFICATION = "notification"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    STATUS_UPDATE = "status_update"
    SYSTEM_ALERT = "system_alert"
    MERLIN_MESSAGE = "merlin_message"


class WatchNotificationLevel(StrEnum):
    """Niveles de notificación."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class WatchNotification:
    """Notificación para el reloj."""
    notification_id: str
    title: str
    message: str
    level: WatchNotificationLevel
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False
    requires_action: bool = False
    action_type: str | None = None


@dataclass
class WatchApprovalRequest:
    """Solicitud de aprobación desde el reloj."""
    request_id: str
    title: str
    description: str
    workflow_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    responded: bool = False
    approved: bool | None = None


@dataclass
class WatchStatus:
    """Estado del sistema para el reloj."""
    system_online: bool = True
    scheduler_running: bool = False
    active_workflows: int = 0
    pending_approvals: int = 0
    findings_total: int = 0
    findings_confirmed: int = 0
    targets_active: int = 0
    health_score: float = 100.0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class WearOSIntegration:
    """Integración con Wear OS."""

    def __init__(self, storage_path: Path | None = None):
        self.storage_path = storage_path or Path.home() / ".ownex" / "wear_os"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.notifications: list[WatchNotification] = []
        self.approval_requests: list[WatchApprovalRequest] = []
        self._load_state()

    def _load_state(self) -> None:
        """Cargar estado desde almacenamiento."""
        notifications_file = self.storage_path / "notifications.json"
        if notifications_file.exists():
            with open(notifications_file) as f:
                data = json.load(f)
                self.notifications = [WatchNotification(**n) for n in data]

        approvals_file = self.storage_path / "approvals.json"
        if approvals_file.exists():
            with open(approvals_file) as f:
                data = json.load(f)
                self.approval_requests = [WatchApprovalRequest(**a) for a in data]

    def _save_state(self) -> None:
        """Guardar estado a almacenamiento."""
        notifications_file = self.storage_path / "notifications.json"
        with open(notifications_file, "w") as f:
            json.dump([n.__dict__ for n in self.notifications], f, indent=2, default=str)

        approvals_file = self.storage_path / "approvals.json"
        with open(approvals_file, "w") as f:
            json.dump([a.__dict__ for a in self.approval_requests], f, indent=2, default=str)

    def send_notification(
        self,
        title: str,
        message: str,
        level: WatchNotificationLevel = WatchNotificationLevel.MEDIUM,
        requires_action: bool = False,
        action_type: str | None = None,
    ) -> WatchNotification:
        """Enviar notificación al reloj."""
        notification = WatchNotification(
            notification_id=f"notif_{datetime.now().timestamp()}",
            title=title,
            message=message,
            level=level,
            requires_action=requires_action,
            action_type=action_type,
        )

        self.notifications.insert(0, notification)

        # Keep only last 50 notifications
        if len(self.notifications) > 50:
            self.notifications = self.notifications[:50]

        self._save_state()
        logger.info(f"Wear OS notification sent: {title}")
        return notification

    def request_approval(
        self,
        title: str,
        description: str,
        workflow_id: str | None = None,
    ) -> WatchApprovalRequest:
        """Solicitar aprobación desde el reloj."""
        request = WatchApprovalRequest(
            request_id=f"approval_{datetime.now().timestamp()}",
            title=title,
            description=description,
            workflow_id=workflow_id,
        )

        self.approval_requests.insert(0, request)

        # Keep only last 20 approval requests
        if len(self.approval_requests) > 20:
            self.approval_requests = self.approval_requests[:20]

        self._save_state()
        logger.info(f"Wear OS approval request sent: {title}")
        return request

    def respond_approval(self, request_id: str, approved: bool) -> bool:
        """Responder a solicitud de aprobación."""
        request = next((r for r in self.approval_requests if r.request_id == request_id), None)

        if not request:
            return False

        request.responded = True
        request.approved = approved

        self._save_state()
        logger.info(f"Wear OS approval response: {request_id} = {approved}")
        return True

    def get_status(self) -> WatchStatus:
        """Obtener estado del sistema para el reloj."""
        # This would query the actual system status
        # For now, return a basic status
        return WatchStatus(
            system_online=True,
            scheduler_running=True,
            active_workflows=3,
            pending_approvals=len([r for r in self.approval_requests if not r.responded]),
            findings_total=42,
            findings_confirmed=23,
            targets_active=8,
            health_score=95.0,
        )

    def get_notifications(
        self,
        level: WatchNotificationLevel | None = None,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[WatchNotification]:
        """Obtener notificaciones del reloj."""
        notifications = self.notifications

        if level:
            notifications = [n for n in notifications if n.level == level]

        if unread_only:
            notifications = [n for n in notifications if not n.read]

        return notifications[:limit]

    def mark_notification_read(self, notification_id: str) -> bool:
        """Marcar notificación como leída."""
        notification = next((n for n in self.notifications if n.notification_id == notification_id), None)

        if not notification:
            return False

        notification.read = True
        self._save_state()
        return True

    def get_pending_approvals(self) -> list[WatchApprovalRequest]:
        """Obtener aprobaciones pendientes."""
        return [r for r in self.approval_requests if not r.responded]

    def clear_old_notifications(self, days: int = 7) -> int:
        """Limpiar notificaciones antiguas."""
        cutoff = datetime.now().timestamp() - (days * 86400)
        original_count = len(self.notifications)
        self.notifications = [n for n in self.notifications if datetime.fromisoformat(n.created_at).timestamp() > cutoff]
        self._save_state()
        return original_count - len(self.notifications)


# Singleton instance
_wear_os_integration: WearOSIntegration | None = None


def get_wear_os_integration() -> WearOSIntegration:
    """Obtener instancia singleton de integración Wear OS."""
    global _wear_os_integration
    if _wear_os_integration is None:
        _wear_os_integration = WearOSIntegration()
    return _wear_os_integration


def reset_wear_os_integration() -> None:
    """Resetear instancia singleton."""
    global _wear_os_integration
    _wear_os_integration = None
