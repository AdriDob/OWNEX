"""Tests for Mercenary Filter — aggressive opportunity scoring."""

import pytest

from core.opportunity.mercenary_filter import (
    CATEGORY_PRIORITIES,
    MercenaryAttributes,
    MercenaryFilter,
    OpportunityCategory,
    get_mercenary_filter,
)


@pytest.fixture
def mercenary_filter():
    """Create mercenary filter instance."""
    return MercenaryFilter()


def test_mercenary_filter_initialization(mercenary_filter):
    """Test mercenary filter initialization."""
    assert mercenary_filter is not None
    assert mercenary_filter.MIN_SCORE_THRESHOLD == 80.0
    assert mercenary_filter.WEIGHT_VERIFIABLE_PAYMENT == 20.0
    assert mercenary_filter.WEIGHT_DEFINED_TASK == 20.0


def test_mercenary_filter_singleton():
    """Test that get_mercenary_filter returns the same instance."""
    filter1 = get_mercenary_filter()
    filter2 = get_mercenary_filter()
    assert filter1 is filter2


def test_category_priorities():
    """Test category priorities mapping."""
    assert CATEGORY_PRIORITIES[OpportunityCategory.BUG_BOUNTY].name == "EXTREME"
    assert CATEGORY_PRIORITIES[OpportunityCategory.DEVELOPMENT_TASKS].name == "EXTREME"
    assert CATEGORY_PRIORITIES[OpportunityCategory.TESTING_QA].name == "HIGH"
    assert CATEGORY_PRIORITIES[OpportunityCategory.AI_EVALUATION].name == "MEDIUM_HIGH"


def test_perfect_opportunity_score(mercenary_filter):
    """Test scoring of a perfect opportunity (should pass filter)."""
    attrs = MercenaryAttributes(
        verifiable_payment=True,
        payment_amount_verified=True,
        payment_history_good=True,
        defined_objective=True,
        clear_deliverable=True,
        scope_well_defined=True,
        no_interview_required=True,
        no_portfolio_required=True,
        no_experience_required=True,
        argentina_compatible=True,
        remote_work=True,
        flexible_hours=True,
        real_it_work=True,
        technical_skill_required=True,
        no_mechanical_task=True,
        reasonable_timeframe=True,
        estimated_hours=8.0,
        hourly_rate_competitive=True,
        category=OpportunityCategory.BUG_BOUNTY,
    )

    score = mercenary_filter.score_opportunity("test-opp-1", attrs)

    assert score.total_score >= 80.0
    assert score.passed_filter is True
    assert score.category == OpportunityCategory.BUG_BOUNTY
    assert score.category_priority.name == "EXTREME"


def test_low_quality_opportunity_score(mercenary_filter):
    """Test scoring of a low quality opportunity (should fail filter)."""
    attrs = MercenaryAttributes(
        verifiable_payment=False,
        payment_amount_verified=False,
        defined_objective=False,
        clear_deliverable=False,
        no_interview_required=False,  # BLOCKER
        no_portfolio_required=False,  # BLOCKER
        argentina_compatible=False,
        remote_work=False,
        real_it_work=False,
        no_mechanical_task=False,  # BLOCKER
        reasonable_timeframe=False,
        estimated_hours=0.0,
        hourly_rate_competitive=False,
        category=OpportunityCategory.AI_EVALUATION,
    )

    score = mercenary_filter.score_opportunity("test-opp-2", attrs)

    assert score.total_score < 80.0
    assert score.passed_filter is False
    assert "interview_required" in score.blockers
    assert "portfolio_required" in score.blockers


def test_get_category_bug_bounty(mercenary_filter):
    """Test category detection for bug bounty platforms."""
    for platform in ["hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi"]:
        category = mercenary_filter.get_category(platform, "dev_bounty", ["security"])
        assert category == OpportunityCategory.BUG_BOUNTY


def test_get_category_dev_bounty(mercenary_filter):
    """Test category detection for dev bounty platforms."""
    for platform in ["algora", "opire", "superteam", "gitcoin", "bountysource"]:
        category = mercenary_filter.get_category(platform, "dev_bounty", ["code"])
        assert category == OpportunityCategory.DEVELOPMENT_TASKS


def test_get_category_ai_evaluation(mercenary_filter):
    """Test category detection for AI evaluation platforms."""
    for platform in ["outlier", "dataannotation", "mindrift", "remotasks"]:
        category = mercenary_filter.get_category(platform, "ai_work", ["ml"])
        assert category == OpportunityCategory.AI_EVALUATION


def test_get_category_devops(mercenary_filter):
    """Test category detection for DevOps based on tags."""
    category = mercenary_filter.get_category("freelancer", "task", ["devops", "docker"])
    assert category == OpportunityCategory.DEVOPS_CLOUD


def test_get_category_game_programming(mercenary_filter):
    """Test category detection for game programming based on tags."""
    category = mercenary_filter.get_category("freelancer", "task", ["unity", "gamedev"])
    assert category == OpportunityCategory.GAME_PROGRAMMING


def test_mercenary_attributes_defaults():
    """Test MercenaryAttributes default values."""
    attrs = MercenaryAttributes()
    assert attrs.verifiable_payment is False
    assert attrs.defined_objective is False
    assert attrs.no_interview_required is False
    assert attrs.category == OpportunityCategory.DEVELOPMENT_TASKS


def test_cache_functionality(mercenary_filter):
    """Test that filter caches scores."""
    attrs = MercenaryAttributes(
        verifiable_payment=True,
        defined_objective=True,
        no_interview_required=True,
        no_portfolio_required=True,
        category=OpportunityCategory.BUG_BOUNTY,
    )

    # First call
    score1 = mercenary_filter.score_opportunity("cache-test", attrs)
    # Second call (should return cached)
    score2 = mercenary_filter.score_opportunity("cache-test", attrs)

    assert score1 is score2

    # Clear cache
    mercenary_filter.clear_cache()
    # Third call (should create new)
    score3 = mercenary_filter.score_opportunity("cache-test", attrs)

    assert score1 is not score3


def test_score_component_breakdown(mercenary_filter):
    """Test that score components are calculated correctly."""
    attrs = MercenaryAttributes(
        verifiable_payment=True,
        defined_objective=True,
        no_interview_required=True,
        no_portfolio_required=True,
        argentina_compatible=True,
        remote_work=True,
        real_it_work=True,
        reasonable_timeframe=True,
        category=OpportunityCategory.BUG_BOUNTY,
    )

    score = mercenary_filter.score_opportunity("component-test", attrs)

    # Each component should have some score
    assert score.payment_score > 0
    assert score.task_definition_score > 0
    assert score.requirements_score > 0
    assert score.location_score > 0
    assert score.technical_score > 0
    assert score.time_score > 0

    # Reasons should be populated
    assert len(score.reasons) > 0
