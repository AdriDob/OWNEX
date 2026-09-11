"""L3: mode="zero_first" + region filter on recommend()."""

from __future__ import annotations

from cores.direct_work_engine.models import (
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.recommendation import (
    ZERO_FIRST_RECOMMENDER_CONFIG,
    IntelligentRecommender,
    filter_by_region,
)


def _opp(**overrides) -> Opportunity:
    base = {
        "id": "z-1",
        "title": "t",
        "platform": WorkPlatform.ALGORA,
        "category": OpportunityCategory.BACKEND,
        "payment": 200.0,
        "currency": "USD",
        "payment_method": PaymentMethod.PAYPAL,
        "remote": True,
        "estimated_time_hours": 5.0,
    }
    base.update(overrides)
    return Opportunity(**base)


def _profile(**overrides) -> UserProfile:
    base = {"name": "Test", "country": "Argentina", "skills": {"python"}, "projects": []}
    base.update(overrides)
    return UserProfile(**base)


class TestZeroFirstConfig:
    def test_weights_sum_to_one(self):
        assert ZERO_FIRST_RECOMMENDER_CONFIG.validate() is True

    def test_no_acceptance_floor(self):
        assert ZERO_FIRST_RECOMMENDER_CONFIG.enforce_acceptance_floor is False
        assert ZERO_FIRST_RECOMMENDER_CONFIG.min_expected_value == 0.0

    def test_mode_selectable(self):
        rec = IntelligentRecommender()
        ranked = rec.recommend([_opp()], _profile(), limit=5, mode="zero_first")
        assert rec._current_mode == "zero_first"
        assert len(ranked) >= 0  # smoke: mode runs end-to-end


class TestRegionFilter:
    def test_global_passes(self):
        opps = [_opp(), _opp(id="z-2")]
        assert len(filter_by_region(opps, "Argentina")) == 2

    def test_allowed_country_match(self):
        opp = _opp(allowed_countries=("AR", "BR"))
        assert filter_by_region([opp], "Argentina") == [opp]
        assert filter_by_region([opp], "ar") == [opp]

    def test_blocked_country_filtered(self):
        opp = _opp(allowed_countries=("US",))
        assert filter_by_region([opp], "Argentina") == []

    def test_empty_region_no_filter(self):
        opp = _opp(allowed_countries=("US",))
        assert filter_by_region([opp], "") == [opp]
        assert filter_by_region([opp], None) == [opp]

    def test_recommend_uses_profile_country(self):
        rec = IntelligentRecommender()
        us_only = _opp(id="us", allowed_countries=("US",))
        ar_ok = _opp(id="ar", allowed_countries=("AR",))
        ranked = rec.recommend([us_only, ar_ok], _profile(), limit=5)
        assert [r.opportunity.id for r in ranked] == ["ar"]

    def test_explicit_region_overrides_profile(self):
        rec = IntelligentRecommender()
        us_only = _opp(id="us", allowed_countries=("US",))
        ranked = rec.recommend([us_only], _profile(), limit=5, region="US")
        assert [r.opportunity.id for r in ranked] == ["us"]


class TestBalancedUnchanged:
    def test_balanced_ignores_region_when_global(self):
        rec = IntelligentRecommender()
        ranked = rec.recommend([_opp()], _profile(), limit=5, mode="balanced")
        assert rec._current_mode == "balanced"
        assert len(ranked) == 1
