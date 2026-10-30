"""Help Center API — In-app contextual help.

Endpoints:
- GET /api/help/quick-answers — Live answers to the most common operational
  questions, computed from actual system state (not static text).
- GET /api/help/workflows — Guided step-by-step recipes for the key daily
  loops (first money, daily execution, delivery, platform onboarding).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/help", tags=["help-center"])
logger = logging.getLogger("ownex.api.help_center")


def _workbank_counts() -> dict[str, int] | None:
    try:
        from cores.direct_work_engine.workbank import get_workbank

        bank = get_workbank()
        ready = list(bank.best_ready(1000))
        needs = list(bank.needs_access()) if hasattr(bank, "needs_access") else []
        return {"ready": len(ready), "needs_access": len(needs)}
    except Exception as exc:
        logger.debug("workbank counts failed: %s", exc)
        return None


def _setup_progress() -> dict[str, Any] | None:
    try:
        from cores.setup.checklist import get_setup_checklist

        status = get_setup_checklist().status()
        return {
            "pct": status.get("complete_pct", 0),
            "complete": status.get("complete", False),
            "next_task": status.get("next_task"),
        }
    except Exception as exc:
        logger.debug("setup progress failed: %s", exc)
        return None


def _ai_status() -> dict[str, Any] | None:
    try:
        from api.routers.settings_ai import get_config as _ai_config

        return _ai_config()
    except Exception as exc:
        logger.debug("ai status failed: %s", exc)
        return None


def _brief_actions_count() -> int:
    """Number of ranked actions in today's brief (cheap re-use of the engine)."""
    try:
        from cores.direct_work_engine.workbank import get_workbank

        bank = get_workbank()
        return len(list(bank.best_ready(100)))
    except Exception:
        return 0


def _capital() -> dict[str, Any] | None:
    try:
        from database import db, models

        session = db.SessionLocal()
        try:
            verified = 0.0
            pending = 0.0
            for r in session.query(models.Report).all():
                amount = float(getattr(r, "bounty_amount", 0) or 0)
                status = (getattr(r, "status", "") or "").lower()
                if status in ("paid", "resolved", "bounty_paid"):
                    verified += amount
                elif status in ("triaged", "reported", "pending"):
                    pending += amount
            return {"verified_usd": verified, "pending_usd": pending}
        finally:
            session.close()
    except Exception as exc:
        logger.debug("capital snapshot failed: %s", exc)
        return None


def build_quick_answers() -> dict[str, Any]:
    """Contextual answers computed from live system state."""
    answers: list[dict[str, Any]] = []
    generated_at = datetime.now(UTC).isoformat()

    wb = _workbank_counts()
    setup = _setup_progress()
    ai = _ai_status()
    capital = _capital()
    _ = _brief_actions_count()  # warm the cache; kept cheap on purpose

    # ¿Qué hago ahora?
    now_answer: dict[str, Any]
    if wb and wb["ready"] > 0:
        now_answer = {
            "question": "¿Qué hago ahora?",
            "answer": (
                f"Tenés {wb['ready']} entrega(s) lista(s) en el Work Bank. "
                "Enviarlas es la acción de mayor valor: convierte trabajo preparado en dinero real."
            ),
            "action": {"label": "Ir a Work Queue", "path": "/operations/work-queue"},
            "priority": "high",
        }
    elif setup and not setup["complete"]:
        task = setup.get("next_task") or {}
        now_answer = {
            "question": "¿Qué hago ahora?",
            "answer": (
                f"Tu setup está al {setup['pct']}%. La tarea de hoy es: "
                f"{task.get('title', 'completar el checklist de configuración')}. "
                "Cada ítem desbloquea fuentes de ingreso adicionales."
            ),
            "action": {"label": "Abrir Setup Checklist", "path": "/setup/checklist"},
            "priority": "high",
        }
    else:
        now_answer = {
            "question": "¿Qué hago ahora?",
            "answer": (
                "Abrí el Daily Brief en el Command Center: rankea tus oportunidades "
                "por EV/hora y te dice el próximo paso concreto de cada una."
            ),
            "action": {"label": "Ver Daily Brief", "path": "/"},
            "priority": "medium",
        }
    answers.append(now_answer)

    # ¿Cuánto llevo ganado?
    if capital is not None:
        answers.append(
            {
                "question": "¿Cuánto llevo ganado?",
                "answer": (
                    f"Verificado: ${capital['verified_usd']:.2f} · Pendiente de pago: "
                    f"${capital['pending_usd']:.2f}. El detalle por plataforma vive en Capital → Ledger."
                ),
                "action": {"label": "Ver Capital", "path": "/capital"},
                "priority": "medium",
            }
        )
    else:
        answers.append(
            {
                "question": "¿Cuánto llevo ganado?",
                "answer": "Todavía no hay pagos registrados. Cuando confirmes un payout, aparece acá y en Capital.",
                "action": {"label": "Ver Capital", "path": "/capital"},
                "priority": "low",
            }
        )

    # ¿Por qué no hay entregas listas?
    if wb is not None and wb["ready"] == 0:
        msg = (
            "El Work Bank no tiene entregas listas. OWNEX sigue descubriendo; "
            "mientras tanto podés conectar plataformas para ampliar fuentes."
        )
        if wb["needs_access"] > 0:
            msg = (
                f"Hay {wb['needs_access']} trabajo(s) bloqueado(s) porque falta conectar la plataforma. "
                "Conectarlas los desbloquea y vuelven a la cola de entregas."
            )
        answers.append(
            {
                "question": "¿Por qué no hay entregas listas?",
                "answer": msg,
                "action": {"label": "Integraciones", "path": "/integrations/connections"},
                "priority": "medium",
            }
        )

    # ¿La IA está funcionando?
    if ai is not None:
        available = bool(ai.get("available"))
        answers.append(
            {
                "question": "¿La IA está funcionando?",
                "answer": (
                    f"Sí — proveedor activo: {ai.get('active_provider', 'desconocido')} "
                    f"(modelo: {ai.get('model') or 'default'})."
                    if available
                    else "No. El proveedor de IA configurado no responde; el análisis automático está en fallback. "
                    "Revisá Settings → IA o verificá Ollama."
                ),
                "action": {"label": "Configurar IA", "path": "/operations/settings"},
                "priority": "critical" if not available else "low",
            }
        )

    return {"generated_at": generated_at, "answers": answers}


