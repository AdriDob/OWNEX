from __future__ import annotations

from typing import Any

from core.setup.steps import define_step

SMARTWATCH_SCHEMA: dict[str, Any] = {
    "type": "form",
    "fields": [
        {
            "key": "enable_watch",
            "label": "Habilitar ORION Watch Companion",
            "type": "switch",
            "required": False,
            "default": False,
            "description": "Sincronizar notificaciones y estado con Wear OS",
        },
        {
            "key": "notifications_enabled",
            "label": "Notificaciones en el reloj",
            "type": "switch",
            "required": False,
            "default": True,
        },
        {
            "key": "critical_only",
            "label": "Solo alertas críticas",
            "type": "switch",
            "required": False,
            "default": False,
            "description": "Solo notificar aprobaciones y fallos del sistema",
        },
    ],
}


@define_step(
    step_id="smartwatch",
    label="Smartwatch",
    description="Configurar la extensión para Wear OS",
    icon="watch",
    order=5,
    required=False,
    schema=SMARTWATCH_SCHEMA,
)
def execute(state: dict[str, Any]) -> dict[str, Any]:
    enabled = state.get("enable_watch", False)

    if not enabled:
        return {
            "status": "ok",
            "message": "ORION Watch Companion no configurado (se puede activar después)",
            "data": {"enabled": False},
        }

    return {
        "status": "ok",
        "message": "ORION Watch Companion configurado",
        "data": {
            "enabled": True,
            "notifications_enabled": state.get("notifications_enabled", True),
            "critical_only": state.get("critical_only", False),
            "sync_via": "companion",
        },
    }
