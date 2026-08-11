from __future__ import annotations

from typing import Any

from core.setup.requirements_check import check_all as check_requirements
from core.setup.steps import define_step

SYSTEM_SCHEMA: dict[str, Any] = {
    "type": "checklist",
    "checks": [
        {"key": "python", "label": "Python 3.10+"},
        {"key": "node", "label": "Node.js 18+"},
        {"key": "ollama", "label": "Ollama (modelos locales)"},
        {"key": "disk", "label": "Disco (>500 MB libres)"},
        {"key": "permissions", "label": "Permisos de escritura"},
    ],
}


@define_step(
    step_id="system",
    label="Sistema",
    description="Verificar que el entorno cumple los requisitos mínimos",
    icon="monitor",
    order=2,
    required=True,
    schema=SYSTEM_SCHEMA,
)
def execute(state: dict[str, Any]) -> dict[str, Any]:
    r = check_requirements()

    status = "ok"
    if r["errors"] > 0:
        status = "error"
    elif r["warnings"] > 0:
        status = "warning"

    data: dict[str, Any] = {
        "total_checks": r["total"],
        "ok": r["ok"],
        "warnings": r["warnings"],
        "errors": r["errors"],
        "results": r["results"],
        "by_category": r["by_category"],
    }
    for cr in r["results"]:
        data[cr["name"]] = cr["status"]

    return {
        "status": status,
        "message": f"{r['ok']} ok, {r['warnings']} advertencias, {r['errors']} errores",
        "data": data,
    }
