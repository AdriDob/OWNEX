"""Alerts API — Endpoints for real-time alert system.

Endpoints:
- GET /api/alerts/status — Current alert system status
- GET /api/alerts/active — Get all active alerts
- POST /api/alerts/create — Create a new alert
- POST /api/alerts/resolve — Resolve an alert
- GET /api/alerts/category/{category} — Get alerts by category
- POST /api/alerts/sweep — Auto-generate warnings from current system state
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.financial_intelligence.alert_system import (
    AlertCategory,
    AlertType,
    get_alert_system,
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

# ── Sweep state (avoid duplicate warnings on every poll) ──
_sweep_lock = threading.Lock()
_last_sweep_ids: set[str] = set()


def _workbank_snapshot() -> dict[str, Any] | None:
    """Best-effort workbank counts (ready / needs_access)."""
    try:
        from cores.direct_work_engine.workbank import get_workbank

        bank = get_workbank()
        ready = list(getattr(bank, "best_ready", lambda limit=1000: [])(5))
        needs = list(bank.needs_access()) if hasattr(bank, "needs_access") else []
        return {"ready": len(ready), "needs_access": len(needs)}
    except Exception as exc:
        logger.debug("workbank snapshot failed: %s", exc)
        return None


def _pending_approvals() -> list[dict[str, str]]:
    """WorkerCore items blocked on human action."""
    try:
        from cores.worker_core import get_worker_core

        worker = get_worker_core()
        return [
            {"id": wid, "title": witem.title, "description": witem.human_action_description or "Approval needed"}
            for wid, witem in worker.work_items.items()
            if witem.human_action_required
        ]
    except Exception as exc:
        logger.debug("pending approvals scan failed: %s", exc)
        return []


def _setup_pending() -> dict[str, Any] | None:
    """Setup checklist progress (complete flag + next task)."""
    try:
        from cores.setup.checklist import get_setup_checklist

        status = get_setup_checklist().status()
        return {
            "complete": status.get("complete", False),
            "pct": status.get("complete_pct", 0),
            "next_task": status.get("next_task"),
        }
    except Exception as exc:
        logger.debug("setup checklist status failed: %s", exc)
        return None


def _ai_available() -> bool | None:
    try:
        from cores.ai.provider import get_registry

        return bool(get_registry().get_provider().is_available())
    except Exception as exc:
        logger.debug("AI availability check failed: %s", exc)
        return None


def _last_scan_age_hours() -> float | None:
    try:
        from database import db, models

        session = db.SessionLocal()
        try:
            last = session.query(models.ScanRun).order_by(models.ScanRun.started_at.desc()).first()
            if last is None or last.started_at is None:
                return None
            from datetime import UTC, datetime

            started = last.started_at if last.started_at.tzinfo else last.started_at.replace(tzinfo=UTC)
            return (datetime.now(UTC) - started).total_seconds() / 3600
        finally:
            session.close()
    except Exception as exc:
        logger.debug("last scan query failed: %s", exc)
        return None


def _dedup_key(title: str, detail: str) -> str:
    return f"{title}::{detail}"


def _build_sweep_alerts() -> list[dict[str, Any]]:
    """Derive actionable warnings from current system state."""
    sweep: list[dict[str, Any]] = []

    approvals = _pending_approvals()
    for item in approvals[:5]:
        sweep.append(
            {
                "type": "warning",
                "category": "approval",
                "title": "Aprobación requerida",
                "message": f"{item['title']}: {item['description']}",
                "severity": "warning",
                "priority": "high",
                "requires_action": True,
                "action_steps": ["Revisá el ítem en la Work Queue", "Aprobá o descartá para desbloquear el pipeline"],
                "ui_path": "/operations/work-queue",
                "key": _dedup_key("approval", item["id"]),
            }
        )

    wb = _workbank_snapshot()
    if wb:
        if wb["needs_access"] > 0:
            sweep.append(
                {
                    "type": "warning",
                    "category": "credentials",
                    "title": "Entregas bloqueadas por acceso",
                    "message": f"{wb['needs_access']} trabajo(s) listo(s) en el Work Bank necesitan que conectes la plataforma para poder entregarse.",
                    "severity": "warning",
                    "priority": "high",
                    "requires_action": True,
                    "action_steps": ["Conectá la plataforma desde Integraciones → Cuentas"],
                    "ui_path": "/integrations/accounts",
                    "key": _dedup_key("workbank_access", str(wb["needs_access"])),
                }
            )
        if wb["ready"] > 0:
            sweep.append(
                {
                    "type": "info",
                    "category": "ultra_fast_income",
                    "title": "Entregas listas",
                    "message": f"{wb['ready']} entrega(s) preparada(s) en el Work Bank. Enviarlas convierte EV en dinero real.",
                    "severity": "info",
                    "priority": "medium",
                    "requires_action": True,
                    "action_steps": ["Abrí la Work Queue y enviá las entregas listas"],
                    "ui_path": "/operations/work-queue",
                    "key": _dedup_key("workbank_ready", str(wb["ready"])),
                }
            )

    setup = _setup_pending()
    if setup and not setup["complete"]:
        task = setup.get("next_task") or {}
        sweep.append(
            {
                "type": "warning",
                "category": "system",
                "title": "Setup incompleto",
                "message": f"Configuración al {setup['pct']}%. Tarea sugerida: {task.get('title', 'completar checklist')}",
                "severity": "warning",
                "priority": "medium",
                "requires_action": False,
                "action_steps": ["Completá la tarea del día en el Setup Checklist"],
                "ui_path": "/setup/checklist",
                "key": _dedup_key("setup", str(setup["pct"])),
            }
        )

    ai = _ai_available()
    if ai is False:
        sweep.append(
            {
                "type": "error",
                "category": "system",
                "title": "IA no disponible",
                "message": "El proveedor de IA activo no responde. El análisis de oportunidades y el Copilot están en fallback.",
                "severity": "error",
                "priority": "critical",
                "requires_action": True,
                "action_steps": [
                    "Verificá Ollama (ollama list) o el proveedor configurado",
                    "Cambiá de proveedor en Settings → IA",
                ],
                "ui_path": "/operations/settings",
                "key": _dedup_key("ai_down", "provider"),
            }
        )

    age = _last_scan_age_hours()
    if age is None or age > 24:
        label = "nunca se ejecutó un scan" if age is None else f"último scan hace {age:.0f}h"
        sweep.append(
            {
                "type": "warning",
                "category": "health",
                "title": "Sin actividad de scan reciente",
                "message": f"{label.capitalize()}. Sin discovery fresco el radar de oportunidades queda desactualizado.",
                "severity": "warning",
                "priority": "medium",
                "requires_action": False,
                "action_steps": ["Revisá el scheduler o lanzá un scan manual desde Operations"],
                "ui_path": "/operations/scheduler",
                "key": _dedup_key("scan_stale", "24h"),
            }
        )

    return sweep


class SweepRequest(BaseModel):
    """Optional request body for the sweep endpoint."""

    create: bool = Field(default=True, description="Persist matching alerts in the alert system")


class CreateAlertRequest(BaseModel):
    """Request model for creating an alert."""

    type: str = Field(..., description="Alert type: error, warning, info, success, critical")
    category: str = Field(..., description="Alert category")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: str = Field(default="info", description="Severity: info, warning, error, critical")
    priority: str = Field(default="medium", description="Priority: low, medium, high, critical")
    requires_action: bool = Field(default=False, description="Whether action is required")
    action_steps: list[str] = Field(default_factory=list, description="Steps to resolve")
    ui_path: str = Field(default="", description="UI path to resolve")
    auto_dismiss_after: int = Field(default=0, description="Auto-dismiss after N seconds (0 = no auto-dismiss)")


class ResolveAlertRequest(BaseModel):
    """Request model for resolving an alert."""

    alert_id: str = Field(..., description="Alert ID to resolve")


@router.get("/status")
async def get_alert_status() -> dict[str, Any]:
    """Get current alert system status."""
    try:
        alert_system = get_alert_system()
        return alert_system.get_status()
    except Exception as e:
        logger.error(f"Failed to get alert status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert status: {str(e)}") from e


@router.get("/active")
async def get_active_alerts(include_resolved: bool = False) -> dict[str, Any]:
    """Get all active alerts."""
    try:
        alert_system = get_alert_system()
        alerts = alert_system.get_active_alerts(include_resolved=include_resolved)
        return {
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
        }
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get active alerts: {str(e)}") from e


@router.post("/create")
async def create_alert(request: CreateAlertRequest) -> dict[str, Any]:
    """Create a new alert."""
    try:
        alert_system = get_alert_system()
        alert = alert_system.create_alert(
            type=AlertType(request.type),
            category=AlertCategory(request.category),
            title=request.title,
            message=request.message,
            severity=request.severity,
            priority=request.priority,
            requires_action=request.requires_action,
            action_steps=request.action_steps,
            ui_path=request.ui_path,
            auto_dismiss_after=request.auto_dismiss_after,
        )
        return {
            "status": "alert_created",
            "alert": alert.to_dict(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create alert: {str(e)}") from e


@router.post("/resolve")
async def resolve_alert(request: ResolveAlertRequest) -> dict[str, Any]:
    """Resolve an alert."""
    try:
        alert_system = get_alert_system()
        alert = alert_system.resolve_alert(request.alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail=f"Alert not found: {request.alert_id}")
        return {
            "status": "alert_resolved",
            "alert": alert.to_dict(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resolve alert: {str(e)}") from e


@router.post("/sweep")
async def sweep_alerts(request: SweepRequest | None = None) -> dict[str, Any]:
    """Scan system state and surface actionable warnings.

    Returns every current finding; optionally persists the new ones in the
    alert system (deduplicated per unique key) so the AlertPopup shows them.
    """
    create = request.create if request is not None else True
    findings = _build_sweep_alerts()
    created: list[dict[str, Any]] = []

    if create:
        with _sweep_lock:
            alert_system = get_alert_system()
            for item in findings:
                key = item["key"]
                if key in _last_sweep_ids:
                    continue
                _last_sweep_ids.add(key)
                try:
                    alert = alert_system.create_alert(
                        type=AlertType(item["type"]),
                        category=AlertCategory(item["category"]),
                        title=item["title"],
                        message=item["message"],
                        severity=item["severity"],
                        priority=item["priority"],
                        requires_action=item["requires_action"],
                        action_steps=item["action_steps"],
                        ui_path=item["ui_path"],
                    )
                    created.append(alert.to_dict())
                except Exception as exc:
                    logger.warning("Failed to persist sweep alert: %s", exc)

    for item in findings:
        item.pop("key", None)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "findings": findings,
        "created": created,
        "total_findings": len(findings),
        "total_created": len(created),
    }


@router.get("/category/{category}")
async def get_alerts_by_category(category: str) -> dict[str, Any]:
    """Get alerts by category."""
    try:
        alert_system = get_alert_system()
        try:
            cat = AlertCategory(category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid category: {category}") from None

        alerts = alert_system.get_alerts_by_category(cat)
        return {
            "category": category,
            "total": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alerts by category: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts by category: {str(e)}") from e
