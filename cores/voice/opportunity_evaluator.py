"""Opportunity Evaluator — intelligent reasoning behind every voice request.

The assistant never just answers: it reasons about whether the request is worth
working on, generating income, or investing time. Classifies the request domain
and returns an honest verdict with reasoning — the "system of trust" layer that
decides what deserves the user's attention. Pure and decoupled, never invents
data (only reasons over the request text + static domain knowledge).

Extended to integrate with VoiceCommandExecutor for actionable voice commands.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger("ownex.voice.opportunity_evaluator")

# Domain detection keywords (lowercased, substring match).
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "opportunity": [
        "oportunidad",
        "bounty",
        "trabajo",
        "freelance",
        "remoto",
        "cobrar",
        "ganar",
        "busca",
        "encontr",
        "proyecto",
        "propuesta",
        "tarea",
        "contrato",
        "empleo",
    ],
    "investment": [
        "invert",
        "inversión",
        "inversiones",
        "inversor",
        "cripto",
        "bitcoin",
        "eth",
        "accion",
        "acciones",
        "portafolio",
        "portfolio",
        "trading",
        "rendimiento",
    ],
    "wealth": [
        "patrimonio",
        "ahorr",
        "gasto",
        "ingreso pasivo",
        "multiplic",
        "capital",
        "finanzas",
        "presupuesto",
        "cuenta",
        "cobro",
        "pago",
    ],
    "learning": [
        "aprend",
        "estudi",
        "curso",
        "capacit",
        "nueva tecnolog",
        "mejora",
        "skill",
        "entren",
        "practic",
    ],
    "productivity": [
        "productividad",
        "organiz",
        "plan",
        "sistema",
        "flujo",
        "automatiz",
        "tarea",
        "agenda",
        "recordat",
        "hora",
        "enfoque",
    ],
    "life": [
        "vida",
        "salud",
        "hábito",
        "hábitos",
        "descanso",
        "ejercicio",
        "sueño",
        "equilibrio",
        "rutina",
    ],
}

# Domains that directly produce income when acted upon.
_INCOME_DOMAINS: frozenset[str] = frozenset({"opportunity", "investment", "wealth"})

# Domains that build the ability to earn (indirect income).
_LEARNING_DOMAINS: frozenset[str] = frozenset({"learning"})

# Phrasings that turn any domain into a low-value request.
_LOW_VALUE_MARKERS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(jugar|mirar|stream|video|película|pelicula|meme|chiste)\b"), "entertainment"),
    (re.compile(r"\b(abrir|cerrar|instalar|descargar)\b\s+(chrome|juego|app|programa)\b"), "system_errand"),
]


@dataclass(slots=True)
class EvaluationResult:
    """Verdict of whether a request deserves the user's time."""

    request_text: str
    domain: str = "general"
    worth_it: bool = False
    worth_score: float = 0.0  # 0-1
    reasoning: list[str] = field(default_factory=list)
    suggested_action: str = ""
    confidence: float = 0.0
    is_executable: bool = False  # Whether this can be executed by VoiceCommandExecutor
    executor_action: str | None = None  # Action to execute if is_executable


