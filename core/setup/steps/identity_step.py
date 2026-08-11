from __future__ import annotations

import getpass
from typing import Any

from core.setup.steps import define_step

IDENTITY_SCHEMA: dict[str, Any] = {
    "type": "form",
    "fields": [
        {"key": "username", "label": "Nombre de usuario", "type": "text", "required": True, "default": ""},
        {"key": "email", "label": "Email", "type": "email", "required": False, "default": ""},
        {
            "key": "role",
            "label": "Rol",
            "type": "select",
            "required": True,
            "default": "senior_hunter",
            "options": [
                {"value": "observer", "label": "Observer — solo lectura"},
                {"value": "assistant", "label": "Assistant — sugerencias automáticas"},
                {"value": "operator", "label": "Operator — ejecución con aprobación"},
                {"value": "senior_hunter", "label": "Senior Hunter — ejecución autónoma"},
                {"value": "administrator", "label": "Administrator — control total"},
            ],
        },
    ],
}


@define_step(
    step_id="identity",
    label="Identidad",
    description="Configurar tu perfil de usuario y nivel de autoridad",
    icon="user",
    order=1,
    required=True,
    schema=IDENTITY_SCHEMA,
)
def execute(state: dict[str, Any]) -> dict[str, Any]:
    username = state.get("username") or getpass.getuser()
    email = state.get("email", "")
    role = state.get("role", "senior_hunter")

    if not username or not username.strip():
        return {
            "status": "error",
            "message": "El nombre de usuario es obligatorio",
            "data": {"username": "", "email": email, "role": role},
        }

    return {
        "status": "ok",
        "message": f"Perfil configurado: {username} ({role})",
        "data": {
            "username": username,
            "email": email,
            "role": role,
            "orion_authority_level": role,
        },
    }
