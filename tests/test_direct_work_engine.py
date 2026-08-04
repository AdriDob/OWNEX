"""Tests for the Direct Work Engine (zero-barrier spectrum + game dev + recommendation).

Covers the completed design: async UniversalDiscovery adapters, ZeroBarrierScorer
(continuous 0-100), IntelligentRecommender (RankedOpportunity), and the
DirectWorkEngine orchestrator. Async APIs are driven with asyncio.run().
"""

from __future__ import annotations

import asyncio

import pytest

from cores.direct_work_engine.discovery import (
    BaseDiscoveryAdapter,
    DiscoverySource,
    UniversalDiscovery,
)
from cores.direct_work_engine.engine import DirectWorkEngine
from cores.direct_work_engine.models import (
    BarrierLevel,
    ExperienceLevel,
    GameDevSpecialization,
    Opportunity,
    OpportunityCategory,
    PaymentMethod,
    RankedOpportunity,
    UserProfile,
    WorkPlatform,
)
from cores.direct_work_engine.profile_builder import IntelligentProfileBuilder
from cores.direct_work_engine.recommendation import IntelligentRecommender, RecommenderConfig
from cores.direct_work_engine.scoring import ZeroBarrierScorer


def make_profile(**overrides) -> UserProfile:
    defaults = {
        "name": "Adriel",
        "country": "Argentina",
        "languages": {"es", "en"},
        "skills": {"python", "go", "unity"},
        "projects": ["Personal portfolio web app", "Open-source HTTP probe tool"],
    }
    defaults.update(overrides)
    return UserProfile(**defaults)


def make_opportunity(**overrides) -> Opportunity:
    defaults = {
        "id": "op-1",
        "title": "Fix a bug in an open-source game backend",
        "platform": WorkPlatform.ALGORA,
        "category": OpportunityCategory.GAME_DEVELOPMENT,
        "specialization": GameDevSpecialization.GAME_BACKEND,
        "remote": True,
        "payment": 500.0,
        "currency": "USD",
        "payment_method": PaymentMethod.PAYPAL,
        "payment_proven": True,
        "accepts_beginner": True,
        "accepts_ai_tools": True,
        "asynchronous": True,
        "time_to_payout_days": 5,
        "stability": 0.8,
    }
    defaults.update(overrides)
    return Opportunity(**defaults)


class FakeDiscoveryAdapter(BaseDiscoveryAdapter):
    """Deterministic async adapter used to exercise the pipeline."""

    name = "fake"

    def __init__(self, source: DiscoverySource, opportunities: list[Opportunity] | None = None):
        super().__init__(source)
        self._opportunities = opportunities or []

    async def fetch_opportunities(self) -> list[Opportunity]:
        return list(self._opportunities)

    async def validate_connection(self) -> bool:
        return True


def fake_adapter(opportunities: list[Opportunity] | None = None) -> FakeDiscoveryAdapter:
    source = DiscoverySource(
        name="fake",
        platform=WorkPlatform.ALGORA,
        categories=[OpportunityCategory.GAME_DEVELOPMENT, OpportunityCategory.DEV_BOUNTY],
    )
    return FakeDiscoveryAdapter(source, opportunities)


class TestGameDevelopmentProgrammingOnly:
    def test_game_development_requires_specialization(self) -> None:
        with pytest.raises(ValueError):
            Opportunity(
                id="op-gd",
                title="Game dev without specialization",
                platform=WorkPlatform.FREELANCER,
                category=OpportunityCategory.GAME_DEVELOPMENT,
            )

    def test_rejects_artistic_specialization(self) -> None:
        with pytest.raises(ValueError):
            Opportunity(
                id="op-art",
                title="Concept artist (excluded)",
                platform=WorkPlatform.FREELANCER,
                category=OpportunityCategory.GAME_DEVELOPMENT,
                specialization="concept_art",  # type: ignore[arg-type]
            )

    def test_accepts_every_programming_specialization(self) -> None:
        for spec in GameDevSpecialization:
            op = make_opportunity(id=f"op-{spec.value}", title=f"Game dev {spec.value}", specialization=spec)
            assert op.specialization == spec

    def test_non_game_categories_do_not_require_specialization(self) -> None:
        op = Opportunity(
            id="op-web",
            title="Frontend task",
            platform=WorkPlatform.UPWORK,
            category=OpportunityCategory.FRONTEND,
        )
        assert op.category == OpportunityCategory.FRONTEND


