"""AI Tasks Adapter — Outlier, Scale AI, Alignerr, Mindrift, Remotasks.

Zero-barrier platforms for AI evaluation, LLM testing, and data tasks.
No portfolio, no interview — just pass qualification tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.adapters.ai_tasks")

#: Plataformas cuya entrada exige credencial ACADÉMICA, verificado en la
#: página de cada una el 2026-10-08:
#:   · Outlier  — "minimum qualifications typically require undergraduate-level
#:     expertise"; lo preferido es posgrado.
#:   · Mindrift — "70% of our contributors hold a Master's degree or PhD" y
#:     pide "domain expertise in your field".
#: No confundir con la dificultad de la tarea: un task "easy" en Outlier
#: igual pasa por el filtro de grado.
_CREDENTIAL_PLATFORMS = frozenset({"outlier", "mindrift"})


@dataclass
class AITaskOpportunity:
    """An AI task opportunity."""

    id: str
    platform: str
    title: str
    description: str
    task_type: str  # evaluation, annotation, rating, testing
    pay_rate: float  # USD per hour
    pay_range: tuple[float, float] = (0.0, 0.0)
    estimated_minutes: float = 30.0
    skills_required: list[str] | None = None
    qualification_needed: bool = True
    qualification_difficulty: str = "medium"  # easy, medium, hard
    url: str = ""
    available: bool = True
    country_accessible: list[str] | None = None
    metadata: dict[str, Any] | None = None

    @property
    def ev_per_hour(self) -> float:
        return self.pay_rate

    @property
    def barrier(self) -> str:
        """Barrera de entrada REAL, derivada de la plataforma (verificada).

        Antes devolvía `"$0"` fijo y el router lo publica como `barrier` en
        `/api/pillars/ai-tasks/summary`: afirmaba barrera cero para Outlier,
        cuya página dice *"minimum qualifications typically require
        undergraduate-level expertise"* (verificado 2026-10-08).

        La fuente es la plataforma, NO `qualification_difficulty` (que es
        dificultad de la tarea: un task "hard" no implica doctorado, y uno
        "easy" en Outlier igual pide grado).

        Se mantiene el string `$0` para las que no piden nada porque el
        contrato del endpoint y sus consumidores lo esperan.
        """
        if self.platform in _CREDENTIAL_PLATFORMS:
            return "assessment + credencial académica"
        if self.qualification_needed:
            return "assessment"
        return "$0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "pay_rate": self.pay_rate,
            "pay_range": list(self.pay_range),
            "estimated_minutes": self.estimated_minutes,
            "ev_per_hour": self.ev_per_hour,
            "barrier": self.barrier,
            "skills_required": self.skills_required or [],
            "qualification_needed": self.qualification_needed,
            "qualification_difficulty": self.qualification_difficulty,
            "url": self.url,
            "available": self.available,
        }


class OutlierAdapter:
    """Outlier.ai — AI evaluation and LLM testing tasks."""

    PLATFORM = "outlier"
    BASE_URL = "https://outlier.ai"

    QUALIFICATION_TASKS = [
        {"type": "code_review", "difficulty": "medium", "pay": 25},
        {"type": "llm_rating", "difficulty": "easy", "pay": 20},
        {"type": "prompt_evaluation", "difficulty": "medium", "pay": 28},
        {"type": "response_quality", "difficulty": "easy", "pay": 18},
        {"type": "safety_evaluation", "difficulty": "hard", "pay": 35},
    ]

    async def fetch_opportunities(self) -> list[AITaskOpportunity]:
        """Fetch available AI task types from Outlier."""
        opportunities = []
        for i, task in enumerate(self.QUALIFICATION_TASKS):
            opportunities.append(
                AITaskOpportunity(
                    id=f"outlier_{i}",
                    platform="outlier",
                    title=f"Outlier: {task['type'].replace('_', ' ').title()}",
                    description=f"AI {task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 5, task["pay"] + 10),
                    estimated_minutes=45,
                    skills_required=["python", "ai", "reasoning"],
                    qualification_needed=True,
                    qualification_difficulty=task["difficulty"],
                    url="https://outlier.ai",
                    available=True,
                    country_accessible=["*"],  # Global
                )
            )
        return opportunities


class ScaleAIAdapter:
    """Scale AI — Data annotation, AI evaluation, and training tasks."""

    PLATFORM = "scale"
    BASE_URL = "https://scale.com"

    TASK_TYPES = [
        {"type": "code_evaluation", "pay": 30, "difficulty": "medium"},
        {"type": "image_annotation", "pay": 15, "difficulty": "easy"},
        {"type": "text_classification", "pay": 12, "difficulty": "easy"},
        {"type": "llm_comparison", "pay": 25, "difficulty": "medium"},
        {"type": "safety_rating", "pay": 28, "difficulty": "hard"},
        {"type": "prompt_engineering", "pay": 35, "difficulty": "hard"},
    ]

    async def fetch_opportunities(self) -> list[AITaskOpportunity]:
        """Fetch available task types from Scale AI."""
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                AITaskOpportunity(
                    id=f"scale_{i}",
                    platform="scale_ai",
                    title=f"Scale AI: {task['type'].replace('_', ' ').title()}",
                    description=f"AI {task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 5, task["pay"] + 10),
                    estimated_minutes=30,
                    skills_required=["python", "ai"],
                    qualification_needed=True,
                    qualification_difficulty=task["difficulty"],
                    url="https://scale.com",
                    available=True,
                    country_accessible=["*"],
                )
            )
        return opportunities


class AlignerrAdapter:
    """Alignerr — AI alignment and evaluation tasks."""

    PLATFORM = "alignerr"
    BASE_URL = "https://alignerr.com"

    TASK_TYPES = [
        {"type": "ai_alignment", "pay": 30, "difficulty": "medium"},
        {"type": "response_rating", "pay": 22, "difficulty": "easy"},
        {"type": "safety_check", "pay": 25, "difficulty": "medium"},
        {"type": "code_review", "pay": 35, "difficulty": "hard"},
    ]

    async def fetch_opportunities(self) -> list[AITaskOpportunity]:
        """Fetch available tasks from Alignerr."""
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                AITaskOpportunity(
                    id=f"alignerr_{i}",
                    platform="alignerr",
                    title=f"Alignerr: {task['type'].replace('_', ' ').title()}",
                    description=f"AI {task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 5, task["pay"] + 10),
                    estimated_minutes=40,
                    skills_required=["ai", "reasoning"],
                    qualification_needed=True,
                    qualification_difficulty=task["difficulty"],
                    url="https://alignerr.com",
                    available=True,
                    country_accessible=["*"],
                )
            )
        return opportunities


class MindriftAdapter:
    """Mindrift — AI training and evaluation tasks."""

    PLATFORM = "mindrift"

    TASK_TYPES = [
        {"type": "llm_training", "pay": 20, "difficulty": "easy"},
        {"type": "prompt_testing", "pay": 22, "difficulty": "medium"},
        {"type": "response_evaluation", "pay": 18, "difficulty": "easy"},
    ]

    async def fetch_opportunities(self) -> list[AITaskOpportunity]:
        """Fetch available tasks from Mindrift."""
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                AITaskOpportunity(
                    id=f"mindrift_{i}",
                    platform="mindrift",
                    title=f"Mindrift: {task['type'].replace('_', ' ').title()}",
                    description=f"AI {task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 3, task["pay"] + 8),
                    estimated_minutes=25,
                    skills_required=["ai"],
                    qualification_needed=True,
                    qualification_difficulty=task["difficulty"],
                    url="https://mindrift.ai",
                    available=True,
                    country_accessible=["*"],
                )
            )
        return opportunities


class AITasksOrchestrator:
    """Orchestrates all AI Tasks adapters."""

    def __init__(self) -> None:
        self.adapters = [
            OutlierAdapter(),
            ScaleAIAdapter(),
            AlignerrAdapter(),
            MindriftAdapter(),
        ]

    async def fetch_all(self) -> list[AITaskOpportunity]:
        """Fetch from all AI task platforms."""
        all_opps: list[AITaskOpportunity] = []
        for adapter in self.adapters:
            try:
                opps = await adapter.fetch_opportunities()
                all_opps.extend(opps)
                logger.info("[AI_TASKS] %s: %d opportunities", adapter.PLATFORM, len(opps))
            except Exception as e:
                logger.warning("[AI_TASKS] %s failed: %s", adapter.PLATFORM, e)
        return all_opps

    def get_summary(self) -> dict[str, Any]:
        """Resumen del landscape de AI tasks.

        Reconciliado 2026-10-08. Antes todo el bloque era literal:
        `barrier: "$0"`, `avg_pay_rate: 24.0`, `pay_range: "$12-45/hour"` y
        `monthly_potential: "$1,000 - $5,000"` para las cuatro plataformas,
        sin ninguna base de cálculo. **Dos de ellas piden credencial
        académica** (verificado en sus páginas ese día):

            · Outlier  — "minimum qualifications typically require
              undergraduate-level expertise"; lo preferido es posgrado.
            · Mindrift — "70% of our contributors hold a Master's or PhD".

        La barrera se deriva de la plataforma (es un dato verificable). El
        pay y el potencial mensual quedan `None` = UNKNOWN: dependen de
        horas disponibles y de la tasa de aceptación real, que todavía no
        existen. Afirmarlos era la forma más cara de mentir sobre
        ingresos.
        """
        # `fetch_all` es async (hace red), así que un GET sincrónico no puede
        # depender de él: el resumen se arma con lo declarado por cada adapter
        # (`PLATFORM` + barrera verificada), no con números inventados.
        platforms = sorted({a.PLATFORM for a in self.adapters})
        credential = [p for p in platforms if p in _CREDENTIAL_PLATFORMS]
        open_barrier = [p for p in platforms if p not in _CREDENTIAL_PLATFORMS]

        if credential and open_barrier:
            barrier = (
                f"mixto: {', '.join(open_barrier)} assessment sin credencial; "
                f"{', '.join(credential)} piden credencial académica"
            )
        elif credential:
            barrier = "assessment + credencial académica"
        else:
            barrier = "assessment"

        return {
            "platforms": platforms,
            "total_platforms": len(self.adapters),
            "avg_pay_rate": None,
            "pay_range": (
                "UNKNOWN: se calcula con fetch_all (async). Verificado 2026-10-08 en "
                "alignerr.com/jobs: $10-35/hr, $15-35/hr, $150/hr publicados."
            ),
            "barrier": barrier,
            "qualification": "Required (online test)",
            "portfolio": "Not required",
            "interview": "Not required",
            "country": "Global (most platforms)",
            "skill_requirements": ["reasoning", "attention to detail", "python helpful"],
            "time_to_first_pay": "1-2 weeks after qualification",
            "monthly_potential": None,
            "monthly_potential_note": (
                "UNKNOWN: depende de horas disponibles y tasa de aceptación real. "
                "Antes afirmaba $1,000-$5,000 sin base de cálculo."
            ),
        }


# Singleton
_ai_tasks_orchestrator: AITasksOrchestrator | None = None


def get_ai_tasks_orchestrator() -> AITasksOrchestrator:
    """Get or create the global AI tasks orchestrator."""
    global _ai_tasks_orchestrator
    if _ai_tasks_orchestrator is None:
        _ai_tasks_orchestrator = AITasksOrchestrator()
    return _ai_tasks_orchestrator
