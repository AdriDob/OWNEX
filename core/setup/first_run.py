from __future__ import annotations

import logging
import time
from typing import Any

from core import ORION_DIR

logger = logging.getLogger("orion.core.setup.first_run")

SETUP_MARKER = ORION_DIR / ".setup_complete"


def is_setup_complete() -> bool:
    from core.setup.wizard import _get_state

    return _get_state().completed or SETUP_MARKER.exists()


def setup_status() -> dict[str, Any]:
    from core.setup.wizard import wizard_status

    ws = wizard_status()
    done = ws.get("completed", False) or SETUP_MARKER.exists()
    if done:
        return {"completed": True, "wizard": ws, "message": "Configuración inicial completada"}
    return {"completed": False, "message": "Pendiente — ejecutar wizard de configuración"}


def complete_setup() -> dict[str, Any]:
    if is_setup_complete():
        return {"status": "ok", "message": "Setup already completed"}

    results: dict[str, Any] = {"timestamp": time.time()}
    errors: list[str] = []

    try:
        ORION_DIR.mkdir(parents=True, exist_ok=True)
        results["directories"] = "ok"
    except OSError as exc:
        errors.append(f"directories: {exc}")
        results["directories"] = f"error: {exc}"

    try:
        init_vault()
        results["vault"] = "ok"
    except Exception as exc:
        errors.append(f"vault: {exc}")
        results["vault"] = f"error: {exc}"

    try:
        init_config()
        results["config"] = "ok"
    except Exception as exc:
        errors.append(f"config: {exc}")
        results["config"] = f"error: {exc}"

    try:
        from core.integrations import init_integration_registry

        init_integration_registry()
        results["integrations"] = "ok"
    except Exception as exc:
        logger.warning("Integration registry init failed: %s", exc)
        results["integrations"] = f"warning: {exc}"

    try:
        SETUP_MARKER.write_text(f"completed_at: {time.time()}\n")
        results["marker"] = "ok"
    except OSError as exc:
        errors.append(f"marker: {exc}")
        results["marker"] = f"error: {exc}"

    status = "error" if errors else "ok"
    if status == "ok":
        logger.info("First-run setup completed successfully")

    return {"status": status, "results": results, "errors": errors}


def init_vault() -> None:
    from core.secrets.manager import get_secrets_manager

    get_secrets_manager()


def init_config() -> None:
    config_dir = ORION_DIR / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    log_dir = ORION_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    backups_dir = ORION_DIR / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
