"""Source Prep — preparación guiada para quedarte ADENTRO de cada web desde 0.

Dos capas:
1. Determinista (`build_prep_guide`): qué revisar, formato probable del
   assessment, checklist y esfuerzo por categoría. Siempre disponible, sin IA.
2. IA (`generate_ai_prep`): usa el router free 24/7 (FCC→NVIDIA→OmniRoute→
   OpenCode→Ollama) para generar un plan personalizado por plataforma con
   ejemplos concretos. Best-effort: si no hay IA, cae al guía determinista.

Propósito: que "empiezo de 0 en esta web" no sea adivinar — te dice QUÉ
estudiar, QUÉ esperan del assessment y CÓMO llegar a aprobar con asistencia.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ownex.source_prep")

# ── Guía determinista por categoría (siempre disponible, sin IA) ──

_CATEGORY_PREP: dict[str, list[dict[str, str]]] = {
    "bug_bounty": [
        {
            "topic": "Protocolo HTTP (métodos, headers, cookies, status codes)",
            "why": "El 90% de los bug bounties web vive en HTTP.",
        },
        {
            "topic": "OWASP Top 10 (IDOR, XSS, SQLi, SSRF, auth)",
            "why": "Es el checklist mental con el que empezás a buscar.",
        },
        {
            "topic": "Leer el scope del programa (in scope / out of scope)",
            "why": "Reportar fuera de scope = ban. Leer primero SIEMPRE.",
        },
        {
            "topic": "Burp Suite / navegador DevTools básico",
            "why": "Para interceptar peticiones y ver cómo responde el server.",
        },
        {
            "topic": "Cómo redactar un reporte claro (repro steps, impacto, PoC)",
            "why": "Un buen reporte se acepta 3x más que uno confuso.",
        },
    ],
    "dev_bounty": [
        {"topic": "Git esencia (branch, commit, push, PR)", "why": "El 100% de los bounties OSS se entregan por PR."},
        {
            "topic": "Leer código ajeno sin miedo (tests primero, luego lógica)",
            "why": "Los repos tienen tests que te dicen qué se espera.",
        },
        {
            "topic": "Correr el proyecto local (install + run + tests)",
            "why": "OWNEX clona y configura; vos tenés que poder correrlo.",
        },
        {
            "topic": "El lenguaje del repo (Python/Go/Rust/TS/Solidity...)",
            "why": "Leer docs del framework para escribir el fix correcto.",
        },
        {
            "topic": "Cómo escribir/ajustar tests",
            "why": "PR sin tests que pasan = merge gate. Con tests que pasan = mergeable.",
        },
        {
            "topic": "Entender el issue: qué se pide, qué se acepta",
            "why": "Resolver el problema pedido ≠ resolver un problema.",
        },
    ],
    "ai_evaluation": [
        {
            "topic": "Leer instrucciones MUY bien (rubric/guidelines)",
            "why": "Las plataformas de AI eval puntúan contra una rúbrica; seguirla es la mitad del aprobar.",
        },
        {
            "topic": "Inglés escrito claro y técnico",
            "why": "Respuestas de calidad = respuestas escritas con precisión.",
        },
        {"topic": "Tu especialidad (coding/writing/math)", "why": "El assessment mide dominio real del tema."},
        {
            "topic": "Consistencia (no responder al azar)",
            "why": "Las plataformas detectan respuestas aleatorias y banean.",
        },
    ],
    "data_entry": [
        {
            "topic": "Seguir instrucciones exactas (linking, bounding boxes, ruotazione)",
            "why": "Microtareas: precisión es lo único que se evalúa.",
        },
        {"topic": "Atención al detalle", "why": "Cada tarea mal hecha baja tu calidad y tus futuras tareas."},
        {"topic": "Inglés básico para leer la UI", "why": "La mayoría de plataformas están en inglés."},
    ],
}

_PREP_CHECKLIST: list[str] = [
    "Crear la cuenta (email + perfil + país Argentina).",
    "Dar el assessment UNA sola vez (si aplica). No apures: OWNEX te preparó los temas.",
    "Configurar el rail de cobro ANTES de trabajar (P(CASH) real).",
    "Primera tarea pequeña: completar > ganar. La primera entrega exitosa desbloquea el resto.",
    "Registrar horas humanas y resultado (OWNEX aprende tu $/h real).",
]


def _category_key(src: Any) -> str:
    cat = str(getattr(getattr(src, "category", ""), "value", getattr(src, "category", ""))).lower()
    if "bug" in cat:
        return "bug_bounty"
    if "dev" in cat:
        return "dev_bounty"
    if "ai" in cat:
        return "ai_evaluation"
    return "data_entry"


def build_prep_guide(src: Any) -> dict[str, Any]:
    """Guía determinista: qué revisar + checklist + límites reales. Sin IA, siempre."""
    name = str(getattr(src, "name", "?"))
    cat = _category_key(src)
    topics = _CATEGORY_PREP.get(cat, [])

    entry_note = ""
    if bool(getattr(src, "professional_experience_required", False)):
        entry_note = "⚠️ Esta web pide experiencia profesional en sus roles principales → NO es entry-level. OWNEX la bloquea del mix salvo proyectos puntuales all-access."
    elif bool(getattr(src, "requires_assessment", False)):
        entry_note = f"Única barrera: 1 assessment ({getattr(src, 'assessment_count', 1)}). Preparate con los temas de abajo; lo rendís vos."
    elif bool(getattr(src, "beginner_accessible", True)):
        entry_note = "Entrada directa por resultado, sin assessment. Registro → perfil → tarea → entrega."

    return {
        "name": name,
        "category": cat,
        "entry_note": entry_note,
        "topics": topics,
        "checklist": _PREP_CHECKLIST,
        "estimated_effort": {
            "bug_bounty": "alta (aprender HTTP+OWASP+reporting)",
            "dev_bounty": "media (Git+correr repo+test)",
            "ai_evaluation": "baja-media (seguir rúbrica)",
            "data_entry": "baja (precisión)",
        }.get(cat, "media"),
    }


def _build_ai_prompt(src: Any, guide: dict[str, Any]) -> str:
    name = str(getattr(src, "name", "?"))
    url = str(getattr(src, "url", "") or "")
    cat = guide["category"]
    topics = ", ".join(t["topic"] for t in guide["topics"])
    return (
        f"Perfil: usuario NUEVO sin experiencia profesional, inglés excelente, {cat}, "
        f"outcome-based, sin entrevista/cert/portfolio, máx 1 assessment.\n\n"
        f"Plataforma: {name} ({url})\n"
        f"Categoría: {cat}. ¿Qué tenés que saber/estudiar para pasar su assessment y "
        f"ganar TU PRIMER pago ahí? Pasos concretos día a día (qué hacer hoy, mañana, "
        f"día 3), ejemplos de lo que pide la plataforma, errores comunes y cómo "
        f"evitarlos. En español, directo y accionable, sin humo, sin prometer plata. "
        f"Temas base sugeridos: {topics}."
    )


async def generate_ai_prep(src: Any, timeout_s: float = 60.0) -> dict[str, Any]:
    """Prep con IA (free 24/7). Best-effort: si la IA no responde, devuelve el guía determinista."""
    guide = build_prep_guide(src)
    prompt = _build_ai_prompt(src, guide)
    try:
        from cores.copilot.providers.router import TASK_CHAT, get_provider_router

        import asyncio

        resp = await asyncio.wait_for(
            get_provider_router().route(task_type=TASK_CHAT, messages=[{"role": "user", "content": prompt}]),
            timeout=timeout_s,
        )
        text = str(getattr(resp, "content", "") or "").strip()
        if text and "No provider available" not in text:
            return {**guide, "ai": True, "ai_text": text}
    except Exception as exc:
        logger.warning("source_prep: IA no disponible (%s) → guía determinista", exc)
    return {**guide, "ai": False, "ai_text": ""}
