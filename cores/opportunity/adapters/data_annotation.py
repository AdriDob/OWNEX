"""Data Annotation Adapter — REMOVED.

Data annotation platforms (Scale AI, Outlier, Appen, Telus, Clickworker) have been
removed from OWNEX in favor of higher-value open source bounties (Algora, BountyBoard,
Polar, GitHub Sponsors, thanks.dev).

Rationale:
- Data annotation is low-skill, low-pay ($8-22/hour), high-friction (qualification tests)
- Open source bounties are zero-barrier, higher-pay ($50-5,000), outcome-based
- Open source contributions build reputation and passive income (GitHub Sponsors, thanks.dev)
- Data annotation does not align with OWNEX's goal: high-value technical work

This file is kept for backward compatibility but returns empty results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("ownex.adapters.data_annotation")


@dataclass
class DataAnnotationOpportunity:
    """A data annotation opportunity (deprecated)."""

    id: str
    platform: str
    title: str
    description: str
    task_type: str
    pay_rate: float
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


class DataAnnotationOrchestrator:
    """Orchestrates all Data Annotation adapters (deprecated — returns empty)."""

    def __init__(self) -> None:
        self.adapters = []

    async def fetch_all(self) -> list[DataAnnotationOpportunity]:
        """Fetch from all data annotation platforms (deprecated — returns empty)."""
        logger.warning("[DATA] Data annotation adapters removed in favor of open source bounties")
        return []

    def get_summary(self) -> dict[str, Any]:
        """Get summary of data annotation landscape (deprecated)."""
        return {
            "platforms": [],
            "total_platforms": 0,
            "avg_pay_rate": 0.0,
            "pay_range": "$0",
            "barrier": "$0",
            "qualification": "Not required (deprecated)",
            "portfolio": "Not required",
            "interview": "Not required",
            "skill_requirements": [],
            "time_to_first_pay": "N/A (deprecated)",
            "monthly_potential": "$0 (deprecated)",
            "note": "Data annotation removed in favor of open source bounties (Algora, BountyBoard, Polar)",
        }


# Singleton
_data_annotation_orchestrator: DataAnnotationOrchestrator | None = None


def get_data_annotation_orchestrator() -> DataAnnotationOrchestrator:
    """Get or create the global data annotation orchestrator (deprecated)."""
    global _data_annotation_orchestrator
    if _data_annotation_orchestrator is None:
        _data_annotation_orchestrator = DataAnnotationOrchestrator()
    return _data_annotation_orchestrator
