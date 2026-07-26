"""Tests for Target Intelligence — EV-based prioritization + attack plans."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestComputeTechAdjustment:
    def test_empty_tags_returns_one(self):
        from core.target_intelligence.prioritizer import compute_tech_adjustment

        assert compute_tech_adjustment("", {}) == 1.0
        assert compute_tech_adjustment("", {"xss": 1.5}) == 1.0

    def test_no_match_returns_one(self):
        from core.target_intelligence.prioritizer import compute_tech_adjustment

        assert compute_tech_adjustment("unknown_tech_xzy", {"xss": 1.5}) == 1.0

    def test_matching_tech_picks_highest_adjustment(self):
        from core.target_intelligence.prioritizer import compute_tech_adjustment

        result = compute_tech_adjustment("wordpress", {"xss": 1.5, "sqli": 2.0})
        assert result == 2.0

    def test_case_insensitive_matching(self):
        from core.target_intelligence.prioritizer import compute_tech_adjustment

        result = compute_tech_adjustment("REACT,GraphQL", {"xss": 1.5})
        assert result == 1.5

    def test_multiple_techs_picks_highest(self):
        from core.target_intelligence.prioritizer import compute_tech_adjustment

        result = compute_tech_adjustment("django,aws", {"ssrf": 1.8, "xss": 1.2, "sqli": 0.5})
        assert result == 1.8


@pytest.fixture
def mock_intel():
    intel = MagicMock()
    intel.id = 1
    intel.reward_score = 1000.0
    intel.reward_confidence = 0.7
    intel.quality_score = 80
    intel.attack_surface_score = 0.6
    intel.technology_tags = "django,postgres"
    intel.program_url = "https://hackerone.com/test"
    return intel


def make_target(id: int, name: str = "test"):
    target = MagicMock()
    target.id = id
    target.name = name
    return target


class TestAttackPlan:
    def test_basic_creation(self):
        from core.target_intelligence.prioritizer import AttackPlan

        plan = AttackPlan(strategies=["django"], estimated_hours=2.0)
        assert plan.strategies == ["django"]
        assert plan.estimated_hours == 2.0
        assert "discover" in plan.phases_to_run

    def test_to_dict(self):
        from core.target_intelligence.prioritizer import AttackPlan

        plan = AttackPlan(strategies=["graphql"], estimated_hours=1.0, phases_to_run=["recon", "validate"])
        d = plan.to_dict()
        assert d["strategies"] == ["graphql"]
        assert d["estimated_hours"] == 1.0
        assert d["phases_to_run"] == ["recon", "validate"]


class TestPriorityResult:
    def test_priority_score_clamps_low(self):
        from core.priority.ev_engine import EVResult
        from core.target_intelligence.prioritizer import PriorityResult

        ev = EVResult(
            expected_value=0.0,
            estimated_reward=0,
            acceptance_probability=0,
            speed_multiplier=0,
            confidence=0,
            reasoning="",
            breakdown={},
        )
        pr = PriorityResult(
            target_id=1,
            target_name="t",
            expected_value=0.0,
            estimated_reward=0,
            acceptance_probability=0,
            speed_multiplier=0,
            confidence=0,
            ev_detail=ev,
        )
        assert pr.priority_score == 0.1

    def test_priority_score_mid_range(self):
        from core.priority.ev_engine import EVResult
        from core.target_intelligence.prioritizer import PriorityResult

        ev = EVResult(
            expected_value=100.0,
            estimated_reward=200,
            acceptance_probability=0.5,
            speed_multiplier=1.0,
            confidence=0.5,
            reasoning="",
            breakdown={},
        )
        pr = PriorityResult(
            target_id=1,
            target_name="t",
            expected_value=100.0,
            estimated_reward=200,
            acceptance_probability=0.5,
            speed_multiplier=1.0,
            confidence=0.5,
            ev_detail=ev,
        )
        assert pr.priority_score == 2.0

    def test_priority_score_clamps_high(self):
        from core.priority.ev_engine import EVResult
        from core.target_intelligence.prioritizer import PriorityResult

        ev = EVResult(
            expected_value=99999.0,
            estimated_reward=99999,
            acceptance_probability=1.0,
            speed_multiplier=1.5,
            confidence=1.0,
            reasoning="",
            breakdown={},
        )
        pr = PriorityResult(
            target_id=1,
            target_name="t",
            expected_value=99999.0,
            estimated_reward=99999,
            acceptance_probability=1.0,
            speed_multiplier=1.5,
            confidence=1.0,
            ev_detail=ev,
        )
        assert pr.priority_score == 10.0


class TestPrioritizer:
    def test_prioritize_empty_targets(self):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        prioritizer = TargetPrioritizer()
        p_dict, results = prioritizer.prioritize([], {})
        assert p_dict == {}
        assert results == []

    def test_prioritize_target_without_intel_defaults_to_one(self):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        target = make_target(1)
        prioritizer = TargetPrioritizer()
        p_dict, results = prioritizer.prioritize([target], {})
        assert p_dict[1] == 1.0
        assert len(results) == 0

    @patch("core.target_intelligence.prioritizer.compute_ev")
    def test_prioritize_with_intel_calls_ev_engine(self, mock_compute_ev, mock_intel):
        from core.priority.ev_engine import EVResult
        from core.target_intelligence.prioritizer import TargetPrioritizer

        mock_compute_ev.return_value = EVResult(
            expected_value=150.0,
            estimated_reward=1000,
            acceptance_probability=0.35,
            speed_multiplier=1.0,
            confidence=0.7,
            reasoning="test",
            breakdown={},
        )

        target = make_target(1)
        prioritizer = TargetPrioritizer()
        p_dict, results = prioritizer.prioritize([target], {1: mock_intel}, {})

        assert len(results) == 1
        r = results[0]
        assert r.target_id == 1
        assert r.estimated_reward == 1000
        assert r.attack_plan.strategies == ["django"]

        mock_compute_ev.assert_called_once()
        kwargs = mock_compute_ev.call_args.kwargs
        assert kwargs["estimated_reward"] == 1000
        assert kwargs["platform"] == "hackerone"
        assert kwargs["confidence"] == 0.7

    def test_prioritize_ranks_by_ev(self):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        intel1 = MagicMock()
        intel1.id = 1
        intel1.reward_score = 100.0
        intel1.reward_confidence = 0.5
        intel1.quality_score = 50
        intel1.attack_surface_score = 0.5
        intel1.technology_tags = ""
        intel1.program_url = ""

        intel2 = MagicMock()
        intel2.id = 2
        intel2.reward_score = 500.0
        intel2.reward_confidence = 0.8
        intel2.quality_score = 80
        intel2.attack_surface_score = 0.9
        intel2.technology_tags = "graphql"
        intel2.program_url = ""

        t1 = make_target(1)
        t2 = make_target(2)

        prioritizer = TargetPrioritizer()
        p_dict, results = prioritizer.prioritize([t1, t2], {1: intel1, 2: intel2}, {})

        assert len(results) == 2
        assert results[0].target_id == 2
        assert results[1].target_id == 1

    def test_estimate_reward_no_score_uses_default(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        mock_intel.reward_score = None
        mock_intel.program_url = ""
        prioritizer = TargetPrioritizer()
        with patch.object(prioritizer, "_revenue_metrics", None):
            reward = prioritizer._estimate_reward(mock_intel)
        assert reward == 500.0

    def test_estimate_reward_zero_score_uses_default(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        mock_intel.reward_score = 0
        mock_intel.program_url = ""
        prioritizer = TargetPrioritizer()
        with patch.object(prioritizer, "_revenue_metrics", None):
            reward = prioritizer._estimate_reward(mock_intel)
        assert reward == 500.0

    def test_estimate_reward_with_score(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        mock_intel.reward_score = 2500.0
        mock_intel.program_url = ""
        prioritizer = TargetPrioritizer()
        with patch.object(prioritizer, "_revenue_metrics", None):
            reward = prioritizer._estimate_reward(mock_intel)
        assert reward == 2500.0

    def test_detect_platform_known_domain(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        target = make_target(1)
        mock_intel.program_url = "https://bugcrowd.com/acme"
        prioritizer = TargetPrioritizer()
        platform = prioritizer._detect_platform(target, mock_intel)
        assert platform == "bugcrowd"

    def test_detect_platform_unknown_returns_none(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        target = make_target(1)
        mock_intel.program_url = "https://custom.example.com"
        prioritizer = TargetPrioritizer()
        platform = prioritizer._detect_platform(target, mock_intel)
        assert platform is None

    def test_build_attack_plan_matches_tech(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        mock_intel.technology_tags = "django,postgres,graphql"
        prioritizer = TargetPrioritizer()
        plan = prioritizer._build_attack_plan(mock_intel)

        assert "django" in plan.strategies
        assert "graphql" in plan.strategies
        assert plan.estimated_hours > 0

    def test_build_attack_plan_empty_tags(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        mock_intel.technology_tags = ""
        prioritizer = TargetPrioritizer()
        plan = prioritizer._build_attack_plan(mock_intel)

        assert plan.strategies == []
        assert plan.estimated_hours == 1.5

    def test_build_attack_plan_includes_validate_for_attackable_tech(self, mock_intel):
        from core.target_intelligence.prioritizer import TargetPrioritizer

        mock_intel.technology_tags = "graphql"
        prioritizer = TargetPrioritizer()
        plan = prioritizer._build_attack_plan(mock_intel)

        assert "validate" in plan.phases_to_run
        assert "report" in plan.phases_to_run
