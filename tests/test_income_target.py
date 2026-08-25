"""Tests for Income Target Engine."""

import pytest
from cores.direct_work_engine.income_target import (
    IncomeTargetEngine,
    TargetTier,
    TargetMode,
    IncomeTarget,
    TargetPlan,
    TargetProgress,
    workitem_to_opportunity,
)
from cores.direct_work_engine.workbank import WorkItem
from cores.direct_work_engine.profile_kit import UserProfile


class TestIncomeTargetEngine:
    def test_create_target_from_tier(self):
        engine = IncomeTargetEngine()
        target = engine.create_target(TargetTier.WEEKLY_500, TargetMode.FAST_CASH)
        assert target.tier == TargetTier.WEEKLY_500
        assert target.amount_usd == 500.0
        assert target.period == "weekly"
        assert target.mode == TargetMode.FAST_CASH

    def test_create_target_custom(self):
        engine = IncomeTargetEngine()
        target = engine.create_target(
            TargetTier.CUSTOM,
            TargetMode.BALANCED,
            custom_amount=1234.0,
            custom_period="monthly"
        )
        assert target.tier == TargetTier.CUSTOM
        assert target.amount_usd == 1234.0
        assert target.period == "monthly"
        assert target.mode == TargetMode.BALANCED

    def test_create_target_custom_requires_amount_period(self):
        engine = IncomeTargetEngine()
        with pytest.raises(ValueError):
            engine.create_target(TargetTier.CUSTOM, TargetMode.BALANCED)

    def test_build_plan_with_public_ready_items(self):
        engine = IncomeTargetEngine()
        target = engine.create_target(TargetTier.WEEKLY_500, TargetMode.FAST_CASH)
        
        from cores.direct_work_engine.profile_kit import ProfileKitEngine
        kit = ProfileKitEngine()
        profile = kit.get() or kit.default_profile()
        profile_obj = ProfileKitEngine.profile_from_dict(profile)

        plan = engine.build_plan(target, profile_obj)
        
        assert isinstance(plan, TargetPlan)
        assert plan.target == target
        assert plan.required_opportunities >= 0
        assert plan.required_hours_per_week >= 0
        assert 0.0 <= plan.probability_of_success <= 1.0

    def test_build_plan_no_feasible_opportunities(self):
        engine = IncomeTargetEngine()
        target = engine.create_target(TargetTier.MONTHLY_10000, TargetMode.MAX_EV)
        
        from cores.direct_work_engine.profile_kit import ProfileKitEngine
        kit = ProfileKitEngine()
        profile = kit.get() or kit.default_profile()
        profile_obj = ProfileKitEngine.profile_from_dict(profile)
        # The test expects a plan to be created
        plan = engine.build_plan(target, profile_obj)
        assert isinstance(plan, TargetPlan)

    def test_rank_by_mode_fast_cash(self):
        engine = IncomeTargetEngine()
        
        from cores.direct_work_engine.economic_engine import OpportunityEconomicProfile
        
        p1 = OpportunityEconomicProfile(opportunity_id="1", platform="test", cash_adjusted_value=100.0)
        p2 = OpportunityEconomicProfile(opportunity_id="2", platform="test", cash_adjusted_value=50.0)
        p3 = OpportunityEconomicProfile(opportunity_id="3", platform="test", cash_adjusted_value=200.0)
        
        ranked = engine._rank_by_mode([p1, p2, p3], TargetMode.FAST_CASH)
        assert ranked[0].opportunity_id == "3"
        assert ranked[1].opportunity_id == "1"
        assert ranked[2].opportunity_id == "2"

    def test_rank_by_mode_max_ev(self):
        engine = IncomeTargetEngine()
        
        from cores.direct_work_engine.economic_engine import OpportunityEconomicProfile
        
        p1 = OpportunityEconomicProfile(opportunity_id="1", platform="test", expected_net_value=100.0)
        p2 = OpportunityEconomicProfile(opportunity_id="2", platform="test", expected_net_value=50.0)
        p3 = OpportunityEconomicProfile(opportunity_id="3", platform="test", expected_net_value=200.0)
        
        ranked = engine._rank_by_mode([p1, p2, p3], TargetMode.MAX_EV)
        assert ranked[0].opportunity_id == "3"
        assert ranked[1].opportunity_id == "1"
        assert ranked[2].opportunity_id == "2"


