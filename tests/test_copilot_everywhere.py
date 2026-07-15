"""Tests for COPILOT Everywhere — system context, scheduler hooks, targets integration."""

from __future__ import annotations

from core.copilot.agent import CopilotAgent
from core.copilot.permissions import AuthorityLevel
from core.copilot.recommender import Recommendation
from core.copilot.system_context import CopilotContext, SystemContextBuilder

# ── SystemContextBuilder ─────────────────────────────────────────────


def test_system_context_builder_no_db():
    """Builder works without a DB factory (returns empty aggregates)."""
    builder = SystemContextBuilder()
    ctx = builder.build(authority=AuthorityLevel.SENIOR_HUNTER)
    assert isinstance(ctx, CopilotContext)
    state = ctx.system_state
    assert "targets" in state
    assert "findings" in state
    assert "collected_at" in state
    assert state["targets"] == []
    assert state["findings"] == {}


def test_system_context_top_actions_no_targets():
    builder = SystemContextBuilder()
    ctx = builder.build()
    actions = builder.top_actions(ctx)
    assert isinstance(actions, list)
    if len(actions) > 0:
        assert actions[0]["action"] == "discover_targets"


def test_system_context_top_actions_with_open_findings():
    builder = SystemContextBuilder()
    ctx = builder.build(
        authority=AuthorityLevel.SENIOR_HUNTER,
        extra={
            "findings": {"total": 5, "open": 3, "confirmed": 1, "rejected": 1},
            "targets": [],
        },
    )
    actions = builder.top_actions(ctx)
    actions_by_name = {a["action"]: a for a in actions}
    assert "validate_findings" in actions_by_name
    assert actions_by_name["validate_findings"]["count"] == 3


def test_system_context_top_actions_with_confirmed():
    builder = SystemContextBuilder()
    ctx = builder.build(
        authority=AuthorityLevel.SENIOR_HUNTER,
        extra={
            "findings": {"total": 2, "open": 0, "confirmed": 2, "rejected": 0},
            "targets": [],
        },
    )
    actions = builder.top_actions(ctx)
    actions_by_name = {a["action"]: a for a in actions}
    assert "generate_reports" in actions_by_name


def test_system_context_top_actions_with_high_value_targets():
    builder = SystemContextBuilder()
    ctx = builder.build(
        authority=AuthorityLevel.SENIOR_HUNTER,
        extra={
            "findings": {"total": 0, "open": 0, "confirmed": 0, "rejected": 0},
            "targets": [
                {"id": 1, "name": "high", "score": 8.5, "status": "active"},
                {"id": 2, "name": "medium", "score": 5.0, "status": "active"},
                {"id": 3, "name": "low", "score": 2.0, "status": "active"},
            ],
        },
    )
    actions = builder.top_actions(ctx)
    actions_by_name = {a["action"]: a for a in actions}
    assert "deep_study_targets" in actions_by_name
    assert actions_by_name["deep_study_targets"]["count"] == 1  # only the 8.5 one
    assert "recon_targets" in actions_by_name
    assert actions_by_name["recon_targets"]["count"] == 1  # the 5.0 one


def test_system_context_prioritize_targets():
    builder = SystemContextBuilder()
    targets = [
        {"id": 1, "score": 3.0},
        {"id": 2, "score": 9.0},
        {"id": 3, "score": 5.0},
    ]
    sorted_t = builder.prioritize_targets(targets)
    assert sorted_t[0]["id"] == 2
    assert sorted_t[1]["id"] == 3
    assert sorted_t[2]["id"] == 1


# ── CopilotAgent: recommend_for_system ──────────────────────────────


def test_recommend_for_system_no_db():
    agent = CopilotAgent(authority=AuthorityLevel.SENIOR_HUNTER)
    actions = agent.recommend_for_system()
    assert isinstance(actions, list)
    # Without DB, returns system-level recommendations based on empty state
    # Should include discover_targets since there's nothing
    action_names = [a["action"] for a in actions]
    assert "discover_targets" in action_names or len(actions) == 0


def test_recommend_for_system_with_state():
    agent = CopilotAgent(authority=AuthorityLevel.SENIOR_HUNTER)
    actions = agent.recommend_for_system(
        extra_state={
            "findings": {"total": 10, "open": 4, "confirmed": 3, "rejected": 3},
            "targets": [
                {"id": 1, "name": "fintech", "score": 9.0, "status": "active"},
                {"id": 2, "name": "ecom", "score": 6.0, "status": "active"},
            ],
        }
    )
    assert isinstance(actions, list)
    action_names = [a["action"] for a in actions]
    assert "validate_findings" in action_names
    assert "deep_study_targets" in action_names
    assert "generate_reports" in action_names


# ── CopilotAgent: create_plan and event subscriber ──────────────────


def test_copilot_create_target_plan():
    """Simulate what the target:created subscriber does."""
    agent = CopilotAgent(authority=AuthorityLevel.SENIOR_HUNTER)
    plan = agent.create_plan(finding=None)
    assert plan is not None
    assert hasattr(plan, "id")
    assert hasattr(plan, "to_dict")

    # Verify it logged the decision
    journal = agent.get_decision_journal(action="create_plan")
    assert len(journal) >= 1


# ── Recommendation class ────────────────────────────────────────────


def test_recommendation_to_dict():
    rec = Recommendation(
        action="test_action",
        description="Test description",
        priority=5,
        reason="Because",
        risk=0.3,
    )
    d = rec.to_dict()
    assert d["action"] == "test_action"
    assert d["priority"] == 5
    assert d["risk"] == 0.3


def test_recommendation_defaults():
    rec = Recommendation(action="minimal", description="test")
    assert rec.priority == 0
    assert rec.risk == 0.0
    assert rec.reason == ""
