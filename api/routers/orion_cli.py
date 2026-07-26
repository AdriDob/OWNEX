"""ORION CLI + F1 API — command center and assistant endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

from core.f1 import get_f1
from core.notifications.intelligent import DetailLevel, get_intelligent_notifier
from core.orion_cli import get_cli

logger = logging.getLogger("orion.cli.api")
router = APIRouter(prefix="/api/cli", tags=["orion_cli"])


def _detail_from_query(detalles: bool, debug: bool) -> int:
    if debug:
        return 3
    if detalles:
        return 2
    return 1


@router.get("/help")
async def cli_help(command: str = ""):
    """Lista de comandos disponibles."""
    cli = get_cli()
    result = cli.help(command)
    return {"success": result.success, "command": "help", "summary": result.summary}


@router.get("/status")
async def cli_status(detalles: bool = Query(False), debug: bool = Query(False)):
    """Estado general del sistema."""
    cli = get_cli()
    detail = _detail_from_query(detalles, debug)
    result = cli.status(detail=detail)
    return {
        "success": result.success,
        "command": "status",
        "summary": result.summary,
        "suggestions": result.suggestions,
        "debug": result.debug if debug else None,
    }


@router.get("/daily")
async def cli_daily(detalles: bool = Query(False), debug: bool = Query(False)):
    """Briefing diario completo."""
    cli = get_cli()
    detail = _detail_from_query(detalles, debug)
    result = cli.daily(detail=detail)
    return {
        "success": result.success,
        "command": "daily",
        "summary": result.summary,
        "suggestions": result.suggestions,
    }


@router.post("/hunt")
async def cli_hunt(data: dict[str, Any] | None = None):
    """Activar cacería de vulnerabilidades."""
    cli = get_cli()
    target = (data or {}).get("target", "")
    result = cli.hunt(target=target)
    return {
        "success": result.success,
        "command": "hunt",
        "summary": result.summary,
        "suggestions": result.suggestions,
    }


@router.post("/trade")
async def cli_trade():
    """Activar trading automatizado."""
    cli = get_cli()
    result = cli.trade()
    return {
        "success": result.success,
        "command": "trade",
        "summary": result.summary,
        "suggestions": result.suggestions,
    }


@router.get("/revenue")
async def cli_revenue(detalles: bool = Query(False), debug: bool = Query(False)):
    """Estado financiero y revenue actual."""
    cli = get_cli()
    detail = _detail_from_query(detalles, debug)
    result = cli.revenue(detail=detail)
    return {
        "success": result.success,
        "command": "revenue",
        "summary": result.summary,
        "suggestions": result.suggestions,
    }


@router.post("/max")
async def cli_max():
    """MAX REVENUE MODE — todo al máximo."""
    cli = get_cli()
    result = cli.max_revenue()
    return {
        "success": result.success,
        "command": "max",
        "summary": result.summary,
        "suggestions": result.suggestions,
    }


@router.get("/health")
async def cli_health(detalles: bool = Query(False), debug: bool = Query(False)):
    """Salud del sistema y servicios."""
    cli = get_cli()
    detail = _detail_from_query(detalles, debug)
    result = cli.health(detail=detail)
    return {
        "success": result.success,
        "command": "health",
        "summary": result.summary,
        "suggestions": result.suggestions,
    }


@router.get("/f1/history")
async def f1_history(limit: int = 10):
    """Historial de interacciones con F1."""
    f1 = get_f1()
    return {"success": True, "history": f1.get_history(limit=limit)}


@router.post("/f1/ask")
async def f1_ask(data: dict[str, Any]):
    """Hacer una pregunta a F1."""
    f1 = get_f1()
    question = data.get("question", "")
    context = data.get("context", "")
    if not question:
        return {"success": False, "error": "question is required"}
    response = f1.ask(question, context)
    return {"success": True, "response": response}


@router.get("/notifications")
async def get_notifications(limit: int = 20, level: str = "normal"):
    """Historial de notificaciones inteligentes."""
    notifier = get_intelligent_notifier()
    if level == "essential":
        notifier.user_level = DetailLevel.ESSENTIAL
    elif level == "debug":
        notifier.user_level = DetailLevel.DEBUG
    else:
        notifier.user_level = DetailLevel.NORMAL
    history = notifier.get_history(limit=limit)
    stats = notifier.get_stats()
    return {
        "success": True,
        "notifications": history,
        "stats": stats,
        "total": len(history),
    }


@router.post("/notifications/digest")
async def trigger_digest():
    """Forzar envío de digest de notificaciones."""
    notifier = get_intelligent_notifier()
    digest = notifier.maybe_send_digest(force=True)
    return {"success": True, "digest": digest or []}


@router.get("/notifications/stats")
async def notification_stats():
    """Estadísticas del sistema de notificaciones inteligentes."""
    notifier = get_intelligent_notifier()
    return {"success": True, "stats": notifier.get_stats()}