# Guided workflows: the recurring loops of the system.
_WORKFLOWS: list[dict[str, Any]] = [
    {
        "id": "daily-loop",
        "title": "Loop diario: de abrir OWNEX a generar ingresos",
        "when": "Cada mañana (10-15 min de gestión + tiempo de ejecución)",
        "steps": [
            {"n": 1, "text": "Abrí el Command Center (/) y mirá el Daily Brief: acción #1 rankeada por EV/hora.", "path": "/"},
            {"n": 2, "text": "Ejecutá la One Action del día. Si requiere aprobación tuya, aparece en 'Necesitan tu aprobación'.", "path": "/operations/work-queue"},
            {"n": 3, "text": "Si hay entregas listas en el Work Bank, envialas antes de empezar trabajo nuevo.", "path": "/operations/work-queue"},
            {"n": 4, "text": "Al terminar, marcá las tareas completadas en la cola para que el ranking aprenda.", "path": "/operations/work-queue"},
        ],
    },
    {
        "id": "first-money",
        "title": "Primer ingreso: $0 → primer payout",
        "when": "Una vez, al empezar",
        "steps": [
            {"n": 1, "text": "Completá el Setup Checklist — cada ítem desbloquea plataformas o fuentes.", "path": "/setup/checklist"},
            {"n": 2, "text": "Conectá al menos una plataforma en Integraciones → Conexiones.", "path": "/integrations/connections"},
            {"n": 3, "text": "Seguí la guía First Money: tareas zero-barrier que no requieren historial ni aprobación previa.", "path": "/operations/first-money"},
            {"n": 4, "text": "Cuando la plataforma pague, registrá el payout en Capital para que el sistema trackee tu progreso real.", "path": "/capital"},
        ],
    },
    {
        "id": "delivery",
        "title": "Entregar trabajo del Work Bank",
        "when": "Cuando el Work Bank tenga items 'ready_to_deliver'",
        "steps": [
            {"n": 1, "text": "Abrí la Work Queue y filtrá por items listos.", "path": "/operations/work-queue"},
            {"n": 2, "text": "Revisá el paquete preparado (draft, términos, match de perfil) antes de enviar.", "path": "/operations/work-queue"},
            {"n": 3, "text": "Enviá en la plataforma con el botón de entrega; OWNEX marca el item como delivered.", "path": "/operations/work-queue"},
            {"n": 4, "text": "Seguí el pago en Capital → Ledger hasta confirmarlo.", "path": "/operations/ledger"},
        ],
    },
    {
        "id": "platform-onboarding",
        "title": "Sumar una plataforma nueva",
        "when": "Cuando quieras ampliar fuentes de oportunidades",
        "steps": [
            {"n": 1, "text": "Mirá el ranking '¿Dónde trabajo hoy?': muestra rate efectivo y % de readiness por plataforma.", "path": "/"},
            {"n": 2, "text": "Abrí la guía de onboarding de esa plataforma y completá el registro.", "path": "/operations/platforms"},
            {"n": 3, "text": "Guardá credenciales en Integraciones → Cuentas para desbloquear la entrega automática.", "path": "/integrations/accounts"},
            {"n": 4, "text": "El readiness sube y la plataforma empieza a aparecer en tu radar con su rate real.", "path": "/targets/prioritization"},
        ],
    },
    {
        "id": "troubleshoot-ai",
        "title": "La IA no responde: diagnóstico rápido",
        "when": "Cuando veas la alerta 'IA no disponible' o respuestas vacías del Copilot",
        "steps": [
            {"n": 1, "text": "Verificá el proveedor activo en Settings → IA (estado + modelo).", "path": "/operations/settings"},
            {"n": 2, "text": "Si usás Ollama local: corroborá que el servicio esté corriendo y el modelo descargado.", "path": "/operations/settings"},
            {"n": 3, "text": "Cambiá a un proveedor alternativo y guardá; el sistema revalida la disponibilidad al instante.", "path": "/operations/settings"},
            {"n": 4, "text": "Si persiste, revisá el Flight Recorder (logs en vivo) para el error exacto.", "path": "/"},
        ],
    },
]


@router.get("/workflows")
async def list_workflows() -> dict[str, Any]:
    """Guided recipes for the recurring daily loops."""
    return {"workflows": _WORKFLOWS, "total": len(_WORKFLOWS)}


@router.get("/quick-answers")
async def quick_answers() -> dict[str, Any]:
    """Live answers to common questions, computed from real system state."""
    try:
        return build_quick_answers()
    except Exception as exc:
        logger.warning("quick-answers generation failed: %s", exc, exc_info=True)
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "answers": [
                {
                    "question": "¿Qué hago ahora?",
                    "answer": "Abrí el Command Center y seguí el Daily Brief.",
                    "action": {"label": "Command Center", "path": "/"},
                    "priority": "medium",
                }
            ],
        }
