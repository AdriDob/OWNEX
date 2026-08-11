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
            "description": "Recibir notificaciones en tu Wear OS",
        },
        {
            "key": "critical_only",
            "label": "Solo alertas críticas",
            "type": "switch",
            "required": False,
            "default": False,
            "description": "Solo notificar aprobaciones y fallos del sistema",
        },
        {
            "key": "approvals_enabled",
            "label": "Aprobaciones desde el reloj",
            "type": "switch",
            "required": False,
            "default": True,
            "description": "Permitir aprobar workflows desde el reloj",
        },
        {
            "key": "merlin_mini_enabled",
            "label": "MERLIN Mini en el reloj",
            "type": "switch",
            "required": False,
            "default": True,
            "description": "Interfaz simplificada de MERLIN en el reloj",
        },
        {
            "key": "sync_interval",
            "label": "Intervalo de sincronización (minutos)",
            "type": "number",
            "required": False,
            "default": 5,
            "description": "Frecuencia de sincronización con el reloj",
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
        "message": "ORION Watch Companion configurado exitosamente",
        "data": {
            "enabled": True,
            "notifications_enabled": state.get("notifications_enabled", True),
            "critical_only": state.get("critical_only", False),
            "approvals_enabled": state.get("approvals_enabled", True),
            "merlin_mini_enabled": state.get("merlin_mini_enabled", True),
            "sync_interval": state.get("sync_interval", 5),
            "sync_via": "companion",
        },
    }
