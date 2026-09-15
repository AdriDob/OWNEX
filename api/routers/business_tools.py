"""Free Business Tools API — inventario de herramientas $0 para tareas especiales.

Read-only, nunca ejecuta herramientas: solo inventaría disponibilidad real
(binarios/modules/services) y agrupa por tarea especial del sistema.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from cores.tools.business import by_task, inventory, summary, task_catalog

router = APIRouter(prefix="/api/business-tools", tags=["business-tools"])


@router.get("")
async def business_tools_inventory() -> dict[str, Any]:
    """Todas las herramientas gratis + estado de disponibilidad real."""
    rows = inventory()
    return {"total": len(rows), "summary": summary(), "tools": rows}


@router.get("/tasks")
async def business_tools_tasks() -> dict[str, Any]:
    """Tareas especiales del sistema y las herramientas $0 que las resuelven."""
    grouped = by_task()
    out: list[dict[str, Any]] = []
    for task in task_catalog():
        tools = grouped.get(task["id"], [])
        out.append(
            {
                "id": task["id"],
                "name": task["name"],
                "desc": task["desc"],
                "tools_count": len(tools),
                "available_count": sum(1 for t in tools if t["available"]),
                "tools": tools,
            }
        )
    return {"total": len(out), "tasks": out}


@router.get("/installs")
async def business_tools_recommended() -> dict[str, Any]:
    """Qué instalar y por qué: solo faltantes, agrupadas por tarea."""
    from cores.tools.business import recommended_installs

    return {"total_tasks_with_missing": len(recommended_installs()), "recommendations": recommended_installs()}
