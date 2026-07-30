"""
EventBus bridge for CATEYE notifications to Discord/web.
Uses `EventBus` from `cores.events.event_bus` for compatibility.
"""

import logging
from typing import Any

from core.events.event_bus import CoreEventBus
from cores.notifications.discord import get_discord_adapter

logger = logging.getLogger("cateye.notifications.event_bridge")

EVENT_PRIORITY_MAP: dict[str, str] = {
    "finding:created": "high",
    "finding:status_changed": "medium",
    "finding:confirmed": "high",
    "report:generated": "medium",
    "report:accepted": "medium",
    "report:rejected": "low",
    "system:alert": "high",
    "system:degraded": "critical",
    "system:error": "high",
    "opportunity:found": "low",
    "financial:payout_received": "medium",
    "financial:payout_confirmed": "low",
}

EVENT_TITLE_MAP: dict[str, str] = {
    "finding:created": "Finding Detectado",
    "finding:status_changed": "Estado de Finding Cambiado",
    "finding:confirmed": "Finding Confirmado",
    "report:generated": "Reporte Generado",
    "report:accepted": "Reporte Aceptado",
    "report:rejected": "Reporte Rechazado",
    "system:alert": "Alerta del Sistema",
    "system:degraded": "Sistema Degradado",
    "system:error": "Error del Sistema",
    "opportunity:found": "Nueva Oportunidad",
    "financial:payout_received": "Pago Recibido",
    "financial:payout_confirmed": "Pago Confirmado",
}


class NotificationEventBridge:
    """Bridge for CATEYE event bus -> Discord/web notifications."""

    def __init__(self, event_bus: CoreEventBus):
        self._event_bus = event_bus
        self._subscriptions: list = []
        self._discord_adapter = get_discord_adapter()

    def start(self) -> int:
        """Start listening for events and dispatch to Discord."""
        subscribed_count = 0

        for event, priority in EVENT_PRIORITY_MAP.items():
            # Subscribe to event with appropriate priority
            sub_unsub = self._event_bus.subscribe(event, self._handle_event)
            self._subscriptions.append(sub_unsub)
            subscribed_count += 1

        return subscribed_count

    def _handle_event(self, event: str, **data: Any) -> None:
        """Process incoming event and dispatch notification."""
        priority = EVENT_PRIORITY_MAP.get(event, "medium")
        title = EVENT_TITLE_MAP.get(event, event)

        # Convert event data to message string
        message = f"Event: {event}\nData: {data}"

        # Dispatch to Discord adapter
        self._discord_adapter.send(
            title=title,
            message=message,
            priority=priority,
            metadata={"event": event, **data},
        )

    def stop(self) -> None:
        """Stop listening for events."""
        for unsub in self._subscriptions:
            unsub()
        self._subscriptions.clear()

    @property
    def subscribed_events(self) -> list[str]:
        """Get list of currently subscribed events."""
        return list(EVENT_PRIORITY_MAP.keys())
