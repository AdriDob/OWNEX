"""Tests for the Training Pipeline (cores/learning/training_pipeline.py)."""

from __future__ import annotations

import pytest

from cores.learning.training_pipeline import TrainingPipeline, generate_training_plan


def test_generate_plan_for_gap_has_resources():
    plan = generate_training_plan("idor", "bug_bounty", "beginner", "intermediate", 10.0)
    assert plan["skill"] == "idor"
    assert plan["total_estimated_hours"] > 0
    assert plan["resources"], "should include curated resources"
    assert plan["daily_plans"], "should include daily plan"


@pytest.fixture()
def pipeline(tmp_path):
    return TrainingPipeline(data_dir=tmp_path)


def test_plan_persistence_roundtrip(pipeline):
    plan = pipeline.generate_plan_for_gap("xss", "bug_bounty")
    pipeline.save_plan(plan)
    loaded = pipeline.get_plan("xss", "bug_bounty")
    assert loaded is not None
    assert loaded.skill == "xss"


def test_record_completion_and_progress(pipeline):
    pipeline.record_completion("idor", "idor-lab-1", True, "solved")
    progress = pipeline.get_progress("idor")
    assert len(progress["completed"]) == 1
    assert progress["completed"][0]["exercise_id"] == "idor-lab-1"


def test_unknown_skill_falls_back_to_generic(pipeline):
    plan = pipeline.generate_plan_for_gap("creative_writing", "tech_content")
    assert plan.resources, "generic resource should be appended even for unknown skills"


def test_daily_plan_resources_linked(pipeline):
    plan = pipeline.generate_plan_for_gap("python", "dev_bounty")
    daily = plan.daily_plans[0]
    if daily.resources:
        # Every referenced resource id must exist in the plan resource list.
        resource_ids = {r.id for r in plan.resources}
        for r in daily.resources:
            assert r.id in resource_ids


def test_quiet_noop_when_no_data(pipeline):
    assert pipeline.get_progress("missing_skill")["completed"] == []
