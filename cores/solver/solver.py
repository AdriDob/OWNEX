"""Universal Solver — OWNEX resolves qualsiasi dubbio, problema o tarea.

Obiettivo: transformar "tengo una duda / un problema / necesito hacer X" en una
respuesta accionable con contexto real del sistema. NO es otro motor de chat:
clasifica la intención y delega al mejor motor existente (OAR chat, opencode
bridge, knowledge, workbank/daily-digest), y siempre cierra con una NEXT ACTION
con superficie exacta (ruta/endpoint).

Regole (Regla de Oro / One Source of Truth):
- No duplica motores: reutiliza copilot_chat (OAR), OpenCodeBridge.propose,
  KnowledgeIndex.search, workbank y daily_digest.
- Nunca inventa: sin datos reales → UNKNOWN visible; sin evidencia → no accion.
- Human Gate: acciones irreversibles nunca se ejecutan acá (solo proponer).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("ownex.solver")

# ── Intención ────────────────────────────────────────────────────────────

_EXPLAIN_MARKERS = (
    "cómo funciona",
    "que es ",
    "qué es",
    "explica",
    "qué significa",
    "qué quiere decir",
    "dónde está",
    "dónde esta",
    "cómo hago para saber",
)
_ACTION_MARKERS = (
    "implementa",
    "refactor",
    "escribe código",
    "corregí",
    "corrige",
    "fix ",
    "fixeá",
    "claim ",
    "submit ",
    "aplicá",
    "publicá",
    "creá un",
    "hacé un",
)

_INTENT_KEYWORDS = {
    "task_code": (
        "code",
        "código",
        "codigo",
        "implementa",
        "implementar",
        "refactor",
        "bug fix",
        "fix this",
        "crea función",
        "repositorio",
        "repo",
        "pr ",
        "pull request",
        "escribe",
        "programa",
    ),
    "task_platform": (
        "algora",
        "fiverr",
        "opire",
        "issuehunt",
        "bounty",
        "workbank",
        "gig",
        "claim",
        "submit",
        "aplicar",
        "entregar",
        "publicar",
    ),
    "system_state": (
        "estado",
        "salud",
        "health",
        "revenue",
        "pagos",
        "capital",
        "pendiente",
        "qué hay",
        "qué pasa",
        "que hay",
        "que pasa",
        "status",
        "ledger",
        "cobros",
    ),
    "planning": ("plan", "objetivo", "meta", "marcha", "estrategia", "cómo llego", "roadmap", "semanas", "escalar"),
    "knowledge": (
        "qué es",
        "explicar",
        "cómo funciona",
        "qué significa",
        "documentación",
        "dónde está",
        "encuentra",
        "busca",
    ),
}


@dataclass
class SolveRequest:
    message: str
    history: list[dict[str, str]] = field(default_factory=list)
    persona: str = "copilot"


@dataclass
class SolveResult:
    category: str
    answer: str
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    next_action: dict[str, Any] = field(default_factory=dict)
    surfaces: list[str] = field(default_factory=list)
    needs_human_gate: bool = False


def classify_intent(message: str) -> str:
    """Clasifica la intención de la consulta (heurística determinista + OAR si dudoso).

    Prioridad: preguntas explicativas (cómo/qué es/explica) → knowledge, salvo que
    haya un verbo de acción ejecutable (implementa/refactor/claim/submit) que
    indique tarea.
    """
    msg = (message or "").lower()

    if any(m in msg for m in _EXPLAIN_MARKERS) and not any(a in msg for a in _ACTION_MARKERS):
        return "knowledge"

    hits: dict[str, int] = {}
    for intent, kws in _INTENT_KEYWORDS.items():
        hits[intent] = sum(1 for k in kws if k in msg)
    if not any(hits.values()):
        return "question"
    best, score = max(hits.items(), key=lambda kv: kv[1])
    return best if score >= 1 else "question"


def assemble_context() -> dict[str, Any]:
    """Snapshot real del sistema para fundamentar la respuesta (best-effort)."""
    ctx: dict[str, Any] = {"source": "live"}
    try:
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()
        ready = [i for i in wb._items.values() if i.status == "ready_to_deliver"]
        ctx["workbank"] = {
            "ready_to_deliver": len(ready),
            "total_potential_usd": round(sum(i.reward for i in ready), 0),
            "items": [
                {"title": i.title[:70], "platform": i.platform, "reward": i.reward, "url": i.url} for i in ready[:5]
            ],
        }
    except Exception:
        pass
    try:
        from cores.first_money.tracker import get_first_money_tracker

        t = get_first_money_tracker()
        plan = t.get_march2027_plan()
        ctx["economic"] = {
            "target_50k": plan["target_usd"],
            "gap_50k": plan["gap_usd"],
            "weekly_required": plan["weekly_required"],
            "current_earned": plan["current_earned"],
            "ladder": plan["ladder"][:3],
        }
    except Exception:
        pass
    ctx["health"] = {"level": "consultar /api/system/pc-health"}
    return ctx


def search_knowledge(query: str, limit: int = 3) -> list[dict[str, Any]]:
    """Busca en el vault de conocimiento (index local) — best-effort, nunca raisea."""
    try:
        from cores.knowledge.index import get_knowledge_index

        idx = get_knowledge_index()
        notes = idx.list_notes(limit=40) or []
        kw = (query or "").lower()
        scored = []
        for n in notes:
            title = str(n.get("name") or n.get("title") or "")
            if kw in title.lower():
                scored.append(n)
        return scored[:limit] if scored else notes[:limit]
    except Exception:
        return []


async def solve(message: str, history: list[dict[str, str]] | None = None, persona: str = "copilot") -> dict[str, Any]:
    """Resuelve una consulta: contexto real + delegación al motor correcto + next action."""
    req = SolveRequest(message=message, history=history or [], persona=persona)
    intent = classify_intent(req.message)
    ctx = assemble_context()

    # Candidatos de conocimiento local para duda/knowledge
    ingredients: list[dict[str, Any]] = []
    surfaces: list[str] = []
    needs_human_gate = False
    next_action: dict[str, Any] = {}

    if intent == "knowledge":
        matches = search_knowledge(req.message)
        ingredients = [{"kind": "knowledge", "items": matches[:3]}] if matches else [{"kind": "knowledge", "items": []}]
        surfaces.append("GET /api/knowledge/search?q=" + req.message[:40])

    # Respuesta de IA con contexto (si hay IA disponible, degrade honesto)
    answer = ""
    ia_note = ""
    try:
        from api.routers import copilot

        model = copilot.ChatRequest(message=req.message, history=[copilot.ChatMessage(**h) for h in req.history])
        result = await copilot.copilot_chat(model)
        answer = str(result.get("response") or result.get("answer") or "")
    except Exception as exc:
        logger.debug("solver IA degrade: %s", exc)
        answer = ""
        ia_note = " (IA no disponible ahora — respuesta basada en estado local)"

    # Next action según intención
    if intent == "task_code":
        surfaces.append("POST /api/copilot/execute (propose → approve → run) · POST /api/chat/execute")
        needs_human_gate = True
        next_action = {
            "what": "Preparar propuesta de cambio de código en el repositorio",
            "why": "Cambio irreversible sobre código → Human Gate obligatorio",
            "surface": "POST /api/copilot/execute · method=propose",
            "expected": "Plan dif dif + archivos a tocar; luego APPROVE para ejecutar",
            "needs_human": True,
        }
    elif intent == "task_platform":
        surfaces.append("GET /api/daily-digest (best_action pago) · POST /api/direct-work/recommend")
        next_action = {
            "what": "Ejecutar la oportunidad con mayor EV/h del digest de hoy",
            "why": "El digest ya ordena por NET CASH / HUMAN HOUR",
            "surface": "GET /api/daily-digest → best_action → aprobar en WorkBank",
            "expected": "1 delivery aprobado y ejecutado hacia el cobro",
            "needs_human": True,
        }
        needs_human_gate = True
    elif intent == "system_state":
        surfaces.append("GET /api/daily-digest · GET /api/system/pc-health · GET /api/capital/snapshot")
        if ctx.get("economic"):
            m = ctx["economic"]
            next_action = {
                "what": f"Avanzar hacia el hito $50k (gap ${m['gap_50k']:,}, ritmo ${m['weekly_required']}/sem)",
                "why": "Brecha económica a marzo 2027 medida en vivo",
                "surface": "GET /api/daily-digest → best_action",
                "expected": "Acción de mayor EV/h ejecutada",
                "needs_human": False,
            }
    elif intent == "planning":
        surfaces.append("GET /first-money/march2027-plan")
        next_action = {
            "what": "Seguir la escalera mensual del plan marzo 2027",
            "why": "Objetivo $50k agresivo razonable, ataque $100k",
            "surface": "GET /first-money/march2027-plan → weekly_checklist",
            "expected": "Cumplir ritmo semanal del motor más cercano",
            "needs_human": False,
        }
    else:  # question
        surfaces.append("GET /api/chat (copilot) · GET /platform-guides/guide/zero-to-hundred")
        next_action = {
            "what": "Reformular la duda con más contexto o consultar guías 0→100",
            "why": "Respuesta base lista; profundizar con contexto específico",
            "surface": "POST /api/chat · persona=copilot",
            "expected": "Respuesta precisa con datos del sistema",
            "needs_human": False,
        }

    result = SolveResult(
        category=intent,
        answer=(answer or "").strip()
        or "No pude generar respuesta IA; consultá el estado local directamente." + ia_note,
        ingredients=ingredients,
        next_action=next_action,
        surfaces=surfaces,
        needs_human_gate=needs_human_gate,
    )
    logger.info("[SOLVER] intent=%s surfaces=%s gate=%s", intent, len(surfaces), needs_human_gate)
    return {
        "intent": result.category,
        "answer": result.answer,
        "context": ctx,
        "ingredients": result.ingredients,
        "next_action": result.next_action,
        "surfaces": result.surfaces,
        "needs_human_gate": result.needs_human_gate,
        "ia_available": bool(answer),
    }
