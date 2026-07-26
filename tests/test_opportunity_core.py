"""Tests for the Opportunity Score Engine (core/opportunity/)."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.opportunity import (
    OWNEX_WORK_CYCLE_ORDER,
    OWNEX_WORK_CYCLES,
    PersonalHistory,
    PersonalHistoryTracker,
    ScoredOpportunity,
    Top5Engine,
    Top5Recommendation,
    UnifiedScore,
    score_opportunity,
)


class TestUnifiedScore:
    def test_reasoning_contains_all_factors(self):
        s = UnifiedScore(
            expected_value=150.0,
            acceptance_probability=0.35,
            speed_days=14.0,
            difficulty=0.6,
            competition=0.7,
            personal_fit=0.4,
            confidence=0.8,
            overall=0.45,
        )
        lines = s.reasoning()
        assert len(lines) == 8
        assert "EV=" in lines[0]
        assert "acceptance=" in lines[1]
        assert "speed=" in lines[2]
        assert "difficulty=" in lines[3]
        assert "competition=" in lines[4]
        assert "fit=" in lines[5]
        assert "confidence=" in lines[6]
        assert "overall=" in lines[7]

    def test_defaults(self):
        s = UnifiedScore()
        assert s.expected_value == 0.0
        assert s.overall == 0.0


class TestModels:
    def test_personal_history_defaults(self):
        h = PersonalHistory()
        assert h.personal_acceptance_rate == 0.0
        assert h.total_submissions == 0

    def test_personal_history_with_data(self):
        h = PersonalHistory(
            personal_acceptance_rate=0.35,
            personal_avg_payout=250.0,
            personal_avg_days=14.0,
            personal_competition_level=0.65,
            total_submissions=20,
            total_accepted=7,
            by_platform={
                "hackerone": {"acceptance_rate": 0.4, "total": 10, "accepted": 4},
                "bugcrowd": {"acceptance_rate": 0.3, "total": 10, "accepted": 3},
            },
            by_vuln_type={
                "xss": {"total_payout": 500.0, "count": 3, "avg_payout": 166.67},
            },
        )
        assert h.personal_acceptance_rate == 0.35
        assert h.by_platform["hackerone"]["accepted"] == 4

    def test_top5_recommendation_to_dict_empty(self):
        rec = Top5Recommendation(
            ranked=[],
            generated_at="2026-07-26T00:00:00",
            total_scored=0,
            diversification_note="No opportunities.",
            summary="Empty.",
        )
        d = rec.to_dict()
        assert d["total_scored"] == 0
        assert d["top5"] == []

    def test_top5_recommendation_to_dict_with_items(self):
        score = UnifiedScore(
            expected_value=100.0,
            acceptance_probability=0.5,
            speed_days=7.0,
            difficulty=0.3,
            competition=0.4,
            personal_fit=0.8,
            confidence=0.9,
            overall=0.75,
        )
        opp = ScoredOpportunity(
            id="test-1",
            name="Test Opportunity",
            cycle="security",
            source_type="platform",
            source_name="hackerone",
            reward=500.0,
            effort_hours=5.0,
            platform="hackerone",
            technology_tags=["api", "graphql"],
            url="https://example.com",
            created_at="2026-07-26T00:00:00",
            score=score,
        )
        rec = Top5Recommendation(
            ranked=[opp],
            generated_at="2026-07-26T00:00:00",
            total_scored=1,
            diversification_note="1 selected from 1 scored. Cycles: security.",
            summary="Top 1: Test Opportunity ($100 EV).",
        )
        d = rec.to_dict()
        assert d["total_scored"] == 1
        assert len(d["top5"]) == 1
        assert d["top5"][0]["id"] == "test-1"
        assert d["top5"][0]["score"]["overall"] == 0.75
        assert "EV= $100.00" in d["top5"][0]["score"]["reasoning"][0]

    def test_ownex_constants(self):
        assert "security" in OWNEX_WORK_CYCLES
        assert "forge" in OWNEX_WORK_CYCLES
        assert "pulse" in OWNEX_WORK_CYCLES
        assert "vault" in OWNEX_WORK_CYCLES
        assert "atlas" in OWNEX_WORK_CYCLES
        assert OWNEX_WORK_CYCLE_ORDER[0] == "security"


class TestScorer:
    def test_score_security_opportunity(self):
        opp = score_opportunity(
            opp_id="test-1",
            name="HackerOne API Program",
            cycle="security",
            source_type="platform",
            source_name="hackerone",
            reward=1000.0,
            effort_hours=10.0,
            platform="hackerone",
            technology_tags=["api", "graphql", "jwt"],
            url="https://hackerone.com/program",
            created_at="2026-07-01T00:00:00",
        )
        assert opp.id == "test-1"
        assert opp.cycle == "security"
        assert opp.score.expected_value > 0
        assert 0 <= opp.score.overall <= 1
        assert opp.score.difficulty > 0
        assert opp.score.competition > 0

    def test_score_with_personal_history(self):
        personal = PersonalHistory(
            personal_acceptance_rate=0.5,
            personal_avg_payout=300.0,
            total_submissions=20,
            total_accepted=10,
            by_platform={
                "hackerone": {"acceptance_rate": 0.5, "total": 10, "accepted": 5},
                "bugcrowd": {"acceptance_rate": 0.4, "total": 10, "accepted": 4},
            },
            by_vuln_type={
                "xss": {"total_payout": 500.0, "count": 3, "avg_payout": 166.67},
            },
        )
        opp = score_opportunity(
            opp_id="test-2",
            name="Bugcrowd XSS Program",
            cycle="security",
            source_type="platform",
            source_name="bugcrowd",
            reward=500.0,
            effort_hours=5.0,
            platform="bugcrowd",
            technology_tags=["xss"],
            url="https://bugcrowd.com/program",
            created_at="2026-07-15T00:00:00",
            personal=personal,
        )
        assert opp.score.acceptance_probability > 0
        assert opp.score.personal_fit > 0.3
        assert opp.score.expected_value > 0

    def test_score_high_reward_low_effort_ranks_higher(self):
        personal = PersonalHistory(
            personal_acceptance_rate=0.5,
            by_platform={"hackerone": {"acceptance_rate": 0.5, "total": 10, "accepted": 5}},
            by_vuln_type={"xss": {"total_payout": 500.0, "count": 3, "avg_payout": 166.67}},
        )
        high = score_opportunity(
            opp_id="high",
            name="High Reward",
            cycle="security",
            source_type="platform",
            source_name="hackerone",
            reward=5000.0,
            effort_hours=5.0,
            platform="hackerone",
            technology_tags=["api"],
            personal=personal,
        )
        low = score_opportunity(
            opp_id="low",
            name="Low Reward",
            cycle="security",
            source_type="platform",
            source_name="hackerone",
            reward=50.0,
            effort_hours=40.0,
            platform="hackerone",
            technology_tags=["solidity", "web3"],
            personal=personal,
        )
        assert high.score.overall > low.score.overall
        assert high.score.expected_value > low.score.expected_value

    def test_score_difficulty_by_tags(self):
        easy = score_opportunity(
            opp_id="easy",
            name="Easy XSS",
            cycle="security",
            source_type="platform",
            source_name="hackerone",
            reward=200.0,
            effort_hours=2.0,
            platform="hackerone",
            technology_tags=["xss"],
        )
        hard = score_opportunity(
            opp_id="hard",
            name="Hard Web3",
            cycle="security",
            source_type="platform",
            source_name="immunefi",
            reward=50000.0,
            effort_hours=80.0,
            platform="immunefi",
            technology_tags=["solidity", "web3", "defi", "rust", "move"],
        )
        assert easy.score.difficulty < hard.score.difficulty
        assert easy.score.overall > 0
        assert hard.score.overall > 0

    def test_score_without_tags(self):
        opp = score_opportunity(
            opp_id="no-tags",
            name="No Tags",
            cycle="pulse",
            source_type="platform",
            source_name="mindrift",
            reward=100.0,
            effort_hours=2.0,
            platform="mindrift",
        )
        assert opp.score.difficulty == 0.4
        assert opp.score.overall > 0

    def test_score_without_personal_history(self):
        opp = score_opportunity(
            opp_id="no-history",
            name="No History",
            cycle="forge",
            source_type="platform",
            source_name="superteam",
            reward=500.0,
            effort_hours=10.0,
            platform="superteam",
            technology_tags=["rust", "api"],
        )
        assert opp.score.personal_fit == 0.3
        assert opp.score.competition == 0.4

    def test_group_score_use_case(self):
        personal = PersonalHistory(
            by_platform={
                "hackerone": {"acceptance_rate": 0.4, "total": 15, "accepted": 6},
                "bugcrowd": {"acceptance_rate": 0.3, "total": 10, "accepted": 3},
                "immunefi": {"acceptance_rate": 0.0, "total": 2, "accepted": 0},
            },
            by_vuln_type={"xss": {"total_payout": 600.0, "count": 4, "avg_payout": 150.0}},
        )
        opps = [
            score_opportunity(
                opp_id=f"opp-{i}",
                name=f"Opportunity {i}",
                cycle="security" if i < 3 else "forge",
                source_type="platform",
                source_name="hackerone" if i % 2 == 0 else "bugcrowd",
                reward=[5000.0, 200.0, 1000.0, 800.0, 50.0][i],
                effort_hours=[10.0, 1.0, 5.0, 20.0, 0.5][i],
                platform="hackerone" if i % 2 == 0 else "bugcrowd",
                technology_tags=[["api"], ["xss"], ["graphql"], ["rust"], ["csrf"]][i],
                personal=personal,
            )
            for i in range(5)
        ]
        scored = sorted(opps, key=lambda o: o.score.overall, reverse=True)
        assert scored[0].score.overall >= scored[-1].score.overall
        assert all(0 <= o.score.overall <= 1 for o in scored)
        assert all(o.score.expected_value >= 0 for o in scored)


class TestTop5Engine:
    def _make_opp(self, uid: str, cycle: str, source: str, overall: float) -> ScoredOpportunity:
        return ScoredOpportunity(
            id=uid,
            name=f"Opp {uid}",
            cycle=cycle,
            source_type="platform",
            source_name=source,
            reward=100.0,
            effort_hours=5.0,
            platform=source,
            technology_tags=[],
            url=None,
            created_at="2026-07-26T00:00:00",
            score=UnifiedScore(overall=overall, expected_value=overall * 100),
        )

    def test_empty_list(self):
        engine = Top5Engine()
        result = engine.compute([])
        assert result.total_scored == 0
        assert result.ranked == []
        assert "No opportunities" in result.summary

    def test_selects_top_5(self):
        sources = [
            "hackerone",
            "bugcrowd",
            "intigriti",
            "yeswehack",
            "immunefi",
            "hackerone",
            "bugcrowd",
            "intigriti",
            "yeswehack",
            "immunefi",
        ]
        opps = [self._make_opp(str(i), "security", sources[i], 0.9 - i * 0.01) for i in range(10)]
        engine = Top5Engine()
        result = engine.compute(opps)
        assert len(result.ranked) == 5
        assert result.total_scored == 10

    def test_diversification_across_cycles(self):
        opps = [
            self._make_opp("s1", "security", "hackerone", 0.9),
            self._make_opp("s2", "security", "bugcrowd", 0.89),
            self._make_opp("s3", "security", "intigriti", 0.88),
            self._make_opp("f1", "forge", "superteam", 0.87),
            self._make_opp("p1", "pulse", "mindrift", 0.86),
            self._make_opp("v1", "vault", "coingecko", 0.85),
            self._make_opp("a1", "atlas", "linkedin", 0.84),
        ]
        engine = Top5Engine(max_per_cycle=2)
        result = engine.compute(opps)
        assert len(result.ranked) == 5
        cycles = [o.cycle for o in result.ranked]
        assert len(set(cycles)) >= 2

    def test_diversification_limits_per_source(self):
        opps = [
            self._make_opp("h1", "security", "hackerone", 0.9),
            self._make_opp("h2", "security", "hackerone", 0.89),
            self._make_opp("h3", "security", "hackerone", 0.88),
            self._make_opp("b1", "security", "bugcrowd", 0.87),
            self._make_opp("i1", "security", "intigriti", 0.86),
        ]
        engine = Top5Engine(max_per_source=1)
        result = engine.compute(opps)
        sources = [o.source_name for o in result.ranked if o.source_name == "hackerone"]
        assert len(sources) <= 1

    def test_less_than_5_opportunities(self):
        sources = ["hackerone", "bugcrowd", "intigriti"]
        opps = [self._make_opp(str(i), "security", sources[i], 0.5) for i in range(3)]
        engine = Top5Engine()
        result = engine.compute(opps)
        assert len(result.ranked) == 3

    def test_summary_contains_top_info(self):
        opps = [self._make_opp("best", "security", "hackerone", 0.95)]
        engine = Top5Engine()
        result = engine.compute(opps)
        assert "best" in result.summary
        assert "$95" in result.summary

    def test_diversification_note(self):
        opps = [
            self._make_opp("s1", "security", "hackerone", 0.9),
            self._make_opp("f1", "forge", "superteam", 0.8),
        ]
        engine = Top5Engine()
        result = engine.compute(opps)
        assert "security" in result.diversification_note
        assert "forge" in result.diversification_note


class TestPersonalHistoryTracker:
    def test_get_history_empty(self):
        mock = MagicMock()
        mock.acceptance_rate.return_value = {}
        mock.payout_summary.return_value = {"total_payout": 0.0, "total_count": 0}
        mock.time_metrics.return_value = {"avg_days_to_acceptance": 0.0}
        mock.roi_by_vuln_type.return_value = []

        tracker = PersonalHistoryTracker(metrics=mock)
        history = tracker.get_history()
        assert history.total_submissions == 0
        assert history.total_accepted == 0
        assert history.personal_acceptance_rate == 0.0
        assert history.personal_avg_payout == 0.0
        assert history.by_platform == {}
        assert history.by_vuln_type == {}

    def test_get_history_with_data(self):
        mock = MagicMock()
        mock.acceptance_rate.return_value = {
            "hackerone": {"total": 10, "accepted": 4, "rejected": 4, "pending": 2},
            "bugcrowd": {"total": 5, "accepted": 2, "rejected": 2, "pending": 1},
        }
        mock.payout_summary.return_value = {
            "total_payout": 3000.0,
            "total_count": 6,
            "avg_payout": 500.0,
            "pending_total": 0.0,
            "pending_count": 0,
            "by_platform": {"hackerone": 2000.0, "bugcrowd": 1000.0},
            "by_currency": {"usd": 3000.0},
        }
        mock.time_metrics.return_value = {"avg_days_to_acceptance": 12.5, "acceptance_samples": 6}
        mock.roi_by_vuln_type.return_value = [
            {"vuln_type": "xss", "total_payout": 1500.0, "count": 3, "avg_payout": 500.0},
        ]

        tracker = PersonalHistoryTracker(metrics=mock)
        history = tracker.get_history()
        assert history.total_submissions == 15
        assert history.total_accepted == 6
        expected_rate = 6 / (15 - 3)
        assert abs(history.personal_acceptance_rate - expected_rate) < 0.01
        assert history.personal_avg_payout == 500.0
        assert history.personal_avg_days == 12.5
        assert "hackerone" in history.by_platform
        assert "xss" in history.by_vuln_type
        assert history.by_vuln_type["xss"]["avg_payout"] == 500.0
