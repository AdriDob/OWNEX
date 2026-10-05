"""Today — el plan único: qué hacer ahora, y quién lo hace.

Responde en UNA llamada lo que el usuario pidió: "exactamente todo lo que
tenga que hacer, y la mayor parte en automático".

- Arranca en el día 1: sin datos, sin config, sin PAID — igual devuelve plan.
- Cada paso declara `owner`: "system" (ya corre solo) o "human" (tu clic).
- Orden real de desbloqueo: cobrar necesita rail; cobrar necesita trabajo;
  el trabajo sale del ranking. Un paso bloquea al siguiente y lo dice.
- Best-effort por sección: nunca 500, nunca inventa números.

Puro salvo los imports best-effort: sin red, sin escrituras.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.mission_hub.today")

# Bloqueos de primer ingreso, en orden de dependencia real.
# owner="human" = requiere un clic del usuario (irreducible por diseño).
BLOCKER_SEQUENCE: tuple[dict[str, Any], ...] = (
    {
        "id": "payout_rail",
        "owner": "human",
        "title": "Configurá 1 método de cobro",
        "why": "Sin rail configurado, OWNEX trata todo como no cobrable (no inventa).",
        "endpoint": "POST /api/payment-compat/configured",
        "url": "/capital",
        "est_minutes": 10,
        "blocks": "todo lo demás: sin rail no hay P(CASH) real",
    },
    {
        "id": "platform_account",
        "owner": "human",
        "title": "Creá tu cuenta en la plataforma que el ranking te marque",
        "why": "El ranking ya sabe cuál; la cuenta la creás vos (identidad/ToS).",
        "endpoint": "GET /api/applications/platform-ranking",
        "url": "/operations/platforms",
        "est_minutes": 15,
        "blocks": "entregar trabajo",
    },
    {
        "id": "first_delivery",
        "owner": "human",
        "title": "Aprobá la primera entrega parqueada",
        "why": "El daily loop deja 3 listos; aprobar es tu clic (Human Gate).",
        "endpoint": "POST /direct-work/workbank/{id}/deliver/approve",
        "url": "/operations/work-queue",
        "est_minutes": 30,
        "blocks": "primer ingreso",
    },
)

# Lo que el sistema YA hace solo. Si esto no corre, el plan lo dice.
AUTOMATED_DAILY: tuple[dict[str, str], ...] = (
    {"id": "discovery", "what": "Escanea plataformas y curates oportunidades"},
    {"id": "workbank_cycle", "what": "Arma el Work Bank y deja jobs listos para entregar"},
    {"id": "auto_submit_sweep", "what": "Revisa findings confirmados contra el submit-gate"},
    {"id": "review_digest", "what": "Avisa si hay cola de revisión para vos"},
    {"id": "autopilot", "what": "Pausa canales muertos / mata productos sin ventas (evidencia dura)"},
    {"id": "calibration", "what": "Recalibra P(CASH) y neto/hora con tus outcomes"},
)


def _owner_badge(owner: str) -> str:
    return "AUTOMÁTICO" if owner == "system" else "TU CLOQUE"


def _human_tasks(checklist_status: dict[str, Any]) -> list[dict[str, Any]]:
    """Tareas de config que el checklist detecta y vos ejecutás."""
    out: list[dict[str, Any]] = []
    for item in (checklist_status.get("pending") or [])[:6]:
        out.append(
            {
                "id": f"config:{item.get('id')}",
                "owner": "human",
                "title": item.get("title") or item.get("id"),
                "why": item.get("how_to") or item.get("why") or "",
                "est_minutes": item.get("est_minutes"),
                "url": item.get("url"),
                "endpoint": f"GET /api/setup/checklist/status#{item.get('id')}",
                "done": False,
                "badge": _owner_badge("human"),
            }
        )
    return out


def _rails_configured() -> tuple[int, bool]:
    try:
        from cores.payment_compat.engine import get_payment_compatibility_engine

        accounts = get_payment_compatibility_engine().get_configured_accounts()
        return len(accounts), bool(accounts)
    except Exception:
        return 0, False


def _ready_to_deliver() -> tuple[int, float, Any]:
    """(count, reward_sum_usd, top_item) del Work Bank real."""
    try:
        from cores.direct_work_engine.workbank import get_workbank

        bank = get_workbank()
        ready = [i for i in bank._items.values() if i.status == "ready_to_deliver"]
        if not ready:
            return 0, 0.0, None
        top = max(ready, key=lambda i: i.reward or 0)
        return len(ready), round(sum(i.reward or 0 for i in ready), 2), top
    except Exception:
        return 0, 0.0, None


def _pending_review() -> tuple[int, Any]:
    try:
        from cores.review_queue import build_review_queue

        data = build_review_queue(limit=20).to_dict()
        items = data.get("items") or data.get("queue") or []
        return len(items), (items[0] if items else None)
    except Exception:
        return 0, None


def _paid_outcomes() -> int:
    """Outcomes PAID reales. 0 = P(CASH) todavía es UNKNOWN (se dice, no se disimula)."""
    try:
        from cores.economic_feedback.engine import get_economic_feedback_engine

        snap = get_economic_feedback_engine().build_snapshot()
        return int(getattr(snap, "outcomes", 0) or 0)
    except Exception:
        return 0


def _paid_total_usd() -> float | None:
    """Total PAID real. None = sin dato (UNKNOWN ≠ 0.0)."""
    try:
        from cores.revenue_tracker.tracker import get_revenue_tracker

        metrics = get_revenue_tracker().metrics
        total = float(getattr(metrics, "total_earnings", 0) or 0)
        return round(total, 2) if total > 0 else None
    except Exception:
        return None


def build_today_plan() -> dict[str, Any]:
    """Plan del día: qué hacés vos, qué corre solo, y qué falta para cobrar."""
    out: dict[str, Any] = {"who": "TÚ (monitoreo y validación) + OWNEX (todo lo demás)"}

    # ── 1. Estado real (medido, nunca inventado) ──
    rails_n, rails_ok = _rails_configured()
    ready_n, ready_usd, ready_top = _ready_to_deliver()
    review_n, review_top = _pending_review()
    paid_n = _paid_outcomes()
    checklist: dict[str, Any] = {}
    try:
        from cores.setup.checklist import get_setup_checklist

        checklist = get_setup_checklist().status()
    except Exception as exc:
        logger.debug("today: checklist no disponible: %s", exc)

    out["state"] = {
        "payout_rails_configured": rails_n,
        "ready_to_deliver": ready_n,
        "ready_to_deliver_usd": ready_usd if ready_n else None,
        "review_queue": review_n,
        "config_complete_pct": checklist.get("complete_pct"),
        "paid_outcomes": paid_n,
        "p_cash_state": "MEASURED" if paid_n else "UNKNOWN (sin PAID propio todavía)",
        "day1_ok": rails_ok,  # el día 1 es útil incluso vacío
    }

    # ── 2. Lo que YA corre solo ──
    out["automatic"] = [
        {"id": a["id"], "what": a["what"], "owner": "system", "badge": _owner_badge("system")} for a in AUTOMATED_DAILY
    ]

    # ── 3. Tu plan, en orden de dependencia real ──
    plan: list[dict[str, Any]] = []
    if not rails_ok:
        plan.append(dict(BLOCKER_SEQUENCE[0], done=False, badge=_owner_badge("human")))

    if review_n:
        top = review_top or {}
        plan.append(
            {
                "id": "validate_review",
                "owner": "human",
                "title": f"Validá {review_n} finding(s) en la cola",
                "why": "El gate ya calculó veredicto por item; aprobar es tu decisión.",
                "endpoint": "GET /api/system/review",
                "url": "/review",
                "est_minutes": max(5, review_n * 5),
                "top_item": {"id": top.get("id"), "label": top.get("label")} if top else None,
                "done": False,
                "badge": _owner_badge("human"),
            }
        )

    if ready_n:
        plan.append(
            {
                "id": "approve_delivery",
                "owner": "human",
                "title": f"Aprobá la entrega de {ready_n} job(s) listos ({f'${ready_usd:.0f}' if ready_usd else 'sin monto declarado'})",
                "why": "El daily loop ya preparó los paquetes; el envío final es tu clic.",
                "endpoint": "POST /direct-work/workbank/{id}/submit",
                "url": "/operations/work-queue",
                "est_minutes": max(15, ready_n * 20),
                "top_item": {"id": ready_top.id, "title": ready_top.title, "reward": ready_top.reward}
                if ready_top
                else None,
                "done": False,
                "badge": _owner_badge("human"),
            }
        )

    if not ready_n and not review_n and rails_ok:
        plan.append(
            {
                "id": "run_cycle",
                "owner": "system",
                "title": "Correr el ciclo del Work Bank",
                "why": "No hay nada listo todavía; el sistema arma el siguiente lote solo.",
                "endpoint": "POST /direct-work/workbank/cycle",
                "url": "/operations/work-queue",
                "est_minutes": 0,
                "done": False,
                "badge": _owner_badge("system"),
            }
        )

    plan.extend(_human_tasks(checklist))
    out["your_plan"] = plan

    # ── 4. El número: honesto desde el día 1 ──
    out["money"] = {
        "expected_now_usd": ready_usd if ready_n else None,  # EXPECTED, no cobrado
        "paid_usd": _paid_total_usd(),  # None = UNKNOWN, jamás 0.0 disfrazado
        "label": "EXPECTED (dinero en el banco, no cobrado)" if ready_n else "sin nada preparado todavía",
    }
    out["next_step"] = (
        plan[0] if plan else {"id": "idle", "title": "Nada pendiente: el sistema trabaja solo", "owner": "system"}
    )
    out["next_step"]["badge"] = out["next_step"].get("badge") or _owner_badge(out["next_step"].get("owner", "human"))
    return out


# ── HTTP ───────────────────────────────────────────────────────────

from datetime import UTC, datetime  # noqa: E402

from fastapi import APIRouter  # noqa: E402

router = APIRouter(prefix="/today", tags=["today"])


@router.get("")
async def today() -> dict[str, Any]:
    """El plan del día: qué hacés vos y qué corre solo. Best-effort, nunca 500."""
    try:
        plan = build_today_plan()
        plan["generated_at"] = datetime.now(UTC).isoformat()
        return plan
    except Exception as exc:
        logger.warning("today: plan no disponible: %s", exc)
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "who": "TÚ (monitoreo y validación) + OWNEX (todo lo demás)",
            "error": str(exc)[:200],
            "your_plan": [],
            "automatic": [
                {"id": a["id"], "what": a["what"], "owner": "system", "badge": "AUTOMÁTICO"} for a in AUTOMATED_DAILY
            ],
            "next_step": {
                "id": "retry",
                "title": "Plan no disponible: revisá el health del sistema",
                "owner": "human",
                "badge": "TU CLOQUE",
                "endpoint": "GET /api/system/health",
            },
        }
