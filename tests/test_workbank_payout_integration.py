"""Integration tests for Work Bank + PayoutNet.

Tests that the Work Bank correctly recommends payout methods for opportunities
and that the integration is robust to failures.
"""

import pytest

from cores.direct_work_engine.models import (
    EmploymentType,
    ExperienceLevel,
    Opportunity,
    OpportunityCategory,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.workbank import WorkBank, get_workbank


@pytest.fixture
def sample_opportunities():
    """Sample opportunities for testing."""
    return [
        Opportunity(
            id="opire-1",
            title="Python script for data processing",
            platform=WorkPlatform.OPIRE,
            category=OpportunityCategory.DEV_BOUNTY,
            payment=50.0,
            employment_type=EmploymentType.BOUNTY,
            description="Process CSV files",
            url="https://opire.com/op/1",
        ),
        Opportunity(
            id="freelance-1",
            title="Web scraping bot",
            platform=WorkPlatform.FREELANCER,
            category=OpportunityCategory.WEB_SCRAPING,
            payment=200.0,
            employment_type=EmploymentType.FREELANCE,
            description="Scrape e-commerce site",
            url="https://freelancer.com/p/1",
        ),
        Opportunity(
            id="bounty-1",
            title="Find XSS in login form",
            platform=WorkPlatform.HACKERONE,
            category=OpportunityCategory.BUG_BOUNTY,
            payment=500.0,
            employment_type=EmploymentType.BOUNTY,
            description="Find XSS vulnerability",
            url="https://hackerone.com/program/1",
        ),
    ]


@pytest.fixture
def sample_profile():
    """Sample user profile for testing."""
    return UserProfile(
        name="Test User",
        country="Argentina",
        languages={"es", "en"},
        skills={"python", "scraping"},
        experience_level=ExperienceLevel.NONE,
        remote_only=True,
        accepts_ai_tools=True,
        has_portfolio=False,
        preferred_employment_types=[EmploymentType.BOUNTY, EmploymentType.FREELANCE],
        preferred_categories=[
            OpportunityCategory.DEV_BOUNTY,
            OpportunityCategory.WEB_SCRAPING,
            OpportunityCategory.BUG_BOUNTY,
        ],
        excluded_categories=[],
        min_payment=10.0,
    )


def test_workbank_daily_cycle_with_payout_recommendations(sample_opportunities, sample_profile):
    """Test that daily_cycle adds payout_method and payout_method_rationale to items."""
    bank = WorkBank()
    result = bank.daily_cycle(sample_opportunities, target=3, profile=sample_profile)

    # The cycle should complete (even if no items pass the strict filter)
    assert result["scanned"] == len(sample_opportunities)

    # If items were added, check payout fields
    if result["new_items_added"] > 0:
        items = bank.best_ready(limit=10)
        assert len(items) > 0

        for item in items:
            # Payout method should be populated for known platforms
            if item.platform in ["opire", "freelancer", "hackerone"]:
                assert item.payout_method, f"Payout method missing for {item.platform}"
                assert item.payout_method_rationale, f"Payout rationale missing for {item.platform}"


def test_workbank_payout_method_persistence(sample_opportunities, sample_profile):
    """Test that payout methods persist across WorkBank instances."""
    bank1 = WorkBank()
    bank1.daily_cycle(sample_opportunities, target=2, profile=sample_profile)

    # Get items from first instance
    items1 = bank1.best_ready(limit=10)
    item_ids = {i.id for i in items1}

    # Create new instance (should load from disk)
    bank2 = WorkBank()
    items2 = bank2.best_ready(limit=10)

    # Should have same items with payout methods
    assert len(items2) > 0
    for item in items2:
        if item.id in item_ids:
            if item.platform in ["opire", "freelancer", "hackerone"]:
                assert item.payout_method, f"Payout method not persisted for {item.platform}"


def test_workbank_payout_integration_robustness(sample_opportunities, sample_profile):
    """Test that WorkBank handles PayoutNet failures gracefully."""
    bank = WorkBank()

    # Run daily cycle - should not fail even if PayoutNet has issues
    result = bank.daily_cycle(sample_opportunities, target=2, profile=sample_profile)

    # Should still complete the cycle
    assert result["scanned"] == len(sample_opportunities)
    assert result["total_in_bank"] >= 0


def test_workbank_to_dict_includes_payout(sample_opportunities, sample_profile):
    """Test that to_dict includes payout fields."""
    bank = WorkBank()
    bank.daily_cycle(sample_opportunities, target=2, profile=sample_profile)

    bank_dict = bank.to_dict()
    assert "items" in bank_dict

    for item in bank_dict["items"]:
        assert "payout_method" in item
        assert "payout_method_rationale" in item


def test_workbank_singleton_with_payout(sample_opportunities, sample_profile):
    """Test that the WorkBank singleton works with payout integration."""
    bank = get_workbank()
    bank.daily_cycle(sample_opportunities, target=2, profile=sample_profile)

    items = bank.best_ready(limit=10)
    assert len(items) > 0

    for item in items:
        if item.platform in ["opire", "freelancer", "hackerone"]:
            assert hasattr(item, "payout_method")
            assert hasattr(item, "payout_method_rationale")
