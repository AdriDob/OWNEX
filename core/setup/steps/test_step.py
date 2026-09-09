from __future__ import annotations

import logging
from typing import Any

from core.setup.steps import define_step

logger = logging.getLogger("orion.core.setup.steps.test")

TEST_SCHEMA: dict[str, Any] = {
    "type": "checklist",
    "checks": [
        {"key": "event_bus", "label": "EventBus funcionando"},
        {"key": "database", "label": "Base de datos accesible"},
        {"key": "vault", "label": "Bóveda de secretos operativa"},
        {"key": "copilot", "label": "COPILOT inicializado"},
        {"key": "scheduler", "label": "Scheduler registrado"},
    ],
}


@define_step(
    step_id="test",
    label="Prueba",
    description="Verificar que el sistema funciona correctamente",
    icon="check-circle",
    order=6,
    required=True,
    schema=TEST_SCHEMA,
)
def execute(state: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []

    try:
        from core.events.event_bus import get_core_event_bus

        get_core_event_bus()
        results["event_bus"] = "ok"
    except Exception as exc:
        results["event_bus"] = f"error: {exc}"
        errors.append(f"EventBus: {exc}")

    try:
        from database.db import SessionLocal

        sess = SessionLocal()
        sess.execute(__import__("sqlalchemy", fromlist=["text"]).text("SELECT 1"))
        sess.close()
        results["database"] = "ok"
    except Exception as exc:
        results["database"] = f"error: {exc}"
        errors.append(f"Database: {exc}")

    try:
        from core.secrets.manager import get_secrets_manager

        manager = get_secrets_manager()
        health = manager.health()
        if health.get("status") == "ok" or health.get("ok"):
            results["vault"] = "ok"
        else:
            results["vault"] = "warning"
            warnings.append("Vault inicializado pero con advertencias")
    except Exception as exc:
        results["vault"] = f"error: {exc}"
        errors.append(f"Vault: {exc}")

    try:
        from core.copilot.agent import CopilotAgent

        CopilotAgent()
        results["copilot"] = "ok"
    except Exception as exc:
        results["copilot"] = f"warning: {exc}"
        warnings.append(f"COPILOT: {exc}")

    try:
        from core.execution.runtime.clock import VirtualClock
        from core.execution.runtime.kernel import ExecutionKernel
        from core.execution.runtime.scheduler import Scheduler

        clk = VirtualClock(simulation=True)
        kern = ExecutionKernel(clock=clk)
        Scheduler(kernel=kern)
        results["scheduler"] = "ok"
    except Exception as exc:
        results["scheduler"] = f"warning: {exc}"
        warnings.append(f"Scheduler: {exc}")

    status = "error" if errors else ("warning" if warnings else "ok")

    logger.info(
        "System test: %s (%d ok, %d warnings, %d errors)",
        status,
        sum(1 for v in results.values() if v == "ok"),
        len(warnings),
        len(errors),
    )

    return {
        "status": status,
        "message": f"Sistema {'funcional' if status == 'ok' else 'con advertencias' if status == 'warning' else 'con errores'}",
        "data": {
            "results": results,
            "errors": errors,
            "warnings": warnings,
        },
    }