class TestZeroBarrierScorer:
    def test_best_case_scores_very_low_barrier(self) -> None:
        score = ZeroBarrierScorer().score(make_opportunity())
        assert score.total >= 80
        assert score.barrier_level == BarrierLevel.VERY_LOW

    def test_gated_opportunity_scores_lower(self) -> None:
        op = make_opportunity(
            experience_required=ExperienceLevel.SENIOR,
            portfolio_required=True,
            interview_required=True,
            technical_test_required=True,
            registration_required=True,
            remote=False,
            time_to_payout_days=90,
        )
        score = ZeroBarrierScorer().score(op)
        assert score.total < 60
        assert score.barrier_level == BarrierLevel.MEDIUM

    def test_barrier_is_a_spectrum_not_a_boolean(self) -> None:
        scorer = ZeroBarrierScorer()
        easy = make_opportunity()
        mid = make_opportunity(id="op-mid", interview_required=True)
        hard = make_opportunity(
            id="op-hard",
            experience_required=ExperienceLevel.SENIOR,
            portfolio_required=True,
            interview_required=True,
            technical_test_required=True,
            registration_required=True,
            remote=False,
            time_to_payout_days=90,
        )
        easy_s, mid_s, hard_s = scorer.score(easy), scorer.score(mid), scorer.score(hard)
        assert easy_s.total > mid_s.total > hard_s.total

    def test_enablers_and_blockers_populated(self) -> None:
        easy = ZeroBarrierScorer().score(make_opportunity())
        assert easy.enablers
        assert "No interview required" in easy.enablers
        hard = ZeroBarrierScorer().score(
            make_opportunity(id="op-hard", experience_required=ExperienceLevel.SENIOR, portfolio_required=True)
        )
        assert any("experience" in b.lower() for b in hard.blockers)
        assert any("portfolio" in b.lower() for b in hard.blockers)

    def test_fast_payment_scores_higher_than_slow(self) -> None:
        scorer = ZeroBarrierScorer()
        fast = make_opportunity(time_to_payout_days=3)
        slow = make_opportunity(id="op-slow", time_to_payout_days=90)
        assert scorer.score(fast).total > scorer.score(slow).total

    def test_international_payment_detected_from_method(self) -> None:
        op = make_opportunity(payment_method=PaymentMethod.WISE)
        assert op.international_payment is True
        op2 = make_opportunity(id="op-gift", payment_method=PaymentMethod.GIFT_CARD)
        assert op2.international_payment is False

    def test_score_opportunities_sorts_descending(self) -> None:
        scorer = ZeroBarrierScorer()
        easy = make_opportunity(id="op-easy")
        hard = make_opportunity(
            id="op-hard",
            experience_required=ExperienceLevel.SENIOR,
            interview_required=True,
            portfolio_required=True,
        )
        scored = scorer.score_opportunities([hard, easy])
        assert scored[0].id == "op-easy"
        assert scored[1].id == "op-hard"

    def test_weights_are_normalized_to_sum_one(self) -> None:
        from cores.direct_work_engine.scoring import ScorerWeights

        scorer = ZeroBarrierScorer(weights=ScorerWeights(no_experience_required=0.9))
        total = sum(getattr(scorer.weights, f.name) for f in scorer.weights.__dataclass_fields__.values())
        assert abs(total - 1.0) < 1e-9


