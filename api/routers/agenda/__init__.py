"""Unified Agenda API — router canónico de la agenda.

Estructura (una sola implementación, sin duplicados):

    api/routers/agenda/__init__.py   → este router: prefix + vistas + sub-router
    api/routers/agenda/routes.py     → CRUD y vistas de calendario (sub-router)

Historia: hasta 2026-10-22 existía `api/routers/agenda.py` (módulo) junto a
`api/routers/agenda/` (paquete). En Python el paquete sombrea al módulo, así
que main.py montaba el paquete (4 rutas) y las 11 del módulo quedaban
**sin montar** (código muerto): `/api/agenda/items`, `/week`, `/month`,
`/day`, `/timeline`, `/deadlines`, `/refresh` respondían 404.

Las 3 vistas de este archivo fallaban con HTTP 500 (`KeyError`) porque
pedían claves (`next_actions`, `completed_today`, `by_source`) que
`build_unified_agenda()` nunca devolvió. Ahora se derivan del motor
canónico `cores.agenda.engine.AgendaEngine`, que es el dueño del modelo
(`AgendaItem` con `completed`/`completed_at`/`source`).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter

from api.routers.agenda.routes import get_unified_agenda
from api.routers.agenda.routes import router as _routes_router

router = APIRouter(prefix="/api/agenda", tags=["agenda"])
router.include_router(_routes_router)


def _engine():
    """Motor canónico de agenda (singleton)."""
    from cores.agenda.engine import get_agenda_engine

    return get_agenda_engine()


@router.get("", tags=["agenda-overview"])
async def get_agenda_overview() -> dict[str, Any]:
    """Vista unificada de la agenda (misma forma que AgendaView.vue)."""
    return await get_unified_agenda()


@router.get("/next-actions", tags=["agenda"])
async def get_next_actions() -> dict[str, Any]:
    """Próximas acciones: items no completados con fecha en los próximos 7 días."""
    engine = _engine()
    today = datetime.now(UTC).date()
    end = today + timedelta(days=7)
    items = engine.get_items(
        start_date=today.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
        include_completed=False,
    )
    return {"items": [i.to_dict() for i in items], "count": len(items)}


@router.get("/completed-today", tags=["agenda"])
async def get_completed_today() -> dict[str, Any]:
    """Items completados hoy (completed_at del día en curso)."""
    engine = _engine()
    today = datetime.now(UTC).date().isoformat()
    items = [
        i for i in engine.get_items(include_completed=True) if i.completed and (i.completed_at or "").startswith(today)
    ]
    return {"items": [i.to_dict() for i in items], "count": len(items)}


@router.get("/by-source", tags=["agenda"])
async def get_agenda_by_source() -> dict[str, Any]:
    """Items de la agenda agrupados por origen."""
    engine = _engine()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in engine.get_items(include_completed=True):
        grouped.setdefault(item.source.value, []).append(item.to_dict())
    return {"by_source": grouped, "sources": len(grouped)}
