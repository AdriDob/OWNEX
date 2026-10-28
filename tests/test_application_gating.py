"""L4: application gating opt-in — interview / CV-portfolio steps need user opt-in."""

from __future__ import annotations

from typing import Any

from cores.direct_work_engine.models import Opportunity, OpportunityCategory, UserProfile, WorkPlatform
from cores.direct_work_engine.recommendation import IntelligentRecommender


def _opp(**overrides: Any) -> Opportunity:
    base = {
        "id": "op-1",
        "title": "Gated job",
        "platform": WorkPlatform.HACKERONE,
        "category": OpportunityCategory.BUG_BOUNTY,
        "payment": 500.0,
    }
    base.update(overrides)
    return Opportunity(**base)


def _profile(**overrides: Any) -> UserProfile:
    base = {"name": "Adriel", "country": "Argentina"}
    base.update(overrides)
    return UserProfile(**base)


def _filter(opps, profile):
    return IntelligentRecommender()._apply_profile_filter(opps, profile)


class TestOptInDefaults:
    def test_defaults_preserve_legacy_behavior(self):
        """Defaults opt-in (True): gated opps pass the profile filter."""
        opps = [_opp(interview_required=True), _opp(id="op-2", portfolio_required=True)]
        assert _filter(opps, _profile()) == opps

    def test_opt_out_interview_filters(self):
        opps = [_opp(interview_required=True), _opp(id="op-2")]
        kept = _filter(opps, _profile(allow_interview=False))
        assert [o.id for o in kept] == ["op-2"]

    def test_opt_out_cv_filters_portfolio(self):
        opps = [_opp(portfolio_required=True), _opp(id="op-2")]
        kept = _filter(opps, _profile(allow_cv_portfolio=False))
        assert [o.id for o in kept] == ["op-2"]

    def test_opt_out_both_filters_both(self):
        opps = [
            _opp(id="a", interview_required=True),
            _opp(id="b", portfolio_required=True),
            _opp(id="c"),
        ]
        kept = _filter(opps, _profile(allow_interview=False, allow_cv_portfolio=False))
        assert [o.id for o in kept] == ["c"]

    def test_technical_test_is_not_gated(self):
        """Capability assessments are not hiring gates (Zero Experience rule)."""
        opps = [_opp(technical_test_required=True)]
        assert _filter(opps, _profile(allow_interview=False, allow_cv_portfolio=False)) == opps

    def test_recommend_end_to_end_respects_opt_out(self):
        opps = [_opp(id="a", interview_required=True, payment=5000.0), _opp(id="b", payment=100.0)]
        ranked = IntelligentRecommender().recommend(opps, _profile(allow_interview=False), limit=5)
        assert all(r.opportunity.id != "a" for r in ranked)


class TestEligibilityContract:
    def test_defaults_unknown_no_assumptions(self):
        from cores.direct_work_engine.models import AIPolicy, AutomationLevel

        opp = _opp()
        assert opp.ai_policy == AIPolicy.UNKNOWN
        assert opp.automation_level == AutomationLevel.UNKNOWN

    def test_country_verified_on_match(self):
        from cores.direct_work_engine.models import country_access_for

        assert country_access_for(_opp(allowed_countries=("Argentina", "Brasil")), "argentina") == "VERIFIED"

    def test_country_unknown_without_data(self):
        from cores.direct_work_engine.models import country_access_for

        assert country_access_for(_opp(), "argentina") == "UNKNOWN"
        assert country_access_for(_opp(allowed_countries=("USA",)), "argentina") == "UNKNOWN"

    def test_country_conditional_on_vpn(self):
        from cores.direct_work_engine.models import country_access_for

        assert country_access_for(_opp(vpn_required=True), "argentina") == "CONDITIONAL"

    def test_payment_needs_configured_rail(self):
        from cores.direct_work_engine.models import payment_access_for

        assert payment_access_for(_opp()) == "UNKNOWN"
        assert payment_access_for(_opp(), has_configured_rail=True) == "VERIFIED"

    def test_unknown_means_no_auto_action(self):
        from cores.direct_work_engine.models import AutomationLevel, can_auto_act

        assert can_auto_act(_opp()) is False
        assert can_auto_act(_opp(automation_level=AutomationLevel.ALLOWED)) is True
        assert can_auto_act(_opp(automation_level=AutomationLevel.RESTRICTED)) is False

    def test_ai_assist_only_when_explicitly_allowed(self):
        from cores.direct_work_engine.models import AIPolicy, ai_assist_allowed

        assert ai_assist_allowed(_opp()) is False
        assert ai_assist_allowed(_opp(ai_policy=AIPolicy.LIMITED)) is False
        assert ai_assist_allowed(_opp(ai_policy=AIPolicy.PROHIBITED)) is False
        assert ai_assist_allowed(_opp(ai_policy=AIPolicy.ALLOWED)) is True

    def test_exports_available(self):
        import cores.direct_work_engine as dwe

        for name in (
            "AIPolicy",
            "AutomationLevel",
            "country_access_for",
            "payment_access_for",
            "can_auto_act",
            "ai_assist_allowed",
        ):
            assert name in dwe.__all__