class TestIntelligentRecommender:
    def test_returns_ranked_opportunities_ordered_by_overall(self) -> None:
        opportunities = [
            make_opportunity(id="op-a", title="High value low barrier", payment=1000.0),
            make_opportunity(id="op-b", title="Medium", payment=200.0, category=OpportunityCategory.DEV_BOUNTY),
            make_opportunity(id="op-c", title="Low", payment=50.0, category=OpportunityCategory.DATA_ANNOTATION),
        ]
        ranked = IntelligentRecommender().recommend(opportunities, make_profile(), limit=3)
        assert all(isinstance(r, RankedOpportunity) for r in ranked)
        assert len(ranked) == 3
        assert ranked[0].opportunity.id == "op-a"
        scores = [r.overall_recommendation_score for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_rank_assigned_and_fields_populated(self) -> None:
        ranked = IntelligentRecommender().recommend([make_opportunity()], make_profile(), limit=1)
        assert len(ranked) == 1
        top = ranked[0]
        assert top.rank == 1
        assert top.expected_value > 0
        assert top.acceptance_probability > 0
        assert top.zero_barrier_score is not None
        assert top.strategy
        assert top.recommendation_reasoning

    def test_filters_below_min_zero_barrier_threshold(self) -> None:
        gated = make_opportunity(
            id="op-gated",
            experience_required=ExperienceLevel.SENIOR,
            portfolio_required=True,
            interview_required=True,
            technical_test_required=True,
            registration_required=True,
            remote=False,
            payment_method=PaymentMethod.GIFT_CARD,
            payment_proven=False,
            time_to_payout_days=90,
            accepts_beginner=False,
            accepts_freelancers=False,
            accepts_individuals=False,
            accepts_ai_tools=False,
            asynchronous=False,
        )
        config = RecommenderConfig(min_zero_barrier_score=50.0)
        ranked = IntelligentRecommender(config=config).recommend([gated], make_profile(), limit=10)
        assert ranked == []

    def test_config_weights_must_sum_to_one(self) -> None:
        bad = RecommenderConfig(weight_zero_barrier=0.9)
        assert bad.validate() is False
        with pytest.raises(ValueError):
            IntelligentRecommender(config=bad)

    def test_lead_prefers_low_barrier_when_income_comparable(self) -> None:
        famous = make_opportunity(
            id="op-famous",
            title="Famous platform task",
            payment=2000.0,
            experience_required=ExperienceLevel.SENIOR,
            interview_required=True,
        )
        hidden = make_opportunity(
            id="op-hidden",
            title="Hidden gem",
            payment=1500.0,
            experience_required=ExperienceLevel.NONE,
        )
        ranked = IntelligentRecommender().recommend([famous, hidden], make_profile(), limit=1)
        assert ranked[0].opportunity.id == "op-hidden"

    def test_game_dev_strategy_mentions_programming_not_art(self) -> None:
        ranked = IntelligentRecommender().recommend([make_opportunity()], make_profile(), limit=1)
        assert ranked[0].strategy is not None
        assert "game programming" in ranked[0].strategy.lower()
        assert "concept" not in ranked[0].strategy.lower()


class TestUniversalDiscovery:
    def test_register_and_discover(self) -> None:
        op = make_opportunity()
        discovery = UniversalDiscovery()
        discovery.register_adapter(fake_adapter([op]))
        assert discovery.get_registered_platforms() == [WorkPlatform.ALGORA]
        result = asyncio.run(discovery.discover_all())
        assert result == [op]

    def test_discover_filters_by_category(self) -> None:
        op = make_opportunity()
        discovery = UniversalDiscovery()
        discovery.register_adapter(fake_adapter([op]))
        result = asyncio.run(discovery.discover_all(categories=[OpportunityCategory.DEV_BOUNTY]))
        assert result == []

    def test_one_failing_adapter_does_not_kill_others(self) -> None:
        op = make_opportunity()

        class Broken(FakeDiscoveryAdapter):
            async def fetch_opportunities(self) -> list[Opportunity]:
                raise RuntimeError("boom")

        source = DiscoverySource(
            name="broken",
            platform=WorkPlatform.OPIRE,
            categories=[OpportunityCategory.DEV_BOUNTY],
        )
        discovery = UniversalDiscovery()
        discovery.register_adapter(Broken(source))
        discovery.register_adapter(fake_adapter([op]))
        result = asyncio.run(discovery.discover_all())
        assert result == [op]
        assert discovery.sources["broken"].consecutive_errors == 1

    def test_disabled_source_is_skipped(self) -> None:
        adapter = fake_adapter([make_opportunity()])
        adapter.source.enabled = False
        discovery = UniversalDiscovery()
        discovery.register_adapter(adapter)
        assert asyncio.run(discovery.discover_all()) == []


class TestProfileBuilder:
    def test_build_never_invents_without_projects(self) -> None:
        assets = IntelligentProfileBuilder().build(make_profile(projects=[]))
        assert assets.portfolio_sections == []
        assert assets.github_readme != ""
        assert "technology professional" in assets.bio

    def test_build_uses_real_facts(self) -> None:
        assets = IntelligentProfileBuilder().build(make_profile())
        assert "Argentina" in assets.bio
        assert any("Open-source HTTP probe tool" in p["title"] for p in assets.portfolio_sections)


class TestDirectWorkEngine:
    def test_full_cycle_end_to_end(self) -> None:
        engine = DirectWorkEngine()
        engine.register_adapter(fake_adapter([make_opportunity()]))
        opportunities, ranked = asyncio.run(engine.run_cycle(make_profile(), limit=3))
        assert len(opportunities) == 1
        assert len(ranked) == 1
        assert ranked[0].opportunity.id == "op-1"
        assert engine.stats.cycles_completed == 1

    def test_run_cycle_without_adapters_returns_empty(self) -> None:
        engine = DirectWorkEngine()
        opportunities, ranked = asyncio.run(engine.run_cycle(make_profile()))
        assert opportunities == []
        assert ranked == []

    def test_get_status_reports_stats_and_sources(self) -> None:
        engine = DirectWorkEngine()
        engine.register_adapter(fake_adapter([make_opportunity()]))
        asyncio.run(engine.run_cycle(make_profile()))
        status = engine.get_status()
        assert status["stats"]["cycles_completed"] == 1
        assert status["platforms"] == ["algora"]
        assert "fake" in status["sources"]

    def test_build_profile_assets_returns_assets(self) -> None:
        engine = DirectWorkEngine()
        assets = engine.build_profile_assets(make_profile())
        assert assets.bio
        assert assets.skills


class TestLearningFeedback:
    def test_apply_learning_computes_rates(self) -> None:
        from cores.direct_work_engine.feedback import LearningRecord, apply_learning

        profile = make_profile()
        records = [
            LearningRecord(platform="algora", category=OpportunityCategory.DEV_BOUNTY, accepted=True, amount=500.0),
            LearningRecord(platform="algora", category=OpportunityCategory.DEV_BOUNTY, accepted=False, amount=0.0),
            LearningRecord(platform="outlier", category=OpportunityCategory.AI_EVALUATION, accepted=True, amount=80.0),
        ]
        apply_learning(profile, records)
        assert profile.applications_submitted == 3
        assert profile.applications_accepted == 2
        assert profile.total_earnings == 580.0
        assert profile.platform_success_rates == {"algora": 0.5, "outlier": 1.0}
        assert profile.category_success_rates["dev_bounty"] == 0.5

    def test_empty_history_never_invents(self) -> None:
        from cores.direct_work_engine.feedback import apply_learning

        profile = make_profile()
        apply_learning(profile, [])
        assert profile.applications_submitted == 0
        assert profile.applications_accepted == 0
        assert profile.platform_success_rates == {}

    def test_build_history_maps_terminal_statuses(self) -> None:
        from datetime import UTC, datetime, timedelta
        from types import SimpleNamespace

        from cores.direct_work_engine.feedback import build_history_from_revenue_tracker

        now = datetime.now(UTC)

        def opp(
            status: str, platform: str = "bug_bounty", amount: float = 100.0, provider: dict | None = None
        ) -> SimpleNamespace:
            return SimpleNamespace(
                status=status,
                platform=platform,
                amount=amount,
                provider_info=provider or {},
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(days=2),
            )

        tracker = SimpleNamespace(
            opportunities={
                "a": opp("accepted", amount=250.0, provider={"platform": "hackerone"}),
                "b": opp("paid", amount=80.0, platform="data_annotation"),
                "c": opp("failed"),
                "d": opp("cancelled"),
                "e": opp("pending"),
                "f": opp("reviewing"),
            }
        )
        records = build_history_from_revenue_tracker(tracker)
        assert len(records) == 4
        accepted = [r for r in records if r.accepted]
        assert len(accepted) == 2
        assert records[0].platform == "bug_bounty:hackerone"
        assert records[0].category == OpportunityCategory.BUG_BOUNTY
        assert records[1].platform == "data_annotation"
        assert records[1].category == OpportunityCategory.DATA_ANNOTATION
        assert all(r.time_to_payout_days == 8.0 for r in records)

    def test_engine_learn_wires_feedback(self) -> None:
        from cores.direct_work_engine.feedback import LearningRecord

        engine = DirectWorkEngine()
        profile = engine.learn(make_profile(), [LearningRecord(platform="opire", accepted=True, amount=300.0)])
        assert profile.total_earnings == 300.0
        assert profile.platform_success_rates == {"opire": 1.0}


class TestOpportunityModel:
    def test_outcome_based_classification(self) -> None:
        from cores.direct_work_engine.models import EmploymentType
        from cores.direct_work_engine.recommendation import is_outcome_based, opportunity_model

        assert is_outcome_based(EmploymentType.BOUNTY)
        assert is_outcome_based(EmploymentType.MICROTASK)
        assert is_outcome_based(EmploymentType.PRIZE)
        assert is_outcome_based(EmploymentType.OPEN_CALL)
        assert not is_outcome_based(EmploymentType.FULL_TIME)
        assert not is_outcome_based(EmploymentType.FREELANCE)
        assert opportunity_model(EmploymentType.FULL_TIME) == "classic_employment"
        assert opportunity_model(EmploymentType.BOUNTY) == "outcome_bounty"

    def test_reasoning_exposes_model(self) -> None:
        from cores.direct_work_engine.models import EmploymentType

        op = make_opportunity(id="op-bounty", employment_type=EmploymentType.BOUNTY)
        ranked = IntelligentRecommender().recommend([op], make_profile(), limit=1)
        assert any("Model: outcome_bounty" in r for r in ranked[0].recommendation_reasoning)

    def test_strategy_flags_outcome_based(self) -> None:
        from cores.direct_work_engine.models import EmploymentType

        op = make_opportunity(id="op-task", employment_type=EmploymentType.MICROTASK)
        ranked = IntelligentRecommender().recommend([op], make_profile(), limit=1)
        assert ranked[0].strategy is not None
        assert "Outcome-based" in ranked[0].strategy
