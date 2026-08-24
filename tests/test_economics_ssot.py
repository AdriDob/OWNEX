"""FASE 3 remediation — single ExpectedValue contract (economics SSOT).

Two parallel EV formulas existed:
- IntelligentRecommender._calculate_expected_value:
    payment x acceptance x PAYMENT_RELIABILITY[method]
- EVScorer.calculate (autonomous_discovery):
    payment x success_prob, with success_prob derived from an invented
    per-category hard table presented as "historical data".

Contract after remediation:
1. ONE money-math implementation (cores.direct_work_engine.economics).
   Both engines must produce byte-identical EV for identical inputs.
2. Task availability is never silently assumed: UNKNOWN excludes the
   factor and surfaces a warning; KNOWN multiplies explicitly.
3. Cold-start priors are allowed only when labeled as such in the
   output (never presented as measured history).
"""

from __future__ import annotations

import pytest


class TestEconomicsCoreMath:
    def test_known_availability_multiplies(self) -> None:
        from cores.direct_work_engine.economics import TaskAvailability, compute_expected_value

        res = compute_expected_value(
            payment=1000.0,
            acceptance_probability=0.5,
            task_availability=TaskAvailability.of(0.8),
            payment_reliability=0.9,
        )
        assert res.ev_usd == pytest.approx(1000 * 0.5 * 0.9 * 0.8)
        assert res.availability_state == "known"
        assert res.warnings == ()

    def test_unknown_availability_excluded_and_flagged(self) -> None:
        from cores.direct_work_engine.economics import compute_expected_value

        res = compute_expected_value(payment=1000.0, acceptance_probability=0.5)
        # Partial EV without the availability factor...
        assert res.ev_usd == pytest.approx(500.0)
        assert res.availability_state == "unknown"
        # ...but NEVER silent about it.
        assert any("task_availability" in w.lower() for w in res.warnings)

    def test_acceptance_clamped(self) -> None:
        from cores.direct_work_engine.economics import compute_expected_value

        res = compute_expected_value(payment=100.0, acceptance_probability=1.7)
        assert res.ev_usd == pytest.approx(100.0)


class TestRecommenderDelegation:
    def test_recommender_ev_matches_economics(self) -> None:
        """Same inputs through the recommender and the core math agree."""
        from cores.direct_work_engine import economics
        from cores.direct_work_engine.models import (
            PAYMENT_RELIABILITY,
            Opportunity,
            OpportunityCategory,
            PaymentMethod,
            WorkPlatform,
        )
        from cores.direct_work_engine.recommendation import IntelligentRecommender

        opp = Opportunity(
            id="x1",
            platform=WorkPlatform.OPIRE,
            title="T",
            category=OpportunityCategory.DEV_BOUNTY,
            payment=750.0,
            payment_method=PaymentMethod.CRYPTO,
            estimated_time_hours=4.0,
        )
        ranked = IntelligentRecommender()._score_opportunities([opp])[0]
        rec_ev = ranked.expected_value

        expected = economics.compute_expected_value(
            payment=opp.payment,
            acceptance_probability=ranked.acceptance_probability,
            task_availability=economics.TaskAvailability.unknown(),
            payment_reliability=PAYMENT_RELIABILITY.get(opp.payment_method, 0.5),
        ).ev_usd
        assert rec_ev == pytest.approx(expected)


class TestEVScorerDelegation:
    def _sample_opp(self):
        from cores.direct_work_engine.models import (
            Opportunity,
            OpportunityCategory,
            WorkPlatform,
        )

        return Opportunity(
            id="a1",
            platform=WorkPlatform.OPIRE,
            title="Fix bug",
            category=OpportunityCategory.DEV_BOUNTY,
            payment=250.0,
            remote=True,
            accepts_beginner=True,
            asynchronous=True,
            estimated_time_hours=3.0,
        )

    def test_evscorer_delegates_to_economics(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """total_ev must come from economics math fed with EVScorer's own inputs."""
        import cores.direct_work_engine.economics as econ
        from cores.direct_work_engine.autonomous_discovery import EVScorer

        calls: list[dict] = []
        returned: list[float] = []
        original = econ.compute_expected_value

        def _spy(**kwargs):
            calls.append(kwargs)
            result = original(**kwargs)
            returned.append(result.ev_usd)
            return result

        monkeypatch.setattr(econ, "compute_expected_value", _spy)

        opp = self._sample_opp()
        score = EVScorer().score(opp)

        assert len(calls) == 1, "EVScorer must route EV through the SSOT exactly once"
        assert calls[0]["payment"] == pytest.approx(opp.payment)
        # success_probability is stored pre-rounded; allow 5e-4 slack.
        assert calls[0]["acceptance_probability"] == pytest.approx(score.success_probability, abs=5e-4)
        assert calls[0]["payment_reliability"] == 1.0
        # The value flowing into the output IS the SSOT's output.
        assert score.total_ev_usd == pytest.approx(returned[0])

    def test_cold_start_priors_are_labeled(self) -> None:
        """Success probability derived from curated priors must say so."""
        from cores.direct_work_engine.autonomous_discovery import EVScorer

        score = EVScorer().score(self._sample_opp())
        joined = " ".join(score.reasoning).lower()
        assert "cold-start" in joined or "prior" in joined, (
            "invented rates must be surfaced as cold-start priors, not history"
        )
