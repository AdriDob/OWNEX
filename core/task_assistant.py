"""Asistente de Tareas — ayuda segura para tareas de Outlier/DA.

Analiza la tarea que pegás, te da un borrador técnico de referencia (estructura,
argumentos, datos, enfoque) y te marca QUÉ pulir para que quede en tu voz.

NO genera la respuesta final lista para pegar tal cual: eso sería contra TOS de
esas plataformas y te banean. Devuelve material para trabajar, no texto a copiar.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("core.task_assistant")

SYSTEM_PROMPT = """Sos un asistente técnico de referencia para trabajo freelance de IA.
Te pasan el ENUNCIADO de una tarea. Tu trabajo es darle a la persona:

1. **ANÁLISIS** — qué pide exactamente, criterios que probablemente evalúan, trampas comunes.
2. **ESTRUCTURA** — cómo armar una buena respuesta (orden de secciones/argumentos).
3. **BORRADOR TÉCNICO** — contenido de referencia en 1ra persona y voz natural, con datos y razonamiento.
4. **QUÉ PULIR** — las 3-5 cosas que la persona debe reescribir/ajustar para que sea SU trabajo: detalles personales, experiencia real, estilo propio, ejemplos concretos.

IMPORTANTE:
- El borrador es MATERIAL DE TRABAJO, no respuesta final para pegar.
- Escribí en lenguaje natural, con pausas y pequeñas imperfecciones humanas, NO texto académico perfecto.
- Nunca inventes experiencias, números o logros de la persona. Dejá marcadores [TU_EXPERIENCIA] donde corresponda.
- Respondé en ESPAÑOL con registro casual profesional.
"""


def _count_words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _task_type_guess(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["code", "código", "bug", "python", "javascript", "fix", "function", "sql", "api"]):
        return "code"
    if any(k in lower for k in ["essay", "ensayo", "write", "escribe", "summary", "resumen", "paraphrase"]):
        return "writing"
    if any(k in lower for k in ["compare", "compara", "rate", "evalúa", "label", "classify", "clasifica"]):
        return "judging"
    return "general"


async def analyze_task(task_text: str, provider: Any = None) -> dict[str, Any]:
    """Analiza la tarea y devuelve material de referencia."""
    if not task_text or not task_text.strip():
        return {"success": False, "error": "Tarea vacía."}

    words = _count_words(task_text)
    task_type = _task_type_guess(task_text)

    user_msg = (
        "ANÁLISIS DE TAREA\n"
        f"Tipo estimado: {task_type}\n"
        f"Longitud: {words} palabras\n\n"
        "ENUNCIADO:\n"
        f"{task_text}\n\n"
        "Dame el análisis completo según tu rol: ANÁLISIS, ESTRUCTURA, BORRADOR TÉCNICO y QUÉ PULIR."
    )

    # usar el router de providers existente
    try:
        if provider is None:
            from core.copilot.providers.router import get_provider_router

            provider = get_provider_router()
        result = await provider.route(
            task_type="chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        content = result.content or ""
    except Exception as e:
        logger.warning("[TASK_ASSISTANT] fallback sin LLM: %s", e)
        content = (
            "ANÁLISIS: No se pudo conectar al modelo. Revisá la config de IA.\n\n"
            "QUÉ PULIR: (manual)\n"
            "- Leé el enunciado dos veces y marcá los criterios de evaluación.\n"
            "- Armá respuesta corta y directa primero, después expandís.\n"
            "- Reescribí todo con tus palabras y un ejemplo real."
        )

    # Extraer secciones para la UI
    sections = _split_sections(content)

    return {
        "success": True,
        "task_type": task_type,
        "words": words,
        "response": content,
        "sections": sections,
        "provider": getattr(result, "provider", "unknown") if "result" in dir() else "unknown",
    }


def _split_sections(text: str) -> list[dict[str, str]]:
    """Divide la respuesta en secciones ANÁLISIS/ESTRUCTURA/BORRADOR/QUÉ PULIR."""
    markers = ["análisis", "estructura", "borrador", "qué pulir", "que pulir"]
    sections: list[dict[str, str]] = []
    lines = text.splitlines()

    current_title = "general"
    current_body: list[str] = []
    for line in lines:
        stripped = line.strip().lower()
        match = None
        for m in markers:
            if stripped.startswith(("**" + m, m + ":", m + " —", "#" + m)) or stripped.startswith(m):
                match = m
                break
        if match:
            if current_body:
                sections.append({"title": current_title.title(), "body": "\n".join(current_body).strip()})
            current_title = match
            current_body = []
            # limpiar el marker del título
            cleaned = line.strip().lstrip("#").strip()
            cleaned = re.sub(r"^\*\*|\*\*$", "", cleaned)
            cleaned = cleaned.split(":", 1)[-1].strip() if ":" in cleaned else cleaned
            if cleaned and len(cleaned) < 40:
                current_body.append(cleaned)
        else:
            current_body.append(line)
    if current_body:
        sections.append({"title": current_title.title(), "body": "\n".join(current_body).strip()})

    # dedupe títulos
    seen: set[str] = set()
    dedup: list[dict[str, str]] = []
    for s in sections:
        if s["title"].lower() not in seen:
            seen.add(s["title"].lower())
            dedup.append(s)
    return dedup


def get_task_assistant():
    return TaskAssistant()


class TaskAssistant:
    """Wrapper simple para el asistente de tareas."""

    async def analyze(self, task: str) -> dict[str, Any]:
        return await analyze_task(task)
