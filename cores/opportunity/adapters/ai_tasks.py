"""AI Tasks Adapter — Outlier, Scale AI, Alignerr, Mindrift, Remotasks.

Zero-barrier platforms for AI evaluation, LLM testing, and data tasks.
No portfolio, no interview — just pass qualification tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.adapters.ai_tasks")


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
        """Get summary of AI tasks landscape."""
        return {
            "platforms": ["outlier", "scale_ai", "alignerr", "mindrift"],
            "total_platforms": len(self.adapters),
            "avg_pay_rate": 24.0,
            "pay_range": "$12-45/hour",
            "barrier": "$0",
            "qualification": "Required (online test)",
            "portfolio": "Not required",
            "interview": "Not required",
            "country": "Global (most platforms)",
            "skill_requirements": ["reasoning", "attention to detail", "python helpful"],
            "time_to_first_pay": "1-2 weeks after qualification",
            "monthly_potential": "$1,000 - $5,000",
        }


# Singleton
_ai_tasks_orchestrator: AITasksOrchestrator | None = None


def get_ai_tasks_orchestrator() -> AITasksOrchestrator:
    """Get or create the global AI tasks orchestrator."""
    global _ai_tasks_orchestrator
    if _ai_tasks_orchestrator is None:
        _ai_tasks_orchestrator = AITasksOrchestrator()
    return _ai_tasks_orchestrator
