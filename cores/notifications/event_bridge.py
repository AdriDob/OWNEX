from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
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


def _format_message(event: str, data: dict[str, Any]) -> str:
    parts = []
    for k, v in data.items():
        if k == "event":
            continue
        if isinstance(v, (list, dict)):
            import json

            v = json.dumps(v, indent=2)[:500]
        parts.append(f"**{k}**: {v}")
    return "\n".join(parts) if parts else "(sin detalles)"


def _handle_event(event: str, **data: Any) -> None:
    discord = get_discord_adapter()
    if not discord or not discord.is_enabled:
        return
    priority = EVENT_PRIORITY_MAP.get(event, "low")
    title = EVENT_TITLE_MAP.get(event, f"Evento: {event}")
    message = _format_message(event, data)
    discord.send(title=title, message=message, priority=priority)


class NotificationEventBridge:
    """Bridge EventBus events to Discord/web notifications."""

    def __init__(self, event_bus: CoreEventBus):
        self._bus = event_bus
        self._unsubscribers: list[Callable[[], None]] = []

    def start(self) -> int:
        for event_type in EVENT_PRIORITY_MAP:
            unsub = self._bus.subscribe(event_type, _handle_event)
            self._unsubscribers.append(unsub)
        logger.info(
            "[NOTIFY] EventBus bridge started — %d event types subscribed",
            len(self._unsubscribers),
        )
        return len(self._unsubscribers)

    def stop(self) -> None:
        for unsub in self._unsubscribers:
            with contextlib.suppress(Exception):
                unsub()
        count = len(self._unsubscribers)
        self._unsubscribers.clear()
        logger.info("[NOTIFY] EventBus bridge stopped — %d handlers removed", count)

    @property
    def subscribed_events(self) -> list[str]:
        return list(EVENT_PRIORITY_MAP)
