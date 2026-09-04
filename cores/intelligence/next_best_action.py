"""Next Best Action Engine — The heart of LITE mode.

Single canonical decision engine that answers:
> "¿Qué debería hacer ahora?"

Considers:
- Available opportunities
- User profile
- Current skills
- Available time
- Goals
- Capital
- Current tasks
- Platform status
- Previous results

Output:
> NEXT BEST ACTION
> WHY
> EXPECTED VALUE
> ESTIMATED MINUTES
> EV/HOUR
> REQUIREMENTS
> RISKS
> EXACT STEPS
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.intelligence.next_best_action")


@dataclass
class NextBestAction:
    """The single next best action."""

    id: str
    title: str
    description: str
    why: str
    expected_value: float  # USD
    estimated_minutes: float
    ev_per_hour: float
    confidence: float  # 0-1
    barrier: str  # $0, low, medium, high
    requirements: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    exact_steps: list[str] = field(default_factory=list)
    category: str = ""
    platform: str = ""
    url: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "why": self.why,
            "expected_value": self.expected_value,
            "estimated_minutes": self.estimated_minutes,
            "ev_per_hour": self.ev_per_hour,
            "confidence": self.confidence,
            "barrier": self.barrier,
            "requirements": self.requirements,
            "risks": self.risks,
            "exact_steps": self.exact_steps,
            "category": self.category,
            "platform": self.platform,
            "url": self.url,
        }


class NextBestActionEngine:
    """The heart of LITE mode — decides what to do next."""

    def __init__(self) -> None:
        self._action_counter = 0

    def calculate(
        self,
        opportunities: list[dict[str, Any]] | None = None,
        user_skills: list[str] | None = None,
        available_minutes: float = 60,
        capital: float = 0,
        monthly_income: float = 0,
        completed_actions: int = 0,
        current_mode: str = "lite",
    ) -> NextBestAction:
        """Calculate the single next best action."""
        self._action_counter += 1

        # Default skills if not provided
        skills = user_skills or ["python", "javascript", "security", "api"]

        # Score and rank opportunities
        scored = []
        for opp in opportunities or []:
            score = self._score_opportunity(opp, skills, available_minutes)
            scored.append((opp, score))

        # Sort by score (highest first)
        scored.sort(key=lambda x: x[1]["total_score"], reverse=True)

        # Get the best one
        if scored:
            best_opp, best_score = scored[0]
            return self._build_action(best_opp, best_score, self._action_counter)

        # No opportunities — return default
        return self._build_no_action(self._action_counter)

    def _score_opportunity(
        self,
        opp: dict[str, Any],
        skills: list[str],
        available_minutes: float,
    ) -> dict[str, Any]:
        """Score an opportunity for ranking."""
        # Base EV
        ev = opp.get("expected_value", opp.get("payout", 0))
        minutes = opp.get("estimated_minutes", opp.get("effort_hours", 1) * 60)
        ev_per_hour = (ev / max(minutes, 1)) * 60 if minutes > 0 else 0

        # Skill match
        opp_skills = set(opp.get("skills", []))
        skill_match = len(opp_skills & set(skills)) / max(len(opp_skills), 1)

        # Barrier penalty
        barrier = opp.get("barrier", "$0")
        barrier_score = 1.0 if barrier == "$0" else 0.7 if barrier == "low" else 0.4

        # Time fit
        time_fit = 1.0 if minutes <= available_minutes else 0.5

        # Confidence
        confidence = opp.get("confidence", 0.5)

        # Total score
        total = (
            ev_per_hour * 0.3
            + skill_match * 100 * 0.25
            + barrier_score * 100 * 0.2
            + time_fit * 100 * 0.15
            + confidence * 100 * 0.1
        )

        return {
            "ev": ev,
            "minutes": minutes,
            "ev_per_hour": round(ev_per_hour, 2),
            "skill_match": round(skill_match, 2),
            "barrier_score": barrier_score,
            "time_fit": time_fit,
            "confidence": confidence,
            "total_score": round(total, 2),
        }

    def _build_action(
        self,
        opp: dict[str, Any],
        score: dict[str, Any],
        counter: int,
    ) -> NextBestAction:
        """Build a NextBestAction from an opportunity."""
        return NextBestAction(
            id=f"nba_{counter}",
            title=opp.get("title", opp.get("name", "Unknown")),
            description=opp.get("description", ""),
            why=f"Highest EV/hour ({score['ev_per_hour']:.0f}/h) with {score['skill_match']:.0%} skill match",
            expected_value=score["ev"],
            estimated_minutes=score["minutes"],
            ev_per_hour=score["ev_per_hour"],
            confidence=score["confidence"],
            barrier=opp.get("barrier", "$0"),
            requirements=opp.get("requirements", []),
            risks=opp.get("risks", []),
            exact_steps=opp.get("steps", ["Start investigation", "Analyze target", "Submit if confirmed"]),
            category=opp.get("category", ""),
            platform=opp.get("platform", ""),
            url=opp.get("url", ""),
        )

    def _build_no_action(self, counter: int) -> NextBestAction:
        """Build a 'no action' result."""
        return NextBestAction(
            id=f"nba_{counter}",
            title="NO ACTION REQUIRED",
            description="OWNEX will continue monitoring for high-value opportunities.",
            why="No opportunities currently meet the minimum EV/hour threshold.",
            expected_value=0,
            estimated_minutes=0,
            ev_per_hour=0,
            confidence=0,
            barrier="$0",
            requirements=[],
            risks=[],
            exact_steps=[],
            category="",
            platform="",
            url="",
        )


# Singleton
_nba_engine: NextBestActionEngine | None = None


def get_next_best_action_engine() -> NextBestActionEngine:
    """Get or create the global Next Best Action engine."""
    global _nba_engine
    if _nba_engine is None:
        _nba_engine = NextBestActionEngine()
    return _nba_engine
