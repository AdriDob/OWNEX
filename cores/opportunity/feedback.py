"""Feedback loop for opportunity scoring — learns from accepted/rejected outcomes.

Records user decisions and uses them to adjust future scoring through
personalized multipliers per category, platform, and technology.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from cores.memory.memory_store import MemoryStore

logger = logging.getLogger("ownex.opportunity.feedback")

_FEEDBACK_CATEGORY = "opportunity_feedback"
_MEMORY_STORE = MemoryStore()


class FeedbackOutcome(StrEnum):
    """Possible outcomes for an opportunity decision."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SKIPPED = "skipped"


@dataclass
class FeedbackRecord:
    """A single feedback record for an opportunity."""

    opportunity_id: str
    outcome: FeedbackOutcome
    category: str
    platform: str
    technology_tags: list[str]
    timestamp: str
    estimated_payout: float = 0.0
    actual_payout: float = 0.0
    reasoning: str = ""


class FeedbackLoop:
    """Manages feedback collection and score adjustment learning."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def record_feedback(
        self,
        opportunity_id: str,
        outcome: FeedbackOutcome,
        category: str,
        platform: str,
        technology_tags: list[str],
        estimated_payout: float = 0.0,
        actual_payout: float = 0.0,
        reasoning: str = "",
    ) -> None:
        """Record a feedback decision for an opportunity."""
        record = FeedbackRecord(
            opportunity_id=opportunity_id,
            outcome=outcome,
            category=category,
            platform=platform,
            technology_tags=technology_tags,
            timestamp=datetime.now(UTC).isoformat(),
            estimated_payout=estimated_payout,
            actual_payout=actual_payout,
            reasoning=reasoning,
        )

        details = {
            "outcome": outcome.value,
            "category": category,
            "platform": platform,
            "technology_tags": technology_tags,
            "timestamp": record.timestamp,
            "estimated_payout": estimated_payout,
            "actual_payout": actual_payout,
            "reasoning": reasoning,
        }

        try:
            _MEMORY_STORE.store(_FEEDBACK_CATEGORY, opportunity_id, details)
            logger.info(
                "Recorded feedback: %s for %s (category=%s, platform=%s)",
                outcome.value,
                opportunity_id,
                category,
                platform,
            )
        except Exception as exc:
            logger.warning("Failed to store feedback for %s: %s", opportunity_id, exc)

    def get_feedback_history(
        self,
        opportunity_id: str | None = None,
        category: str | None = None,
        platform: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve feedback history with optional filters."""
        try:
            if opportunity_id:
                record = _MEMORY_STORE.get(_FEEDBACK_CATEGORY, opportunity_id)
                return [record] if record else []

            results = _MEMORY_STORE.query(_FEEDBACK_CATEGORY, limit=limit)

            # Extract details from query results
            extracted = []
            for r in results:
                if "details" in r:
                    extracted.append(r["details"])
                else:
                    # If for some reason there's no details key, use the record itself
                    extracted.append(r)

            if category:
                extracted = [r for r in extracted if r.get("category") == category]
            if platform:
                extracted = [r for r in extracted if r.get("platform") == platform]

            return extracted
        except Exception as exc:
            logger.warning("Failed to retrieve feedback history: %s", exc)
            return []

    def compute_category_multiplier(self, category: str) -> float:
        """Compute score multiplier for a category based on feedback."""
        history = self.get_feedback_history(category=category, limit=200)
        if not history:
            return 1.0

        accepted = sum(1 for h in history if h.get("details", {}).get("outcome") == FeedbackOutcome.ACCEPTED.value)
        rejected = sum(1 for h in history if h.get("details", {}).get("outcome") == FeedbackOutcome.REJECTED.value)
        total = accepted + rejected

        if total == 0:
            return 1.0

        acceptance_rate = accepted / total

        if acceptance_rate > 0.7:
            return 1.2
        elif acceptance_rate > 0.5:
            return 1.0
        elif acceptance_rate > 0.3:
            return 0.8
        else:
            return 0.6

    def compute_platform_multiplier(self, platform: str) -> float:
        """Compute score multiplier for a platform based on feedback."""
        history = self.get_feedback_history(platform=platform, limit=200)
        if not history:
            return 1.0

        accepted = sum(1 for h in history if h.get("details", {}).get("outcome") == FeedbackOutcome.ACCEPTED.value)
        rejected = sum(1 for h in history if h.get("details", {}).get("outcome") == FeedbackOutcome.REJECTED.value)
        total = accepted + rejected

        if total == 0:
            return 1.0

        acceptance_rate = accepted / total

        if acceptance_rate > 0.7:
            return 1.15
        elif acceptance_rate > 0.5:
            return 1.0
        elif acceptance_rate > 0.3:
            return 0.85
        else:
            return 0.7

    def compute_technology_multiplier(self, technology_tag: str) -> float:
        """Compute score multiplier for a technology tag based on feedback."""
        history = self.get_feedback_history(limit=500)
        if not history:
            return 1.0

        tag_accepted = 0
        tag_total = 0

        for h in history:
            details = h.get("details", {})
            tags = details.get("technology_tags", [])
            if technology_tag.lower() in [t.lower() for t in tags]:
                tag_total += 1
                if details.get("outcome") == FeedbackOutcome.ACCEPTED.value:
                    tag_accepted += 1

        if tag_total == 0:
            return 1.0

        acceptance_rate = tag_accepted / tag_total

        if acceptance_rate > 0.7:
            return 1.1
        elif acceptance_rate > 0.5:
            return 1.0
        elif acceptance_rate > 0.3:
            return 0.9
        else:
            return 0.8

    def get_personalized_multipliers(
        self,
        category: str,
        platform: str,
        technology_tags: list[str],
    ) -> dict[str, float]:
        """Get all multipliers for personalized scoring."""
        category_mult = self.compute_category_multiplier(category)
        platform_mult = self.compute_platform_multiplier(platform)

        tech_mults = [self.compute_technology_multiplier(tag) for tag in technology_tags]
        avg_tech_mult = sum(tech_mults) / max(len(tech_mults), 1) if tech_mults else 1.0

        combined = category_mult * platform_mult * avg_tech_mult

        return {
            "category_multiplier": round(category_mult, 3),
            "platform_multiplier": round(platform_mult, 3),
            "technology_multiplier": round(avg_tech_mult, 3),
            "combined_multiplier": round(combined, 3),
        }

    def get_feedback_summary(self) -> dict[str, Any]:
        """Get summary statistics of all feedback."""
        history = self.get_feedback_history(limit=1000)

        total = len(history)
        accepted = sum(1 for h in history if h.get("details", {}).get("outcome") == FeedbackOutcome.ACCEPTED.value)
        rejected = sum(1 for h in history if h.get("details", {}).get("outcome") == FeedbackOutcome.REJECTED.value)
        skipped = sum(1 for h in history if h.get("details", {}).get("outcome") == FeedbackOutcome.SKIPPED.value)

        by_category: dict[str, dict[str, int]] = {}
        by_platform: dict[str, dict[str, int]] = {}

        for h in history:
            details = h.get("details", {})
            cat = details.get("category", "unknown")
            plat = details.get("platform", "unknown")
            outcome = details.get("outcome", "unknown")

            if cat not in by_category:
                by_category[cat] = {"accepted": 0, "rejected": 0, "skipped": 0}
            if plat not in by_platform:
                by_platform[plat] = {"accepted": 0, "rejected": 0, "skipped": 0}

            if outcome == FeedbackOutcome.ACCEPTED.value:
                by_category[cat]["accepted"] += 1
                by_platform[plat]["accepted"] += 1
            elif outcome == FeedbackOutcome.REJECTED.value:
                by_category[cat]["rejected"] += 1
                by_platform[plat]["rejected"] += 1
            elif outcome == FeedbackOutcome.SKIPPED.value:
                by_category[cat]["skipped"] += 1
                by_platform[plat]["skipped"] += 1

        return {
            "total_feedback": total,
            "accepted": accepted,
            "rejected": rejected,
            "skipped": skipped,
            "acceptance_rate": round(accepted / max(total, 1), 3),
            "by_category": by_category,
            "by_platform": by_platform,
        }


_GLOBAL_FEEDBACK_LOOP: FeedbackLoop | None = None


def get_feedback_loop() -> FeedbackLoop:
    global _GLOBAL_FEEDBACK_LOOP
    if _GLOBAL_FEEDBACK_LOOP is None:
        _GLOBAL_FEEDBACK_LOOP = FeedbackLoop()
        logger.info("FeedbackLoop initialized")
    return _GLOBAL_FEEDBACK_LOOP