class TestWorkItemToOpportunity:
    def test_converts_workitem_fields(self):
        from cores.direct_work_engine.workbank import WorkItem
        from cores.direct_work_engine.models import EmploymentType
        
        item = WorkItem(
            id="test-1",
            title="Test Bounty",
            platform="bugcrowd",
            category="bug_bounty",
            reward=5000.0,
            employment_type=EmploymentType.BOUNTY,
            barrier_score=90.0,
            status="ready_to_deliver",
            access_status="public",
        )
        
        opp = workitem_to_opportunity(item)
        
        assert opp.id == "test-1"
        assert opp.title == "Test Bounty"
        assert opp.platform == "bugcrowd"
        assert opp.category == "bug_bounty"
        assert opp.payment == 5000.0
        assert opp.currency == "USDC"
        assert opp.payment_method == "crypto"
        assert opp.international_payment is True
        assert opp.employment_type == "bounty"

    def test_converts_minimal_workitem(self):
        from cores.direct_work_engine.workbank import WorkItem
        from cores.direct_work_engine.models import EmploymentType
        
        item = WorkItem(
            id="minimal",
            title="Minimal",
            platform="opire",
            category="dev_bounty",
            reward=100.0,
            employment_type=EmploymentType.BOUNTY,
            barrier_score=80.0,
            status="preparing",
            access_status="public",
        )
        
        opp = workitem_to_opportunity(item)
        
        assert opp.id == "minimal"
        assert opp.platform == "opire"
        assert opp.category == "dev_bounty"
        assert opp.payment == 100.0


class TestTargetPlan:
    def test_target_plan_creation(self):
        from cores.direct_work_engine.income_target import TargetPlan, IncomeTarget, TargetTier, TargetMode
        
        target = IncomeTarget(tier=TargetTier.WEEKLY_500, amount_usd=500.0, period="weekly", mode="fast_cash")
        plan = TargetPlan(
            target=target,
            required_opportunities=5,
            required_hours_per_week=20.0,
            required_hours_per_day=4.0,
            recommended_sources=["bugcrowd", "hackerone"],
            weekly_plan=[{"day": "Mon", "action": "test"}],
            probability_of_success=0.7,
            risk_factors=["Single platform"],
        )
        
        assert plan.target == target
        assert plan.required_opportunities == 5


class TestTargetProgress:
    def test_target_progress_creation(self):
        from cores.direct_work_engine.income_target import TargetProgress, IncomeTarget, TargetTier, TargetMode
        
        target = IncomeTarget(tier=TargetTier.WEEKLY_500, amount_usd=500.0, period="weekly", mode="fast_cash")
        progress = TargetProgress(
            target=target,
            earned_this_period=250.0,
            pending_amount=100.0,
            projected_total=350.0,
            progress_pct=70.0,
            days_remaining=3,
            on_track=True,
            required_daily_rate=71.4,
            actual_daily_rate=83.3,
        )
        
        assert progress.target == target
        assert progress.earned_this_period == 250.0
        assert progress.progress_pct == 70.0


class TestIncomeTargetTiers:
    def test_tier_configs_exist(self):
        from cores.direct_work_engine.income_target import _TIER_CONFIGS, TargetTier
        
        assert TargetTier.WEEKLY_100.value in _TIER_CONFIGS
        assert TargetTier.WEEKLY_500.value in _TIER_CONFIGS
        assert TargetTier.WEEKLY_1000.value in _TIER_CONFIGS
        assert TargetTier.MONTHLY_1000.value in _TIER_CONFIGS
        assert TargetTier.MONTHLY_10000.value in _TIER_CONFIGS
        
        for config in _TIER_CONFIGS.values():
            assert "amount" in config
            assert "period" in config
            assert config["amount"] > 0
            assert config["period"] in ("weekly", "monthly")


class TestConvenienceFunctions:
    def test_create_income_target(self):
        from cores.direct_work_engine.income_target import create_income_target, TargetTier, TargetMode
        
        target = create_income_target("weekly_250", "balanced")
        assert target.amount_usd == 250.0
        assert target.period == "weekly"

    def test_build_target_plan(self):
        from cores.direct_work_engine.income_target import build_target_plan, IncomeTarget, TargetTier, TargetMode
        
        target = IncomeTarget(tier="weekly_100", amount_usd=100.0, period="weekly", mode="balanced")
        plan = build_target_plan(target)
        
        assert isinstance(plan, TargetPlan)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
