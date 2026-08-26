"""Unified Agenda Router — vista calendario de tareas, objetivos y metas."""

from __future__ import annotations

from fastapi import APIRouter

from cores.agenda import build_unified_agenda

router = APIRouter(prefix="/api/agenda", tags=["agenda"])


@router.get("")
async def get_agenda() -> dict:
    """Agenda unificada: corto/mediano/largo plazo desde todos los sistemas."""
    return build_unified_agenda()
