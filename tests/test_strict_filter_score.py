"""L1: StrictFilter numeric score — pass-strength 0-100 alongside hard-reject."""

from __future__ import annotations

from cores.direct_work_engine.filters import FilterScore, StrictFilter
from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform


def _opp(**overrides) -> Opportunity:
    base = {
        "id": "op-1",
        "title": "Test bounty",
        "platform": WorkPlatform.HACKERONE,
        "category": OpportunityCategory.BUG_BOUNTY,
        "payment": 500.0,
    }
    base.update(overrides)
    return Opportunity(**base)


class TestFilterScore:
    def test_clean_scores_100_and_passes(self):
        fs = StrictFilter().score(_opp())
        assert isinstance(fs, FilterScore)
        assert fs.score == 100.0
        assert fs.passed is True
        assert fs.reasons == []

    def test_hard_reject_scores_zero(self):
        fs = StrictFilter().score(_opp(payment=0.0))
        assert fs.score == 0.0
        assert fs.passed is False
        assert fs.reasons != []

    def test_each_hard_rule_zeroes(self):
        cases = [
            {"payment": -5.0},
            {"payment": 0.0, "estimated_time_hours": 5.0},
            {"remote": False},
            {"interview_required": True, "portfolio_required": True, "registration_required": True},
        ]
        for kwargs in cases:
            fs = StrictFilter().score(_opp(**kwargs))
            assert fs.score == 0.0 and fs.passed is False, kwargs

    def test_interview_deducts_15(self):
        fs = StrictFilter().score(_opp(interview_required=True))
        assert fs.passed is True
        assert fs.score == 85.0

    def test_portfolio_and_test_stack(self):
        fs = StrictFilter().score(_opp(portfolio_required=True, technical_test_required=True))
        assert fs.score == 75.0

    def test_small_payment_deductions(self):
        assert StrictFilter().score(_opp(payment=5.0)).score == 90.0
        assert StrictFilter().score(_opp(payment=25.0)).score == 95.0

    def test_slow_payout_deductions(self):
        assert StrictFilter().score(_opp(time_to_payout_days=45)).score == 90.0
        assert StrictFilter().score(_opp(time_to_payout_days=90)).score == 80.0

    def test_consistency_rejected_implies_zero(self):
        f = StrictFilter()
        opp = _opp(payment=0.0)
        assert f.is_rejected(opp) is True
        assert f.score(opp).score == 0.0

    def test_to_dict_shape(self):
        d = StrictFilter().score(_opp()).to_dict()
        assert d == {"score": 100.0, "passed": True, "reasons": []}
