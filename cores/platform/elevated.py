"""Elevated Action Mode — normal user by default, elevated only when strictly required.

Never runs the whole app as Administrator. When an operation needs elevation
(install, service, repair, driver, some Windows configs), this module detects
the need, explains WHY/WHAT/SCOPE/DURATION, and requests elevation in a
controlled way via UAC (Windows) or sudo prompt (Linux/macOS).
"""

from __future__ import annotations

import logging
import os
import platform
from typing import Any

logger = logging.getLogger("ownex.platform.elevated")


def is_admin() -> bool:
    """True if current process has admin/root privileges."""
    try:
        if platform.system().lower().startswith("win"):
            import ctypes  # type: ignore[import-untyped]

            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        return os.geteuid() == 0
    except Exception:
        return False


def needs_elevation(action: str) -> tuple[bool, str]:
    """Whether an action strictly requires elevation and why."""
    elevated_actions = {
        "install": "Instalación de MSI/EXE y registro de servicios",
        "update": "Actualización de binarios y servicios",
        "service": "Configuración de servicios de Windows",
        "repair": "Reparación de instalación o permisos",
        "driver": "Instalación/actualización de drivers relevantes",
        "windows_config": "Configuración de sistema que requiere privilegios",
    }
    if action in elevated_actions:
        return True, elevated_actions[action]
    return False, "No requiere privilegios elevados"


def request_elevation(
    reason: str, what: str, scope: str = "single operation", duration: str = "once"
) -> dict[str, Any]:
    """Request elevation in a controlled way. Returns {requested, is_admin, how}."""
    already = is_admin()
    if already:
        return {"requested": False, "is_admin": True, "how": "already elevated", "reason": reason}

    system = platform.system().lower()
    how = (
        "UAC prompt (Windows) — aprobar solo esta operación"
        if system.startswith("win")
        else "sudo prompt — aprobar solo esta operación"
    )
    logger.info("Elevation requested: reason=%s what=%s scope=%s duration=%s", reason, what, scope, duration)
    return {
        "requested": True,
        "is_admin": False,
        "how": how,
        "reason": reason,
        "what": what,
        "scope": scope,
        "duration": duration,
        "note": "OWNEX no se ejecuta permanentemente como administrador. Solo esta acción se elevará si el usuario aprueba.",
    }


def elevation_status() -> dict[str, Any]:
    """Current elevation status for System Health display."""
    admin = is_admin()
    return {
        "is_admin": admin,
        "mode": "ELEVATED" if admin else "NORMAL USER",
        "policy": "NORMAL USER por defecto; ELEVATED solo para install/update/service/repair cuando sea estrictamente necesario",
    }
