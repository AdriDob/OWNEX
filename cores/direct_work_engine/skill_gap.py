"""Skill Amplification — closes the gap between the user's skills and the job.

OWNEX never claims the user knows everything. It measures the distance between
the opportunity's technology stack and the user's real skills, then produces an
honest learning plan. Pure and decoupled: no side effects, no invented facts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cores.direct_work_engine.models import DifficultyLevel, Opportunity, UserProfile

logger = logging.getLogger("ownex.direct_work_engine.skill_gap")

# How reachable each difficulty level is for a learner (0-1).
_DIFFICULTY_REACH: dict[DifficultyLevel, float] = {
    DifficultyLevel.BEGINNER: 1.0,
    DifficultyLevel.INTERMEDIATE: 0.8,
    DifficultyLevel.ADVANCED: 0.4,
    DifficultyLevel.EXPERT: 0.1,
}


@dataclass(slots=True)
class SkillGapReport:
    """Readiness and learning plan for one opportunity vs the user profile."""

    opportunity_id: str
    required_skills: list[str] = field(default_factory=list)
    user_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    readiness: float = 0.0
    learning_plan: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "required_skills": self.required_skills,
            "user_skills": self.user_skills,
            "missing_skills": self.missing_skills,
            "readiness": self.readiness,
            "learning_plan": self.learning_plan,
        }


class SkillAmplifier:
    """Measures skill distance and builds a concrete learning plan."""

    def analyze(self, opportunity: Opportunity, profile: UserProfile) -> SkillGapReport:
        required = [str(t).strip().lower() for t in (opportunity.technology_tags or []) if str(t).strip()]
        user_skills = sorted({str(s).strip().lower() for s in (profile.skills or set()) if str(s).strip()})

        user_set = set(user_skills)
        missing = [t for t in required if t not in user_set]

        overlap = len([t for t in required if t in user_set]) / len(required) if required else 1.0

        reach = _DIFFICULTY_REACH.get(opportunity.difficulty, 0.5)
        readiness = max(
            0.0, min(1.0, 0.5 * overlap + 0.3 * reach + 0.2 * (1.0 if not opportunity.interview_required else 0.0))
        )

        return SkillGapReport(
            opportunity_id=opportunity.id,
            required_skills=required,
            user_skills=user_skills,
            missing_skills=missing,
            readiness=round(readiness, 3),
            learning_plan=self._build_plan(missing, bool(required)),
        )

    @staticmethod
    def _build_plan(missing: list[str], has_stack: bool) -> list[str]:
        if not has_stack:
            return ["No specific stack required — apply directly"]
        plan: list[str] = []
        for skill in missing:
            plan.append(f"Study the fundamentals of {skill}")
        if missing:
            plan.append("Build a minimal working scaffold with the missing stack")
        plan.append("Run the local tests until green")
        plan.append("Ask OWNEX to review the diff before delivery")
        return plan
