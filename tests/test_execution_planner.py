"""Tests for the Magic Experience / Opportunity Execution planner."""

from __future__ import annotations

from cores.direct_work_engine.execution_planner import plan_execution, plan_objective


def test_plan_objective_classifies_requests() -> None:
    plan = plan_objective("Create a website for my portfolio")
    assert plan.category == "frontend"
    assert plan.goal
    assert plan.requirements
    assert plan.plan
    assert plan.verification
    assert plan.normal_hours >= plan.ownex_hours

    fiverr = plan_objective("Prepare the Fiverr delivery for the client")
    assert fiverr.category == "delivery"
    assert fiverr.deliverables

    bug = plan_objective("Analyze this bug in the login endpoint")
    assert bug.category == "security"


def test_plan_objective_empty_returns_error() -> None:
    plan = plan_objective("   ")
    assert plan.error == "Objetivo vacío"
    assert plan.category == "general"


def test_plan_objective_fallback_category() -> None:
    plan = plan_objective("Help me with something random")
    assert plan.category == "general"
    assert plan.goal
    assert plan.normal_hours > 0


def test_time_compression_ratio_present() -> None:
    plan = plan_objective("Create documentation for the API")
    d = plan.to_dict()
    assert "time_compression" in d
    assert d["time_compression"]["ratio"] >= 1.0


def test_plan_execution_report_and_links() -> None:
    opportunity = {
        "id": "op-1",
        "title": "Fix a bug in a Django REST endpoint",
        "category": "dev_bounty",
        "platform": "opire",
        "url": "https://opire.dev/task/123",
        "reward": 300.0,
        "difficulty": "medium",
        "required_skills": ["python", "django"],
        "estimated_time_hours": 2.0,
        "portfolio_required": False,
    }
    plan = plan_execution(opportunity)
    d = plan.to_dict()
    assert d["title"] == "Fix a bug in a Django REST endpoint"
    assert d["reward_usd"] == 300.0
    assert d["direct_links"]["official_platform"] == "https://opire.dev/task/123"
    assert d["success_probability"] > 0
    assert 0 <= d["automation_pct"] <= 100
    assert len(d["roadmap"]) == 4
    assert d["roadmap"][0]["stage"] == "1. Preparation"
    assert d["expected_value_per_hour"] > 0
    assert d["next_button"]


def test_plan_execution_accepts_workitem_like_object() -> None:
    from types import SimpleNamespace

    item = SimpleNamespace(
        id="wi-9",
        title="Annotate dataset",
        category="data_annotation",
        platform="outlier",
        url="https://outlier.ai/jobs/9",
        reward=150.0,
        difficulties="low",
        description="annotate",
        required_skills=["reading"],
        estimated_time_hours=3.0,
        needs_account=True,
    )
    plan = plan_execution(item)
    assert plan.platform == "outlier"
    assert plan.reward_usd == 150.0
    assert plan.human_work_minutes >= 5.0  # account creation counted


def test_plan_execution_high_reward_is_honest() -> None:
    opportunity = {
        "id": "op-2",
        "title": "Complex bounty",
        "category": "bug_bounty",
        "platform": "hackerone",
        "url": "https://hackerone.com/x",
        "reward": 2000.0,
        "difficulty": "high",
        "estimated_time_hours": 40.0,
    }
    plan = plan_execution(opportunity)
    assert plan.success_probability <= 0.5  # competitive, not guaranteed
    assert plan.original_hours >= 20.0
