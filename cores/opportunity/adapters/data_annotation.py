"""Data Annotation Adapter — Scale AI, Outlier, Appen, Telus, Clickworker.

Zero-barrier platforms for data labeling, annotation, and AI training.
No portfolio, no interview — just pass qualification tests.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.adapters.data_annotation")


@dataclass
class DataAnnotationOpportunity:
    """A data annotation opportunity."""

    id: str
    platform: str
    title: str
    description: str
    task_type: str  # labeling, classification, transcription, evaluation
    pay_rate: float  # USD per hour
    pay_range: tuple[float, float] = (0.0, 0.0)
    estimated_minutes: float = 30.0
    skills_required: list[str] | None = None
    qualification_needed: bool = True
    url: str = ""
    available: bool = True
    metadata: dict[str, Any] | None = None

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
            "barrier": self.barrier,
            "skills_required": self.skills_required or [],
            "qualification_needed": self.qualification_needed,
            "url": self.url,
        }


class ScaleDataAdapter:
    """Scale AI — Data annotation and labeling tasks."""

    PLATFORM = "scale_ai"

    TASK_TYPES = [
        {"type": "image_labeling", "pay": 15, "difficulty": "easy"},
        {"type": "text_classification", "pay": 12, "difficulty": "easy"},
        {"type": "bounding_box", "pay": 18, "difficulty": "medium"},
        {"type": "semantic_segmentation", "pay": 20, "difficulty": "medium"},
        {"type": "transcription", "pay": 14, "difficulty": "easy"},
        {"type": "data_validation", "pay": 16, "difficulty": "easy"},
    ]

    async def fetch_opportunities(self) -> list[DataAnnotationOpportunity]:
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                DataAnnotationOpportunity(
                    id=f"scale_data_{i}",
                    platform="scale_ai",
                    title=f"Scale AI: {task['type'].replace('_', ' ').title()}",
                    description=f"Data {task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 3, task["pay"] + 8),
                    estimated_minutes=30,
                    skills_required=["attention_to_detail"],
                    qualification_needed=True,
                    url="https://scale.com",
                )
            )
        return opportunities


class OutlierDataAdapter:
    """Outlier — Data annotation and evaluation tasks."""

    PLATFORM = "outlier"

    TASK_TYPES = [
        {"type": "data_annotation", "pay": 18, "difficulty": "easy"},
        {"type": "quality_review", "pay": 22, "difficulty": "medium"},
        {"type": "content_moderation", "pay": 15, "difficulty": "easy"},
    ]

    async def fetch_opportunities(self) -> list[DataAnnotationOpportunity]:
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                DataAnnotationOpportunity(
                    id=f"outlier_data_{i}",
                    platform="outlier",
                    title=f"Outlier: {task['type'].replace('_', ' ').title()}",
                    description=f"Data {task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 3, task["pay"] + 8),
                    estimated_minutes=25,
                    skills_required=["attention_to_detail"],
                    qualification_needed=True,
                    url="https://outlier.ai",
                )
            )
        return opportunities


class AppenAdapter:
    """Appen — Data annotation and AI training."""

    PLATFORM = "appen"

    TASK_TYPES = [
        {"type": "search_evaluation", "pay": 12, "difficulty": "easy"},
        {"type": "social_media_evaluation", "pay": 10, "difficulty": "easy"},
        {"type": "data_labeling", "pay": 14, "difficulty": "easy"},
        {"type": "transcription", "pay": 11, "difficulty": "easy"},
    ]

    async def fetch_opportunities(self) -> list[DataAnnotationOpportunity]:
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                DataAnnotationOpportunity(
                    id=f"appen_{i}",
                    platform="appen",
                    title=f"Appen: {task['type'].replace('_', ' ').title()}",
                    description=f"{task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 2, task["pay"] + 5),
                    estimated_minutes=40,
                    skills_required=["attention_to_detail"],
                    qualification_needed=True,
                    url="https://www.appen.com",
                )
            )
        return opportunities


class TelusAdapter:
    """Telus International (formerly Lionbridge) — Data annotation."""

    PLATFORM = "telus"

    TASK_TYPES = [
        {"type": "ai_training", "pay": 14, "difficulty": "easy"},
        {"type": "search_quality", "pay": 12, "difficulty": "easy"},
        {"type": "data_labeling", "pay": 13, "difficulty": "easy"},
    ]

    async def fetch_opportunities(self) -> list[DataAnnotationOpportunity]:
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                DataAnnotationOpportunity(
                    id=f"telus_{i}",
                    platform="telus",
                    title=f"Telus: {task['type'].replace('_', ' ').title()}",
                    description=f"{task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 2, task["pay"] + 5),
                    estimated_minutes=35,
                    skills_required=["attention_to_detail"],
                    qualification_needed=True,
                    url="https://www.telusinternational.com",
                )
            )
        return opportunities


class ClickworkerAdapter:
    """Clickworker — Microtasks and data annotation."""

    PLATFORM = "clickworker"

    TASK_TYPES = [
        {"type": "text_creation", "pay": 10, "difficulty": "easy"},
        {"type": "data_categorization", "pay": 8, "difficulty": "easy"},
        {"type": "web_research", "pay": 12, "difficulty": "easy"},
    ]

    async def fetch_opportunities(self) -> list[DataAnnotationOpportunity]:
        opportunities = []
        for i, task in enumerate(self.TASK_TYPES):
            opportunities.append(
                DataAnnotationOpportunity(
                    id=f"clickworker_{i}",
                    platform="clickworker",
                    title=f"Clickworker: {task['type'].replace('_', ' ').title()}",
                    description=f"{task['type'].replace('_', ' ')} tasks. Pay: ${task['pay']}/hour.",
                    task_type=task["type"],
                    pay_rate=task["pay"],
                    pay_range=(task["pay"] - 2, task["pay"] + 5),
                    estimated_minutes=20,
                    skills_required=["attention_to_detail"],
                    qualification_needed=True,
                    url="https://www.clickworker.com",
                )
            )
        return opportunities


class DataAnnotationOrchestrator:
    """Orchestrates all Data Annotation adapters."""

    def __init__(self) -> None:
        self.adapters = [
            ScaleDataAdapter(),
            OutlierDataAdapter(),
            AppenAdapter(),
            TelusAdapter(),
            ClickworkerAdapter(),
        ]

    async def fetch_all(self) -> list[DataAnnotationOpportunity]:
        """Fetch from all data annotation platforms."""
        all_opps: list[DataAnnotationOpportunity] = []
        for adapter in self.adapters:
            try:
                opps = await adapter.fetch_opportunities()
                all_opps.extend(opps)
                logger.info("[DATA] %s: %d opportunities", adapter.PLATFORM, len(opps))
            except Exception as e:
                logger.warning("[DATA] %s failed: %s", adapter.PLATFORM, e)
        return all_opps

    def get_summary(self) -> dict[str, Any]:
        """Get summary of data annotation landscape."""
        return {
            "platforms": ["scale_ai", "outlier", "appen", "telus", "clickworker"],
            "total_platforms": len(self.adapters),
            "avg_pay_rate": 13.0,
            "pay_range": "$8-22/hour",
            "barrier": "$0",
            "qualification": "Required (online test)",
            "portfolio": "Not required",
            "interview": "Not required",
            "skill_requirements": ["attention to detail", "consistency", "patience"],
            "time_to_first_pay": "1-2 weeks after qualification",
            "monthly_potential": "$500 - $3,000",
        }


# Singleton
_data_annotation_orchestrator: DataAnnotationOrchestrator | None = None


def get_data_annotation_orchestrator() -> DataAnnotationOrchestrator:
    """Get or create the global data annotation orchestrator."""
    global _data_annotation_orchestrator
    if _data_annotation_orchestrator is None:
        _data_annotation_orchestrator = DataAnnotationOrchestrator()
    return _data_annotation_orchestrator
