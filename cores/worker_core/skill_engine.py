"""Skill Engine — Analyzes skill gaps and builds learning plans for work items.

Integrates with WorkerCore prepare phase to provide skill gap analysis
and learning plans before execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from cores.direct_work_engine.models import (
    Opportunity,
    OpportunityCategory,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.profile_builder import IntelligentProfileBuilder, ProfileAssets
from cores.direct_work_engine.skill_gap import SkillAmplifier, SkillGapReport

logger = logging.getLogger("ownex.worker_core.skill_engine")


@dataclass(slots=True)
class SkillAnalysisResult:
    """Result of skill analysis for a work item."""

    work_item_id: str
    opportunity_id: str
    skill_gap_report: SkillGapReport | None = None
    profile_assets: ProfileAssets | None = None
    optimized_profile: UserProfile | None = None
    readiness_score: float = 0.0
    can_execute: bool = False
    missing_critical_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_item_id": self.work_item_id,
            "opportunity_id": self.opportunity_id,
            "skill_gap_report": self.skill_gap_report.to_dict() if self.skill_gap_report else None,
            "profile_assets": self.profile_assets.to_dict() if self.profile_assets else None,
            "optimized_profile": self.optimized_profile.__dict__ if self.optimized_profile else None,
            "readiness_score": self.readiness_score,
            "can_execute": self.can_execute,
            "missing_critical_skills": self.missing_critical_skills,
        }


class SkillEngine:
    """Analyzes skill gaps and optimizes profiles for work execution.

    Used in WorkerCore PREPARE phase to ensure user is ready for execution.
    """

    def __init__(self):
        self._skill_amplifier = SkillAmplifier()
        self._profile_builder = IntelligentProfileBuilder()
        self.logger = logging.getLogger("ownex.worker_core.skill_engine")

    def _workitem_to_opportunity(self, work_item: Any) -> Opportunity:
        """Convert WorkItem to Opportunity."""
        platform_str = getattr(work_item, "platform", "unknown")
        try:
            platform = WorkPlatform(platform_str.lower())
        except ValueError:
            platform = WorkPlatform.OTHER

        category_str = getattr(work_item, "category", "software_engineering")
        try:
            category = OpportunityCategory(category_str)
        except ValueError:
            category = OpportunityCategory.SOFTWARE_ENGINEERING

        return Opportunity(
            id=getattr(work_item, "opportunity_id", getattr(work_item, "id", "unknown")),
            title=getattr(work_item, "title", "Untitled"),
            platform=platform,
            category=category,
            payment=getattr(work_item, "estimated_reward_usd", 0.0),
            estimated_time_hours=getattr(work_item, "estimated_hours", 1.0),
            technology_tags=getattr(work_item, "technologies", []),
            interview_required=getattr(work_item, "interview_required", False),
            portfolio_required=getattr(work_item, "portfolio_required", False),
        )

    def _optimize_profile_for_opportunity(self, profile: UserProfile, work_item: Any) -> UserProfile:
        """Create an optimized profile variant tailored for this specific opportunity."""
        # For now, return the original profile
        # Future: add skill highlighting, reorder skills, adjust bio for opportunity
        return profile

    def _identify_critical_missing(self, report: SkillGapReport, work_item: Any) -> list[str]:
        """Identify skills that are critical for this work item and missing."""
        critical = []
        category = getattr(work_item, "category", "").lower()
        critical_map = {
            "backend": ["python", "sql", "api", "database"],
            "frontend": ["javascript", "react", "typescript", "css"],
            "full_stack": ["python", "javascript", "sql", "api"],
            "devops": ["docker", "kubernetes", "aws", "ci_cd"],
            "ai_engineering": ["python", "pytorch", "tensorflow", "mlops"],
            "game_development": ["c++", "unity", "c#", "graphics"],
        }
        critical_skills = critical_map.get(category, [])
        user_skills_lower = [s.lower() for s in report.user_skills]
        for skill in critical_skills:
            if skill not in user_skills_lower:
                critical.append(skill)
        return critical

    def analyze(self, work_item: Any, user_profile: UserProfile) -> SkillAnalysisResult:
        """Analyze skill gaps for a work item against user profile.

        Args:
            work_item: WorkItem with opportunity info
            user_profile: User's current profile

        Returns:
            SkillAnalysisResult with gap report, profile assets, and readiness
        """
        # Create opportunity from work item
        opportunity = self._workitem_to_opportunity(work_item)

        # Analyze skill gap
        skill_gap_report = self._skill_amplifier.analyze(opportunity, user_profile)

        # Build profile assets
        profile_assets = self._profile_builder.build(user_profile)

        # Optimize profile for this specific opportunity
        optimized_profile = self._optimize_profile_for_opportunity(user_profile, work_item)

        # Calculate readiness
        readiness = skill_gap_report.readiness if skill_gap_report else 0.0
        can_execute = readiness >= 0.6  # Threshold for autonomous execution

        # Identify critical missing skills
        critical_missing = self._identify_critical_missing(skill_gap_report, work_item)

        return SkillAnalysisResult(
            work_item_id=getattr(work_item, "id", "unknown"),
            opportunity_id=getattr(work_item, "opportunity_id", "unknown"),
            skill_gap_report=skill_gap_report,
            profile_assets=profile_assets,
            optimized_profile=optimized_profile,
            readiness_score=readiness,
            can_execute=can_execute,
            missing_critical_skills=critical_missing,
        )
