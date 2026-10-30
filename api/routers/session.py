"""Session API — autoguardado de trabajo diario.

Endpoints:

* ``GET    /api/session/status``      — estado de la sesión activa (para el dashboard).
* ``GET    /api/session/current``     — sesión actual completa con tarea en curso.
* ``POST   /api/session/start``       — iniciar nueva sesión de trabajo.
* ``POST   /api/session/task``        — guardar tarea en curso (título, estado, notas, prioridad, target).
* ``POST   /api/session/progress``    — autoguardar progreso (notas, evidencia, momentum).
* ``POST   /api/session/complete``    — cerrar sesión activa.
* ``GET    /api/session/recent``      — últimas sesiones (historial de trabajo).

Todo lo guardado sobrevive a reinicios del sistema (BD SQLite + respaldo JSON).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from cores.session_manager import (
    FOCO_OPTIONS,
    session_manager,
)

router = APIRouter(tags=["session"])

# Nota: paths absolutos porque main.py aplica un monkey-patch a
# include_router que extiende router.routes directamente descartando el
# prefix del APIRouter. Así las rutas quedan en /api/session/* sin depender
# de cómo se monte el router.


@router.get("/api/session/status", summary="Estado de la sesión de trabajo activa")
async def session_status() -> dict[str, Any]:
    """Devuelve si hay sesión activa, tarea en curso y progreso."""
    return session_manager.get_status()


@router.get("/api/session/current", summary="Sesión actual completa")
async def session_current() -> dict[str, Any]:
    """Devuelve la sesión actual (o la más reciente) con su tarea en curso."""
    data = session_manager.get_current_session()
    if data is None:
        return {"success": True, "has_session": False, "session": None}
    return {"success": True, "has_session": True, "session": data}


@router.post("/api/session/start", summary="Iniciar una nueva sesión de trabajo")
async def session_start(body: dict[str, Any]) -> dict[str, Any]:
    """Inicia una nueva sesión.

    Body opcional: ``{"focus": "bounty|skill|pulse|...", "daily_goal": "...", "notes": "..."}``
    """
    focus = body.get("focus", "bounty")
    if focus not in FOCO_OPTIONS:
        focus = "otro"
    started = session_manager.start_session(
        focus=focus,
        daily_goal=body.get("daily_goal"),
        notes=body.get("notes"),
    )
    return {"success": True, "session": started}


@router.post("/api/session/task", summary="Guardar tarea en curso")
async def session_task(body: dict[str, Any]) -> dict[str, Any]:
    """Guarda (o crea y guarda) la tarea en la que se está trabajando."""
    title = body.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="title es obligatorio")
    saved = session_manager.set_current_task(
        title=title,
        status=body.get("status", "in_progress"),
        notes=body.get("notes"),
        priority=body.get("priority", "medium"),
        linked_type=body.get("linked_type"),
        linked_id=body.get("linked_id"),
        momentum=body.get("momentum"),
        targets_referenced=body.get("targets_referenced"),
        evidence_partial=body.get("evidence_partial"),
    )
    return {"success": True, "task": saved}


@router.post("/api/session/progress", summary="Autoguardar progreso de la tarea")
async def session_progress(body: dict[str, Any]) -> dict[str, Any]:
    """Guarda notas de progreso, una evidencia nueva y/o momentum de la tarea actual."""
    result = session_manager.save_progress(
        notes=body.get("notes"),
        evidence_item=body.get("evidence_item"),
        momentum=body.get("momentum"),
        targets_referenced=body.get("targets_referenced"),
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/api/session/complete", summary="Cerrar la sesión de trabajo activa")
async def session_complete(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Marca la sesión activa como completada."""
    return session_manager.complete_session()


@router.get("/api/session/recent", summary="Últimas sesiones de trabajo")
async def session_recent(limit: int = 10) -> dict[str, Any]:
    """Historial de sesiones para el dashboard (cuánto se trabajó y en qué)."""
    sessions = session_manager.list_recent(limit=limit)
    return {"success": True, "sessions": sessions, "count": len(sessions)}
