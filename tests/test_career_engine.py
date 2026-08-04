"""Tests for the OWNEX Career Engine and CapabilityRegistry auto-integration."""

from __future__ import annotations

import pytest

from cores.career_engine import (
    CATEGORY_REQUIRED_SKILLS,
    CareerEngine,
    CareerRoadmap,
    DailyTrainingPlan,
    SkillGap,
    register_all_capabilities,
    register_capabilities,
)
from cores.direct_work_engine.models import (
    ExperienceLevel,
    OpportunityCategory,
    UserProfile,
)


@pytest.fixture
def engineer_profile() -> UserProfile:
    """A realistic senior engineer profile (Python/backend oriented)."""
    return UserProfile(
        name="Test Engineer",
        country="Argentina",
        languages={"es", "en"},
        skills={"python", "sql", "rest_api", "git", "docker", "pytest"},
        experience_level=ExperienceLevel.SENIOR,
        availability_hours=30.0,
    )


@pytest.fixture
def beginner_profile() -> UserProfile:
    """A beginner with almost no skills — many gaps expected."""
    return UserProfile(
        name="Test Beginner",
        country="Argentina",
        languages={"es"},
        skills={"python"},
        experience_level=ExperienceLevel.JUNIOR,
        availability_hours=10.0,
    )


class TestSkillGapDetection:
    def test_detects_missing_backend_skills(self, engineer_profile):
        engine = CareerEngine()
        gaps = engine.detect_skill_gaps(engineer_profile, categories=[OpportunityCategory.BACKEND])
        gap_skills = {g.skill for g in gaps}
        # python, sql, rest_api, docker, git are present — no gaps expected there.
        assert "python" not in gap_skills
        assert "sql" not in gap_skills
        # All gaps must be real, non-empty skills.
        assert all(g.skill for g in gaps)

    def test_beginner_has_more_gaps_than_engineer(self, engineer_profile, beginner_profile):
        engine = CareerEngine()
        engineer_gaps = engine.detect_skill_gaps(engineer_profile)
        beginner_gaps = engine.detect_skill_gaps(beginner_profile)
        assert len(beginner_gaps) > len(engineer_gaps)

    def test_gaps_are_typed(self, engineer_profile):
        engine = CareerEngine()
        gaps = engine.detect_skill_gaps(engineer_profile)
        assert all(isinstance(g, SkillGap) for g in gaps)
        assert all(g.priority in ("high", "medium", "low") for g in gaps)


class TestRoadmap:
    def test_build_roadmap_returns_typed_roadmap(self, beginner_profile):
        engine = CareerEngine()
        roadmap = engine.build_roadmap(beginner_profile)
        assert isinstance(roadmap, CareerRoadmap)
        assert roadmap.total_gaps == len(roadmap.items)
        assert roadmap.generated_at
        # High priority gaps (skills shared by 2+ categories) come first.
        if roadmap.high_priority:
            assert roadmap.items[0].priority == "high"

    def test_roadmap_high_priority_shared_skills(self, engineer_profile):
        engine = CareerEngine()
        roadmap = engine.build_roadmap(engineer_profile)
        for gap in roadmap.high_priority:
            assert gap.priority == "high"


class TestInterviewPrep:
    def test_known_category_returns_questions(self):
        engine = CareerEngine()
        questions = engine.prepare_interview(OpportunityCategory.BACKEND)
        assert isinstance(questions, list)
        assert len(questions) >= 1
        assert all(isinstance(q, str) and q for q in questions)

    def test_unknown_category_returns_empty(self):
        engine = CareerEngine()
        assert engine.prepare_interview(OpportunityCategory.IOT) == []


class TestDailyTraining:
    def test_daily_training_plan_shape(self, beginner_profile):
        engine = CareerEngine()
        plan = engine.build_daily_training(beginner_profile)
        assert isinstance(plan, DailyTrainingPlan)
        assert plan.date
        assert plan.estimated_minutes > 0
        assert len(plan.focus_skills) <= 3
        assert plan.drills  # at least one drill
        assert all(d for d in plan.drills)

    def test_daily_training_targets_real_gaps(self, beginner_profile):
        engine = CareerEngine()
        plan = engine.build_daily_training(beginner_profile)
        for skill in plan.focus_skills:
            assert skill in {g.skill for g in engine.detect_skill_gaps(beginner_profile)}


class TestAnalyzeProfile:
    def test_analysis_summary_shape(self, engineer_profile):
        engine = CareerEngine()
        summary = engine.analyze_profile(engineer_profile)
        assert summary["name"] == "Test Engineer"
        assert summary["skills_count"] == len(engineer_profile.skills)
        assert summary["skill_gaps"] >= 0
        assert summary["generated_at"]


class TestCategoryCoverage:
    def test_all_categories_have_skills(self):
        """Every declared category must have required skills (no magic gaps)."""
        from cores.direct_work_engine.models import OpportunityCategory as OpportunityCategoryAlias

        missing = [c.value for c in OpportunityCategoryAlias if c not in CATEGORY_REQUIRED_SKILLS]
        assert not missing, f"Categories without required skills: {missing}"


class TestCapabilityRegistration:
    def test_register_career_engine_capabilities(self):
        from core.capabilities.registry import get_capability_registry, reset_capability_registry

        reset_capability_registry()
        register_capabilities()
        reg = get_capability_registry()
        entries = reg.find("career_analysis")
        assert len(entries) == 1
        assert entries[0].module == "career_engine"
        assert "build_roadmap" in entries[0].metadata["capabilities"]

    def test_register_all_capabilities_includes_direct_work_engine(self):
        from core.capabilities.registry import get_capability_registry, reset_capability_registry

        reset_capability_registry()
        register_all_capabilities()
        reg = get_capability_registry()
        dwe = reg.find("opportunity_discovery")
        career = reg.find("career_analysis")
        assert len(dwe) == 1
        assert dwe[0].module == "direct_work_engine"
        assert len(career) == 1

    def test_registration_is_idempotent(self):
        from core.capabilities.registry import get_capability_registry, reset_capability_registry

        reset_capability_registry()
        register_all_capabilities()
        register_all_capabilities()
        reg = get_capability_registry()
        assert len(reg.find("opportunity_discovery")) == 1
        assert len(reg.find("career_analysis")) == 1
