"""L1: modality (remoto/híbrido/presencial) + zone/commute + EV commute cost."""

from __future__ import annotations

from cores.direct_work_engine.models import (
    Modality,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    UserProfile,
    WorkPlatform,
)


def _opp(**overrides) -> Opportunity:
    base = {
        "id": "m-1",
        "title": "t",
        "platform": WorkPlatform.ALGORA,
        "category": OpportunityCategory.BACKEND,
        "payment": 500.0,
        "currency": "USD",
        "payment_method": PaymentMethod.PAYPAL,
        "remote": True,
        "estimated_time_hours": 10.0,
    }
    base.update(overrides)
    return Opportunity(**base)


def _profile(**overrides) -> UserProfile:
    base = {"name": "Test", "country": "Argentina", "skills": {"python"}, "projects": []}
    base.update(overrides)
    return UserProfile(**base)


class TestModalityDefaults:
    def test_legacy_default_is_remoto(self):
        assert _opp().modality == Modality.REMOTO
        assert _opp().zone == ""
        assert _opp().commute_minutes is None
        assert _opp().vpn_required is False

    def test_profile_defaults_silent(self):
        p = _profile()
        assert p.preferred_modality is None
        assert p.zone == ""
        assert p.max_commute_minutes is None


class TestModalityFit:
    def test_explicit_match_scores_full(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        rec = IntelligentRecommender()
        opp = _opp(modality=Modality.PRESENCIAL, zone="Zona Sur")
        prof = _profile(remote_only=False, preferred_modality=Modality.PRESENCIAL, zone="Zona Sur")
        assert rec._modality_fit(opp, prof) == 1.0

    def test_no_preference_is_neutral(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        rec = IntelligentRecommender()
        assert rec._modality_fit(_opp(), _profile()) == 0.75

    def test_zone_mismatch_penalized(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        rec = IntelligentRecommender()
        opp = _make_presencial(zone="CABA")
        prof = _profile(remote_only=False, zone="Zona Sur")
        assert rec._modality_fit(opp, prof) <= 0.3

    def test_commute_over_max_penalized(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        rec = IntelligentRecommender()
        opp = _make_presencial(zone="Zona Sur", commute_minutes=120.0)
        prof = _profile(remote_only=False, zone="Zona Sur", max_commute_minutes=60.0)
        assert rec._modality_fit(opp, prof) <= 0.2


def _make_presencial(**overrides):
    base = {"modality": Modality.PRESENCIAL, "remote": False}
    base.update(overrides)
    return _opp(**base)


class TestCommuteCost:
    def test_presencial_ev_subtracts_roundtrip(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender
        from cores.direct_work_engine.models import RankedOpportunity

        rec = IntelligentRecommender()
        opp = _make_presencial(commute_minutes=60.0)  # 2h round-trip @ $50/h implied = -$100
        ranked = RankedOpportunity(opportunity=opp)
        ranked.acceptance_probability = 1.0
        ev_plain = rec._calculate_expected_value(ranked)
        assert ev_plain < 500.0

    def test_unknown_hours_skips_subtraction(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender
        from cores.direct_work_engine.models import RankedOpportunity

        rec = IntelligentRecommender()
        opp = _make_presencial(commute_minutes=60.0, estimated_time_hours=0.0)
        ranked = RankedOpportunity(opportunity=opp)
        ranked.acceptance_probability = 1.0
        before = rec._calculate_expected_value(ranked)
        opp2 = _make_presencial(commute_minutes=None, estimated_time_hours=0.0)
        ranked2 = RankedOpportunity(opportunity=opp2)
        ranked2.acceptance_probability = 1.0
        assert rec._calculate_expected_value(ranked2) == before

    def test_remote_untouched(self):
        from cores.direct_work_engine.recommendation import IntelligentRecommender
        from cores.direct_work_engine.models import RankedOpportunity

        rec = IntelligentRecommender()
        opp = _opp(commute_minutes=60.0)
        ranked = RankedOpportunity(opportunity=opp)
        ranked.acceptance_probability = 1.0
        opp2 = _opp(commute_minutes=None)
        ranked2 = RankedOpportunity(opportunity=opp2)
        ranked2.acceptance_probability = 1.0
        assert rec._calculate_expected_value(ranked) == rec._calculate_expected_value(ranked2)