class OpportunityEvaluator:
    """Decides what is worth the user's attention."""

    def __init__(self) -> None:
        """Initialize evaluator with command executor awareness."""
        self._executor_patterns = {
            "claim": ["claim", "reclamar"],
            "submit": ["submit", "enviar"],
            "check": ["check", "ver", "status"],
            "start": ["start", "iniciar", "execute"],
        }

    def evaluate(self, request_text: str) -> EvaluationResult:
        original = (request_text or "").strip()
        text = original.lower()
        if not original:
            return EvaluationResult(
                request_text=original,
                domain="general",
                worth_it=False,
                worth_score=0.0,
                reasoning=["No recibí ninguna instrucción."],
                suggested_action="Esperando una instrucción concreta.",
                confidence=0.5,
            )

        domain, domain_hits = self._detect_domain(text)
        low_value, low_value_reason = self._detect_low_value(text)

        score = self._score(text, domain, domain_hits, low_value)
        worth_it = score >= 0.5

        reasoning = self._build_reasoning(domain, low_value, low_value_reason, score)
        suggested_action = self._suggest(domain, worth_it)

        # Check if this is an executable command
        is_executable, executor_action = self._detect_executable(text)

        return EvaluationResult(
            request_text=original,
            domain=domain,
            worth_it=worth_it,
            worth_score=round(score, 2),
            reasoning=reasoning,
            suggested_action=suggested_action,
            confidence=round(min(1.0, 0.5 + domain_hits * 0.12), 2),
            is_executable=is_executable,
            executor_action=executor_action,
        )

    @staticmethod
    def _detect_domain(text: str) -> tuple[str, int]:
        best_domain = "general"
        best_hits = 0
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits > best_hits:
                best_domain = domain
                best_hits = hits
        return best_domain, best_hits

    @staticmethod
    def _detect_low_value(text: str) -> tuple[bool, str]:
        for pattern, label in _LOW_VALUE_MARKERS:
            if pattern.search(text):
                return True, label
        return False, ""

    def _detect_executable(self, text: str) -> tuple[bool, str | None]:
        """Detect if the request is an executable command for VoiceCommandExecutor."""
        for action, keywords in self._executor_patterns.items():
            if any(kw in text for kw in keywords) and ("bounty" in text or "issue" in text or "pr" in text):
                return True, action
        return False, None

    @staticmethod
    def _score(text: str, domain: str, hits: int, low_value: bool) -> float:
        base = 0.15
        if domain in _INCOME_DOMAINS:
            base += 0.35
        elif domain in _LEARNING_DOMAINS:
            base += 0.25
        elif domain in ("productivity", "life"):
            base += 0.2
        base += min(0.3, hits * 0.08)
        if low_value:
            base -= 0.5
        return max(0.0, min(1.0, base))

    @staticmethod
    def _build_reasoning(domain: str, low_value: bool, low_value_reason: str, score: float) -> list[str]:
        if low_value:
            return [
                f"Parece una tarea de {low_value_reason}, no de generación de valor.",
                "Podemos hacerla, pero no prioriza ingresos ni aprendizaje.",
            ]
        domain_label = {
            "opportunity": "búsqueda de oportunidades remuneradas",
            "investment": "decisión de inversión",
            "wealth": "gestión de patrimonio e ingresos",
            "learning": "aprendizaje de habilidades",
            "productivity": "productividad y organización",
            "life": "calidad de vida",
            "general": "solicitud general",
        }.get(domain, "solicitud general")
        if score >= 0.5:
            return [
                f"Es una solicitud de {domain_label}.",
                "Tiene potencial de generar ingresos o aprender — vale la pena invertir tiempo.",
            ]
        return [f"Es una solicitud de {domain_label}.", "No parece directamente ligada a ingresos o aprendizaje ahora."]

    @staticmethod
    def _suggest(domain: str, worth_it: bool) -> str:
        if not worth_it:
            return "Si preferís, puedo convertirla en una tarea de productividad o dejarla pendiente."
        suggestions = {
            "opportunity": "Ejecutar un escaneo de oportunidades (POST /direct-work/discover) y recomendarte el top 3.",
            "investment": "Consultar el estado de ingresos/patrimonio y revisar la relación riesgo-retorno antes de actuar.",
            "wealth": "Revisar los pagos pendientes y el historial de ingresos en el Revenue Tracker.",
            "learning": "Planear un skill gap para la tecnología y preparar un plan de aprendizaje de 7 días.",
            "productivity": "Crear un plan diario y priorizar las tareas de mayor impacto.",
            "life": "Organizar una rutina equilibrada que proteja tu energía para el trabajo.",
            "general": "Descomponer la solicitud en un plan de acción concreto.",
        }
        return suggestions.get(domain, "Descomponer en un plan de acción.")
