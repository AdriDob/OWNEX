"""Perfil de modelo de IA para trabajo de seguridad autorizada.

Por qué existe
--------------
Los reasoners de `cores/offensive/` son heurísticos: no piden ayuda a un LLM.
Cuando OWNEX **sí** usa IA para seguridad (revisar un snippet, redactar un
PoC, priorizar hallazgos, redactar un reporte), el modelo importa — y el
catálogo de modelos mezcla chat models con *clasificadores*, routers y
embeddings. Servir un clasificador donde se esperaba un asistente produce
fallo silencioso.

Este módulo fija el perfil con EVIDENCIA medida, no con opinión. Hay dos
rankings públicos y **ninguno** de sus ganadores es alcanzable desde esta
máquina, así que el perfil elige por *medido acá*:

- `qwen3.8-27b` (Groq vía FreeLLMAPI) — **ejecución**. En Aikido (32 CVEs
  reales, 11.7B tokens) da **26/32 pooled**: segundo en recall detrás de
  `deepseek-v4-pro`. Es el ganador de TrustedSec por pass rate
  (`gemma-4-31b-it`, 98.5%) que **no sirve**: Google responde HTTP 500 para
  `gemma-4-*` (verificado en vivo). Caveat real: en 95 de 96 trazas spends su
  training en CVEs viejos del propio repo ⇒ segunda opinión, nunca veredicto.
- `nemotron-3-super-120b` (NVIDIA NIM) — **descubrimiento**. **92.0%** de pass
  en TrustedSec (736/800 runs, 4º de 6). Es lo que realmente entrega una key
  de NVIDIA: la familia Nemotron, no `glm-5.3` ni `deepseek-v4-pro` (esos
  rutean a z-ai/deepseek, providers sin key).

La lección operativa del mismo benchmark: **pooling > una pasada buena**. Un
solo turno pierde alcance; repetir con otra lente lo recupera. `pool_runs()`
implementa eso.

Lo que la IA NO debe hacer aquí (§25 del megaprompt security)
-------------------------------------------------------------
El benchmark es explícito y OWNEX lo respeta:
- **Explotación multi-paso: 0% en todos los modelos** (UNION injection,
  blind boolean, enumeración de columnas). Nadie mantiene 10+ tool calls
  encadenados. La IA propone; la ejecución la verifica `ProbeEngine`.
- **El scaffolding importa más que el modelo base**: un buen arnés con un
  modelo mediocre supera a un modelo fuerte sin herramientas.
- La IA puede inventar relaciones CVE, CWE malformados o inferir rutas de
  ataque no soportadas ⇒ **es complementaria, nunca autoridad** (§56).
- SCOPE y autorización los decide `scope_enforcement`, no el modelo (§22).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

# ── Nombres exactos en el gateway (verificados vía GET /v1/models) ──
MODEL_OFFENSIVE = "qwen3.8-27b"  # verificado respondiendo (Groq); gemma-4-* da HTTP 500 en Google
# Nemotron vía NVIDIA NIM — MEDIDO respondiendo (2026-09-30). Es lo que
# realmente te da una key de NVIDIA: la familia Nemotron, NO glm-5.3 ni
# deepseek-v4-pro (esos rutean a z-ai/deepseek, providers sin key).
MODEL_DISCOVERY = "nemotron-3-super-120b"
MODEL_LARGE = "nemotron-3-ultra-550b"
MODEL_CHEAP = "gpt-oss-20b"

#: Los modelos de razonamiento (GLM-5.3, Kimi K3, Nemotron *-reasoning) gastan
#: cientos de tokens en `reasoning_content` ANTES de responder. Con max_tokens
#: bajo devuelven HTTP 200 con `content: null` — un fallo silencioso. Medido:
#: GLM-5.3 usó 431 tokens de razonamiento antes de los 104 de respuesta.
REASONING_TOKEN_FLOOR = 2000

#: Evidencia por modelo. Se muestra con el razonamiento para que una decisión
#: de routing sea auditable y no una caja negra.
MODEL_EVIDENCE: dict[str, dict[str, Any]] = {
    MODEL_OFFENSIVE: {
        "role": "offensive_execution",
        "benchmark": "Aikido — 32 CVEs reales, 11.7B tokens",
        "pooled_recall": "26/32",
        "caveat": (
            "CVE deja vu: en 95 de 96 trazas spends su training en CVEs "
            "viejos del propio repo. Útil como segunda opinión, no como veredicto."
        ),
        "verified_here": "identificó SQLi + impacto + fix vía FreeLLMAPI/Groq",
        "provider": "groq (vía FreeLLMAPI)",
        "evidence": "measured",
    },
    MODEL_DISCOVERY: {
        "role": "vulnerability_discovery",
        "benchmark": "TrustedSec — self-hosted offensive security",
        "pass_rate": 0.920,
        "sample": "736/800 runs (4º de 6 modelos)",
        "strong_at": "razonamiento multi-objetivo; SQLi / JWT / LFI / IDOR",
        "verified_here": "identificó SQLi + impacto + fix vía NVIDIA NIM",
        "provider": "nvidia (NIM, free, sin tarjeta)",
        "evidence": "measured",
    },
    MODEL_LARGE: {
        "role": "deep_review",
        "benchmark": "mismo corpus, variante 550B MoE",
        "strong_at": "análisis de código largo y razonamiento difícil",
        "verified_here": "identificó SQLi con detalle vía NVIDIA NIM",
        "provider": "nvidia (NIM, free, sin tarjeta)",
        "evidence": "measured",
    },
    MODEL_CHEAP: {
        "role": "cheap_fallback",
        "benchmark": "sin ranking público relevante",
        "strong_at": "costo/volumen; triage masivo",
        "verified_here": "responde vía FreeLLMAPI",
        "caveat": ("el más pequeño del set: más falsos positivos por token. Triage masivo, nunca veredicto."),
        "evidence": "measured",
    },
}


@dataclass(frozen=True)
class SecurityModelProfile:
    """Perfil de modelo para una tarea de seguridad concreta."""

    model: str
    role: str
    why: str
    #: Esta IA NO decide scope, ni autoriza, ni confirma una vulnerabilidad.
    advisory_only: bool = True
    #: Si la tarea es de ejecución, OWNEX debe verificar la salida con ProbeEngine.
    require_tool_verification: bool = True
    evidence: dict[str, Any] = field(default_factory=dict)
    #: Los reasoning models devuelven `content: null` si el presupuesto no alcanza
    #: para terminar de pensar. Floor medido, no un default arbitrario.
    min_max_tokens: int = REASONING_TOKEN_FLOOR


def profile_for(task: str) -> SecurityModelProfile:
    """Perfil recomendado según el tipo de tarea de seguridad.

    `task` acepta: ``exploit`` / ``redteam``, ``discovery`` / ``triage``,
    ``review`` / ``report``, o cualquier otro → cae a `cheap`.
    """
    t = (task or "").strip().lower()
    if t in {"exploit", "redteam", "red_team", "pentest", "poc", "exploitation"}:
        return SecurityModelProfile(
            model=MODEL_OFFENSIVE,
            role="offensive_execution",
            why=(
                "qwen3.8-27b (Groq): 26/32 de recall pooled en Aikido (32 CVEs "
                "reales). Es el mejor de los que responden desde esta máquina — "
                "el 98.5% de TrustedSec es de gemma-4-31b-it, que da HTTP 500. "
                "Caveat: entrenó sobre CVEs viejos del repo ⇒ segunda opinión."
            ),
            evidence=MODEL_EVIDENCE[MODEL_OFFENSIVE],
        )
    if t in {"discovery", "triage", "hunt", "analysis", "recon"}:
        return SecurityModelProfile(
            model=MODEL_DISCOVERY,
            role="vulnerability_discovery",
            why=(
                "Nemotron-3-Super vía NVIDIA NIM: 92.0% de pass en benchmark "
                "offensive (736/800 runs). Es lo que realmente sirve una key de "
                "NVIDIA; complement al de ejecución, no el mismo."
            ),
            evidence=MODEL_EVIDENCE[MODEL_DISCOVERY],
        )
    if t in {"review", "report", "writeup", "write_up", "summary"}:
        return SecurityModelProfile(
            model=MODEL_OFFENSIVE,
            role="report_and_review",
            why="El mejor razonamiento aplicado del set alcanzable; mismo perfil que ejecución.",
            evidence=MODEL_EVIDENCE[MODEL_OFFENSIVE],
        )
    return SecurityModelProfile(
        model=MODEL_CHEAP,
        role="cheap_fallback",
        why="Triage masivo donde el costo por llamada domina el resultado.",
        evidence=MODEL_EVIDENCE[MODEL_CHEAP],
    )


def pool_runs(answers: Sequence[str | None]) -> dict[str, Any]:
    """Consolida N ejecuciones en una conclusión honesta.

    El benchmark medió el porqué: una pasada de DeepSeek encontró 17 de 32
    vulns y tres pasadas 28/32. Repetir recupera alcance; una sola pasada
    pierde breadth. Este helper no elige el "mejor" resultado (eso sería
    cherry-picking): reporta el **consenso** y la disidencia, que es la
    señal honesta.
    """
    clean = [a.strip() for a in answers if a and a.strip()]
    if not clean:
        return {
            "verdict": "NO_DATA",
            "runs": 0,
            "unique_findings": 0,
            "agreement": None,
            "note": "Ninguna ejecución devolvió contenido.",
        }
    unique = {a for a in clean}
    counts = {a: clean.count(a) for a in unique}
    # Consenso = la respuesta que aparece en más ejecuciones.
    consensus, votes = max(counts.items(), key=lambda kv: kv[1])
    agreement = round(votes / len(clean), 3)
    # Mayoría estricta (>50% de las ejecuciones). Se evita el umbral 0.67 porque
    # 2/3 = 0.6667 redondea a 0.667 y caería en SPLIT por error de punto flotante.
    strict_majority = votes * 2 > len(clean)
    return {
        "verdict": "CONSENSUS" if strict_majority else ("SPLIT" if len(unique) > 1 else "SINGLE"),
        "runs": len(clean),
        "unique_findings": len(unique),
        "agreement": agreement,
        "consensus": consensus,
        "note": (
            "Disidencia entre ejecuciones: se reporta tal cual. "
            "Un veredicto con agreement bajo NO debe presentarse como confirmado."
        ),
    }
