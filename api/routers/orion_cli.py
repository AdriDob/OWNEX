"""ORION CLI + F1 API — command center and assistant endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger("orion.cli.api")
router = APIRouter(prefix="/api/cli", tags=["orion_cli"])


@router.get("/doctor")
async def cli_doctor(
    component: str = Query("all", description="Component to check: all, database, api, pipeline, evidence, verdicts, reports, ai, quick_wins, replay, screenshot, adaptive, timeline, memory, operations"),
    fix: bool = Query(False, description="Attempt auto-fix if issues found"),
):
    """Run system doctor diagnostics (equivalent to 'orion doctor')."""
    from datetime import UTC, datetime
    from cores.operations import get_operations_manager
    
    ops = get_operations_manager()
    result = await ops.run_doctor(component=component, fix=fix)
    
    return {
        "success": True,
        "command": "doctor",
        "summary": result.get("summary", "Doctor check completed"),
        "details": result,
    }


@router.get("/help")
async def cli_help(command: str = ""):
    """Lista de comandos disponibles."""
    return {"success": True, "command": "help", "summary": "OWNEX CLI v5.1.0 operativo"}


@router.get("/status")
async def cli_status(detalles: bool = Query(False), debug: bool = Query(False)):
    """Estado general del sistema."""
    return {
        "success": True,
        "command": "status",
        "summary": "OWNEX v5.1.0 running",
        "debug": debug,
    }


@router.get("/daily")
async def cli_daily(detalles: bool = Query(False), debug: bool = Query(False)):
    """Briefing diario completo."""
    return {
        "success": True,
        "command": "daily",
        "summary": "Daily brief placeholder",
    }


@router.post("/hunt")
async def cli_hunt(data: dict[str, Any] | None = None):
    """Activar cacería de vulnerabilidades."""
    return {"success": True, "command": "hunt", "summary": "Hunt mode placeholder"}


@router.post("/trade")
async def cli_trade():
    """Activar trading automatizado."""
    return {"success": True, "command": "trade", "summary": "Trade mode placeholder"}


@router.get("/revenue")
async def cli_revenue(detalles: bool = Query(False), debug: bool = Query(False)):
    """Estado financiero y revenue actual."""
    return {"success": True, "command": "revenue", "summary": "Revenue placeholder"}


@router.post("/max")
async def cli_max():
    """MAX REVENUE MODE."""
    return {"success": True, "command": "max", "summary": "Max revenue placeholder"}


@router.get("/health")
async def cli_health(detalles: bool = Query(False), debug: bool = Query(False)):
    """Salud del sistema y servicios."""
    return {"success": True, "command": "health", "summary": "OWNEX healthy"}


@router.get("/doctor")
async def cli_doctor(verbose: bool = Query(False)):
    """Run system diagnostics (ownex doctor)."""
    from cores.operations import get_operations_manager
    
    ops = get_operations_manager()
    report = await ops.run_doctor(verbose=verbose)
    
    return {
        "success": report.overall_healthy,
        "command": "doctor",
        "summary": report.summary,
        "healthy": report.overall_healthy,
        "checks": [
            {
                "name": c.name,
                "passed": c.passed,
                "message": c.message,
                "severity": c.severity,
                "details": c.details,
            }
            for c in report.checks
        ],
        "recommendations": report.recommendations,
        "timestamp": report.timestamp.isoformat(),
    }


@router.get("/dashboard")
async def cli_dashboard():
    """Get dashboard data."""
    from cores.dashboard import get_dashboard_api
    
    api = get_dashboard_api()
    return await api.get_dashboard_data()


@router.get("/f1/history")
async def f1_history(limit: int = 10):
    """Historial de interacciones con F1."""
    return {"success": True, "history": []}


@router.post("/f1/ask")
async def f1_ask(data: dict[str, Any]):
    """Hacer una pregunta a F1."""
    question = data.get("question", "")
    if not question:
        return {"success": False, "error": "question is required"}
    return {"success": True, "response": "F1 response placeholder"}


@router.get("/notifications")
async def get_notifications(limit: int = 20, level: str = "normal"):
    """Historial de notificaciones inteligentes."""
    return {"success": True, "notifications": [], "stats": {}, "total": 0}


@router.post("/notifications/digest")
async def trigger_digest():
    """Forzar envío de digest de notificaciones."""
    return {"success": True, "digest": []}


@router.get("/notifications/stats")
async def notification_stats():
    """Estadísticas del sistema de notificaciones inteligentes."""
    return {"success": True, "stats": {}}
