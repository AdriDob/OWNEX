"""Direct Work Learning Engine — Learns from work outcomes to improve future decisions.

Provides learning logic that can be used by WorkerCore for the LEARN phase.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cores.direct_work_engine.feedback import build_history_from_revenue_tracker

logger = logging.getLogger("ownex.direct_work_engine.learning")


@dataclass(slots=True)
class LearningResult:
    """Result of learning from a completed work item."""

    success: bool
    lessons: list[str] = field(default_factory=list)
    skill_updates: dict[str, float] = field(default_factory=dict)
    platform_updates: dict[str, float] = field(default_factory=dict)
    category_updates: dict[str, float] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "lessons": self.lessons,
            "skill_updates": self.skill_updates,
            "platform_updates": self.platform_updates,
            "category_updates": self.category_updates,
            "error": self.error,
        }


class DirectWorkLearningEngine:
    """Learns from completed work outcomes to improve future recommendations.

    Integrates with:
    - RevenueTracker for verified outcomes
    - ProfileBuilder for skill confidence updates
    - CareerEngine for skill gap analysis
    """

    def __init__(self) -> None:
        self._revenue_tracker = None

    def set_revenue_tracker(self, tracker: Any) -> None:
        self._revenue_tracker = tracker

    def learn(self, work_item: Any, outcome: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        """Learn from a completed work item outcome.

        Args:
            work_item: Completed work item
            outcome: Outcome status (accepted, paid, failed, cancelled, etc.)
            details: Additional outcome details (amount, time_to_payout, etc.)

        Returns:
            Learning result dict
        """
        try:
            if not self._revenue_tracker:
                logger.warning("No revenue tracker available for learning")
                return LearningResult(
                    success=False,
                    error="No revenue tracker available",
                ).to_dict()

            # Build learning records from revenue tracker
            records = build_history_from_revenue_tracker(self._revenue_tracker)

            if not records:
                logger.info("No verified outcomes available for learning")
                return LearningResult(
                    success=True,
                    lessons=["No new verified outcomes to learn from"],
                ).to_dict()

            # Apply learning to update profile (this would update the user profile)
            # In practice, this would update a user profile object
            lessons = []
            skill_updates = {}
            platform_updates = {}
            category_updates = {}

            for record in records:
                platform = record.get("platform", "")
                category = record.get("category", "")
                accepted = record.get("accepted", False)
                amount = record.get("amount", 0.0)

                if platform:
                    platform_updates[platform] = platform_updates.get(platform, 0.0) + (1.0 if accepted else -0.5)

                if category:
                    category_updates[category] = category_updates.get(category, 0.0) + (1.0 if accepted else -0.5)

                if accepted:
                    lessons.append(f"Platform {platform} category {category}: accepted ${amount:.2f}")
                else:
                    lessons.append(f"Platform {platform} category {category}: rejected/failed")

            # Extract skill insights from successful outcomes (placeholder)

            # Record calibration data for prediction improvement
            try:
                from cores.direct_work_engine.calibration import get_calibration_engine

                cal = get_calibration_engine()
                for record in records:
                    predicted = record.get("predicted_amount", 0.0)
                    actual = record.get("amount", 0.0)
                    platform = record.get("platform", "")
                    if predicted > 0 and actual > 0 and platform:
                        cal.record(
                            platform=platform,
                            predicted_hourly=predicted,
                            actual_hourly=actual,
                            opportunity_id=record.get("opportunity_id"),
                        )
            except Exception as cal_exc:
                logger.debug("Calibration recording failed (non-blocking): %s", cal_exc)

            logger.info("Learning completed: %d lessons extracted", len(lessons))

            return LearningResult(
                success=True,
                lessons=lessons,
                skill_updates=skill_updates,
                platform_updates=platform_updates,
                category_updates=category_updates,
            ).to_dict()

        except Exception as exc:
            logger.exception("Learning failed")
            return LearningResult(
                success=False,
                error=str(exc),
            ).to_dict()

    def update_skill_confidence(self, skill: str, confidence_delta: float) -> None:
        """Update confidence in a specific skill."""
        # This would update the user profile's skill_confidence
        logger.info("Skill confidence update: %s += %.2f", skill, confidence_delta)

    def get_learning_summary(self) -> dict[str, Any]:
        """Get summary of learned insights."""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "active",
            "message": "Learning engine active, integrates with RevenueTracker",
        }


# Convenience function
async def learn_from_outcome(work_item: Any, outcome: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convenience function for learning from a work outcome."""
    engine = DirectWorkLearningEngine()
    return engine.learn(work_item, outcome, details)
