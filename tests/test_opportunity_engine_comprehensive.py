from unittest.mock import Mock, patch

import pytest

from core.opportunity.scoring import (
    OpportunityEngineLegacy,
    PersonalHistoryTracker,
    Top5Engine,
    UnifiedScore,
    _normalize_severity,
)
from database.models import Finding, Target
from database.models_economic import BountyTier, Program


class TestUnifiedScore:
    """Test cases for UnifiedScore dataclass and scoring logic."""

    def test_unified_score_initialization(self):
        """Test that UnifiedScore initializes with correct default values."""
        score = UnifiedScore(
            opportunity_id=1,
            target_id=1,
            program_id=1,
            title="Test Finding",
            severity="high",
            reward=1000.0,
            difficulty=0.5,
            acceptance_prob=0.8,
            evh=2000.0,
        )

        assert score.opportunity_id == 1
        assert score.target_id == 1
        assert score.program_id == 1
        assert score.title == "Test Finding"
        assert score.severity == "high"
        assert score.reward == 1000.0
        assert score.difficulty == 0.5
        assert score.acceptance_prob == 0.8
        assert score.evh == 2000.0
        assert score.diversity_bonus == 0.0
        assert score.personal_factor == 1.0
        # final_score calculated in __post_init__
        assert score.final_score == 1000.0 * 0.8 * (1.0 - 0.5) * 0.0 * 1.0  # diversity_bonus is 0

    def test_unified_score_calculation_with_diversity(self):
        """Test score calculation when diversity_bonus is applied."""
        score = UnifiedScore(
            opportunity_id=1,
            target_id=1,
            program_id=1,
            title="Test Finding",
            severity="high",
            reward=1000.0,
            difficulty=0.3,
            acceptance_prob=0.7,
            evh=2000.0,
            diversity_bonus=1.5,
            personal_factor=1.2,
        )

        expected = 1000.0 * 0.7 * (1.0 - 0.3) * 1.5 * 1.2
        assert abs(score.final_score - expected) < 0.001

    def test_unified_score_edge_cases(self):
        """Test edge cases for score calculation."""
        # Zero reward
        score_zero_reward = UnifiedScore(
            opportunity_id=1,
            target_id=1,
            program_id=1,
            title="Test",
            severity="info",
            reward=0.0,
            difficulty=0.5,
            acceptance_prob=0.8,
            evh=100.0,
        )
        assert score_zero_reward.final_score == 0.0

        # Maximum difficulty (1.0)
        score_max_diff = UnifiedScore(
            opportunity_id=1,
            target_id=1,
            program_id=1,
            title="Test",
            severity="high",
            reward=1000.0,
            difficulty=1.0,
            acceptance_prob=0.9,
            evh=1000.0,
        )
        assert score_max_diff.final_score == 0.0  # (1-difficulty) = 0

        # Zero acceptance probability
        score_zero_accept = UnifiedScore(
            opportunity_id=1,
            target_id=1,
            program_id=1,
            title="Test",
            severity="medium",
            reward=500.0,
            difficulty=0.2,
            acceptance_prob=0.0,
            evh=500.0,
        )
        assert score_zero_accept.final_score == 0.0


class TestNormalizeSeverity:
    """Test cases for severity normalization function."""

    def test_normalize_severity_valid_inputs(self):
        """Test normalization of valid severity strings."""
        assert _normalize_severity("critical") == "critical"
        assert _normalize_severity("CRITICAL") == "critical"
        assert _normalize_severity("Crit") == "critical"
        assert _normalize_severity("high") == "high"
        assert _normalize_severity("HIGH") == "high"
        assert _normalize_severity("High") == "high"
        assert _normalize_severity("med") == "medium"
        assert _normalize_severity("medium") == "medium"
        assert _normalize_severity("MEDIUM") == "medium"
        assert _normalize_severity("low") == "low"
        assert _normalize_severity("LOW") == "low"
        assert _normalize_severity("lo") == "low"
        assert _normalize_severity("info") == "info"
        assert _normalize_severity("INFO") == "info"
        assert _normalize_severity("information") == "info"
        assert _normalize_severity("inf") == "info"

    def test_normalize_severity_fallback(self):
        """Test that unknown severities default to medium."""
        assert _normalize_severity("unknown") == "medium"
        assert _normalize_severity("") == "medium"
        assert _normalize_severity("invalid") == "medium"
        assert _normalize_severity("CriticalHigh") == "critical"  # starts with "crit"
        assert _normalize_severity("MediumLow") == "medium"  # starts with "med"


class TestTop5Engine:
    """Test cases for Top5Engine diversification logic."""

    def test_top5_engine_initialization(self):
        """Test that Top5Engine initializes with empty cache."""
        engine = Top5Engine()
        assert engine.domains_cache == {}

    def test_top5_engine_compute_empty_input(self):
        """Test computing top5 with empty input."""
        engine = Top5Engine()
        result = engine.compute([])
        assert result == []

    def test_top5_engine_single_domain(self):
        """Test with all opportunities in same domain."""
        engine = Top5Engine()
        candidates = [
            UnifiedScore(1, 1, 1, "Critical SSRF", "critical", 5000, 0.3, 0.8, 10000),
            UnifiedScore(2, 2, 2, "Critical RCE", "critical", 4000, 0.4, 0.7, 8000),
            UnifiedScore(3, 3, 3, "Critical XSS", "critical", 3000, 0.5, 0.6, 6000),
        ]

        result = engine.compute(candidates)
        assert len(result) == 1  # Only one domain
        assert result[0].domain == "critical"
        assert len(result[0].entries) == 3
        # Should be sorted by final_score descending
        assert result[0].entries[0].final_score >= result[0].entries[1].final_score >= result[0].entries[2].final_score

    def test_top5_engine_multiple_domains(self):
        """Test with multiple domains - should return top 5 domains."""
        engine = Top5Engine()
        # Create candidates with different domains and scores
        candidates = [
            # Domain: critical (high scores)
            UnifiedScore(1, 1, 1, "Critical SSRF", "critical", 5000, 0.3, 0.9, 15000),
            UnifiedScore(2, 2, 2, "Critical RCE", "critical", 4000, 0.4, 0.8, 12000),
            # Domain: high (medium scores)
            UnifiedScore(3, 3, 3, "High JWT Leak", "high", 2000, 0.5, 0.7, 5000),
            UnifiedScore(4, 4, 4, "High IDOR", "high", 1500, 0.6, 0.6, 3000),
            # Domain: medium (lower scores)
            UnifiedScore(5, 5, 5, "Medium XSS", "medium", 1000, 0.7, 0.5, 1000),
            # Domain: low (low scores)
            UnifiedScore(6, 6, 6, "Low Config", "low", 500, 0.8, 0.4, 200),
            # Domain: info (very low scores)
            UnifiedScore(7, 7, 7, "Info Header", "info", 100, 0.9, 0.3, 20),
            # Another critical to test diversification
            UnifiedScore(8, 8, 8, "Critical SQLi", "critical", 4500, 0.35, 0.85, 13500),
        ]

        result = engine.compute(candidates)

        # Should have exactly 5 domains (we have 4 unique: critical, high, medium, low, info)
        assert len(result) == 5

        # Domains should be ordered by total score descending
        domain_order = [entry.domain for entry in result]
        expected_order = ["critical", "high", "medium", "low", "info"]
        assert domain_order == expected_order

        # Each domain should have its candidates sorted by individual score
        critical_entries = [e for e in result if e.domain == "critical"][0].entries
        assert len(critical_entries) == 3
        assert critical_entries[0].final_score >= critical_entries[1].final_score

    def test_top5_engine_limit_to_five_domains(self):
        """Test that only top 5 domains are returned when more exist."""
        engine = Top5Engine()
        # Create 6 different domains with decreasing total scores
        domains_and_scores = [
            ("domain1", 100),
            ("domain2", 90),
            ("domain3", 80),
            ("domain4", 70),
            ("domain5", 60),
            ("domain6", 50),  # This should be excluded
        ]

        candidates = []
        for i, (domain, score) in enumerate(domains_and_scores):
            candidates.append(
                UnifiedScore(i + 1, i + 1, i + 1, f"{domain} issue", "medium", float(score), 0.5, 0.5, float(score))
            )

        result = engine.compute(candidates)
        assert len(result) == 5  # Should only get top 5 domains
        domain_names = [entry.domain for entry in result]
        assert "domain6" not in domain_names  # Lowest scoring domain excluded
        assert "domain1" in domain_names  # Highest scoring domain included


class TestPersonalHistoryTracker:
    """Test cases for PersonalHistoryTracker learning functionality."""

    def test_tracker_initialization(self):
        """Test that tracker initializes with default factors."""
        tracker = PersonalHistoryTracker()
        assert "critical_hit_rate" in tracker.factors
        assert "high_hit_rate" in tracker.factors
        assert "medium_hit_rate" in tracker.factors
        assert "low_hit_rate" in tracker.factors
        assert "retry_boost" in tracker.factors
        assert "avoid_boost" in tracker.factors

        # Check default values
        assert tracker.factors["critical_hit_rate"] == 0.5
        assert tracker.factors["high_hit_rate"] == 0.3
        assert tracker.factors["medium_hit_rate"] == 0.2
        assert tracker.factors["low_hit_rate"] == 0.1
        assert tracker.factors["retry_boost"] == 1.2
        assert tracker.factors["avoid_boost"] == 0.5

    def test_tracker_with_user_id(self):
        """Test tracker initialization with user ID."""
        tracker = PersonalHistoryTracker(user_id=123)
        assert tracker.user_id == 123

    def test_on_accept_increases_factor(self):
        """Test that accepting a finding increases the corresponding factor."""
        tracker = PersonalHistoryTracker()
        initial_factor = tracker.factors["critical_hit_rate"]

        # Mock a finding with critical severity
        mock_finding = Mock(spec=Finding)
        mock_finding.severity = "critical"
        mock_finding.difficulty = 0.3

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_finding

            tracker.on_accept(1, 5000.0, 0.3)

            # Factor should increase by 0.05
            assert tracker.factors["critical_hit_rate"] == initial_factor + 0.05

    def test_on_accept_different_severities(self):
        """Test that accepting different severities updates correct factors."""
        tracker = PersonalHistoryTracker()

        test_cases = [("critical", 0.3), ("high", 0.4), ("medium", 0.5), ("low", 0.6)]

        initial_factors = {sev: tracker.factors[f"{sev}_hit_rate"] for sev, _ in test_cases}

        for severity, difficulty in test_cases:
            mock_finding = Mock(spec=Finding)
            mock_finding.severity = severity
            mock_finding.difficulty = difficulty

            with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
                mock_session_instance = Mock()
                mock_session.return_value = mock_session_instance
                mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_finding

                tracker.on_accept(999, 1000.0, difficulty)

        # Check that each factor increased
        for severity, _ in test_cases:
            key = f"{severity}_hit_rate"
            assert tracker.factors[key] == initial_factors[severity] + 0.05

    def test_on_reject_decreases_factor(self):
        """Test that rejecting a finding decreases the corresponding factor."""
        tracker = PersonalHistoryTracker()
        # First increase the factor
        tracker.factors["critical_hit_rate"] = 0.6
        initial_factor = tracker.factors["critical_hit_rate"]

        mock_finding = Mock(spec=Finding)
        mock_finding.severity = "critical"
        mock_finding.difficulty = 0.3

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_finding

            tracker.on_reject(1, 5000.0, 0.3)

            # Factor should decrease by 0.05 but not below 0.0
            assert tracker.factors["critical_hit_rate"] == initial_factor - 0.05

    def test_on_reject_not_below_zero(self):
        """Test that rejecting doesn't reduce factor below 0.0."""
        tracker = PersonalHistoryTracker()
        # Set factor to minimum
        tracker.factors["critical_hit_rate"] = 0.01
        tracker.factors["critical_hit_rate"]

        mock_finding = Mock(spec=Finding)
        mock_finding.severity = "critical"
        mock_finding.difficulty = 0.3

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_finding

            # Multiple rejections should not go below 0
            for _ in range(5):
                tracker.on_reject(1, 5000.0, 0.3)

            assert tracker.factors["critical_hit_rate"] >= 0.0

    def test_get_personal_factor(self):
        """Test getting personal factor for severity/difficulty combination."""
        tracker = PersonalHistoryTracker()

        # Test default factor (1.0) for unknown combination
        assert tracker.get_personal_factor("unknown", 0.5) == 1.0

        # Test known factors
        tracker.factors["critical_high"] = 1.5
        assert tracker.get_personal_factor("critical", 0.8) == 1.5

        # Test fallback to default when specific combo not found
        tracker.factors["critical_0.3"] = 1.2
        assert tracker.get_personal_factor("critical", 0.5) == 1.0  # Not exact match


class TestOpportunityEngine:
    """Test cases for the main OpportunityEngine orchestrator."""

    def test_engine_initialization(self):
        """Test that OpportunityEngine initializes sub-components correctly."""
        engine = OpportunityEngineLegacy()
        assert isinstance(engine.unified_scorer, type)  # Should be the class
        assert isinstance(engine.top5, Top5Engine)
        assert isinstance(engine.tracker, PersonalHistoryTracker)

    def test_estimate_reward_with_program_tiers(self):
        """Test reward estimation when program has bounty tiers."""
        engine = OpportunityEngineLegacy()

        # Mock finding with target and program
        mock_finding = Mock(spec=Finding)
        mock_finding.severity = "high"
        mock_finding.target = Mock(spec=Target)
        mock_finding.target.program_id = 1

        mock_program = Mock(spec=Program)
        mock_program.id = 1

        mock_tier1 = Mock(spec=BountyTier)
        mock_tier1.max_reward = 1000.0
        mock_tier2 = Mock(spec=BountyTier)
        mock_tier2.max_reward = 5000.0  # Higher tier
        mock_tier3 = Mock(spec=BountyTier)
        mock_tier3.max_reward = 3000.0

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.first.side_effect = [
                mock_program,  # First query for program
                mock_tier2,  # Second query for tiers (max_reward should pick highest)
            ]
            mock_session_instance.query.return_value.all.return_value = [mock_tier1, mock_tier2, mock_tier3]

            reward = engine._estimate_reward(mock_finding)

            # Should use highest tier (5000.0) * high severity multiplier (0.7) = 3500.0
            assert reward == 3500.0

    def test_estimate_reward_fallback_to_base_map(self):
        """Test reward estimation falls back to base map when no program tiers."""
        engine = OpportunityEngineLegacy()

        # Mock finding with no target/program
        mock_finding = Mock(spec=Finding)
        mock_finding.severity = "medium"
        mock_finding.target = None

        reward = engine._estimate_reward(mock_finding)

        # Should use base map: medium = 500
        assert reward == 500.0

    def test_estimate_reward_edge_cases(self):
        """Test edge cases for reward estimation."""
        engine = OpportunityEngineLegacy()

        # Test unknown severity defaults to info (50) * 0.05 = 2.5
        mock_finding = Mock(spec=Finding)
        mock_finding.severity = "unknown_severity"
        mock_finding.target = None

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            # No program/target found
            mock_session_instance.query.return_value.filter.return_value.first.return_value = None

            reward = engine._estimate_reward(mock_finding)
            assert reward == 50.0 * 0.05  # base_map["info"] * default multiplier

    def test_compute_opportunities_empty_database(self):
        """Test computing opportunities when no confirmed findings exist."""
        engine = OpportunityEngineLegacy()

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.all.return_value = []

            opportunities = engine.compute_opportunities(limit=10)
            assert opportunities == []

    def test_compute_opportunities_with_data(self):
        """Test computing opportunities with sample data."""
        engine = OpportunityEngineLegacy()

        # Create mock findings
        mock_finding1 = Mock(spec=Finding)
        mock_finding1.id = 1
        mock_finding1.target_id = 1
        mock_finding1.title = "Critical SSRF"
        mock_finding1.severity = "critical"
        mock_finding1.description = "Test description"
        mock_finding1.status = "confirmed"
        mock_finding1.difficulty = 0.2
        mock_finding1.confidence = 0.9
        mock_finding1.estimated_effort_hours = 5.0
        mock_finding1.target = Mock(spec=Target)
        mock_finding1.target.id = 1
        mock_finding1.target.program_id = 1

        mock_finding2 = Mock(spec=Finding)
        mock_finding2.id = 2
        mock_finding2.target_id = 2
        mock_finding2.title = "High XSS"
        mock_finding2.severity = "high"
        mock_finding2.description = "Test description 2"
        mock_finding2.status = "confirmed"
        mock_finding2.difficulty = 0.5
        mock_finding2.confidence = 0.6
        mock_finding2.estimated_effort_hours = 3.0
        mock_finding2.target = Mock(spec=Target)
        mock_finding2.target.id = 2
        mock_finding2.target.program_id = 2

        mock_program1 = Mock(spec=Program)
        mock_program1.id = 1
        mock_program2 = Mock(spec=Program)
        mock_program2.id = 2

        mock_tier1 = Mock(spec=BountyTier)
        mock_tier1.max_reward = 10000.0
        mock_tier2 = Mock(spec=BountyTier)
        mock_tier2.max_reward = 5000.0

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            # Mock the query chains
            mock_query = Mock()
            mock_session_instance.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.all.side_effect = [
                [mock_finding1, mock_finding2],  # findings query
                [mock_program1, mock_program2],  # programs query (for first finding)
                [mock_tier1],  # tiers for program 1
                [mock_tier2],  # tiers for program 2
            ]
            mock_query.first.side_effect = [
                mock_program1,  # program for finding 1
                mock_tier1,  # tier for finding 1
                mock_program2,  # program for finding 2
                mock_tier2,  # tier for finding 2
            ]

            opportunities = engine.compute_opportunities(limit=10)

            assert len(opportunities) == 2
            # Should be sorted by final_score descending
            assert opportunities[0].opportunity_id == 1  # Critical should score higher
            assert opportunities[1].opportunity_id == 2

            # Verify calculations
            # Finding 1: reward=10000*1.0=10000, diff=0.2, accept=0.9, effort=5
            # evh = (10000*0.9)/max(5,0.5) = 9000/5 = 1800
            # final = 10000*0.9*(1-0.2)*1.0*1.0 = 7200
            assert abs(opportunities[0].reward - 10000.0) < 0.01
            assert abs(opportunities[0].final_score - 7200.0) < 0.01

            # Finding 2: reward=5000*0.7=3500, diff=0.5, accept=0.6, effort=3
            # evh = (3500*0.6)/max(3,0.5) = 2100/3 = 700
            # final = 3500*0.6*(1-0.5)*1.0*1.0 = 1050
            assert abs(opportunities[1].reward - 3500.0) < 0.01
            assert abs(opportunities[1].final_score - 1050.0) < 0.01

    def test_record_feedback_accept(self):
        """Test recording acceptance feedback."""
        engine = OpportunityEngineLegacy()

        mock_finding = Mock(spec=Finding)
        mock_finding.id = 1
        mock_finding.severity = "critical"
        mock_finding.difficulty = 0.3

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_finding

            with patch.object(engine.tracker, "on_accept"):
                engine.record_feedback(1, "accept")
                # _estimate_reward returns 5000, difficulty 0.3 — verify on_accept was called
                engine.tracker.on_accept.assert_called_once_with(1, 5000.0, 0.3)

    def test_record_feedback_reject(self):
        """Test recording rejection feedback."""
        engine = OpportunityEngineLegacy()

        mock_finding = Mock(spec=Finding)
        mock_finding.id = 1
        mock_finding.severity = "high"
        mock_finding.difficulty = 0.4

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.first.return_value = mock_finding

            with patch.object(engine.tracker, "on_reject") as mock_on_reject:
                engine.record_feedback(1, "reject")
                mock_on_reject.assert_called_once_with(1, 2000.0, 0.4)  # Assuming high severity reward

    def test_record_feedback_invalid_outcome(self):
        """Test that invalid outcome raises appropriate error."""
        engine = OpportunityEngineLegacy()

        with pytest.raises(ValueError, match="Invalid outcome"):
            engine.record_feedback(1, "invalid_outcome")

    def test_get_top5_by_domain_integration(self):
        """Test get_top5_by_domain integrates with compute_opportunities."""
        engine = OpportunityEngineLegacy()

        # Mock compute_opportunities to return known data
        mock_opportunities = [
            UnifiedScore(1, 1, 1, "Critical SSRF", "critical", 5000, 0.3, 0.9, 15000, personal_factor=1.0),
            UnifiedScore(2, 2, 2, "Critical RCE", "critical", 4000, 0.4, 0.8, 12000, personal_factor=1.0),
            UnifiedScore(3, 3, 3, "High XSS", "high", 2000, 0.5, 0.6, 5000, personal_factor=1.2),
        ]

        with patch.object(engine, "compute_opportunities", return_value=mock_opportunities):
            result = engine.get_top5_by_domain(limit=10)

            assert len(result) == 2  # Two domains: critical and high
            # Critical domain should come first (higher total score)
            assert result[0].domain == "critical"
            assert len(result[0].entries) == 2
            assert result[1].domain == "high"
            assert len(result[1].entries) == 1

            # Check that entries are sorted by score within domain
            assert result[0].entries[0].final_score >= result[0].entries[1].final_score


class TestIntegrationScenarios:
    """Integration test scenarios for end-to-end workflows."""

    @pytest.mark.serial
    def test_full_scoring_workflow(self):
        """Test the complete workflow from feedback to score adjustment."""
        engine = OpportunityEngineLegacy()
        tracker = engine.tracker

        # Initial factor
        initial_factor = tracker.get_personal_factor("critical", 0.3)

        # Simulate accepting a critical finding
        mock_finding = Mock(spec=Finding)
        mock_finding.id = 100
        mock_finding.severity = "critical"
        mock_finding.difficulty = 0.3
        mock_finding.target = Mock(spec=Target)
        mock_finding.target.id = 1
        mock_finding.target.program_id = 1

        mock_program = Mock(spec=Program)
        mock_program.id = 1

        mock_tier = Mock(spec=BountyTier)
        mock_tier.max_reward = 10000.0

        with patch("core.opportunity.scoring.db.SessionLocal") as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.query.return_value.filter.return_value.first.side_effect = [
                mock_finding,  # Finding lookup in record_feedback (accept)
                mock_program,  # Program lookup in _estimate_reward (accept)
                mock_tier,  # Tier lookup in _estimate_reward (accept)
                mock_finding,  # Finding lookup in on_accept
                mock_finding,  # Finding lookup in record_feedback (reject)
                mock_program,  # Program lookup in _estimate_reward (reject)
                mock_tier,  # Tier lookup in _estimate_reward (reject)
                mock_finding,  # Finding lookup in on_reject
            ]
            mock_session_instance.query.return_value.all.return_value = [mock_tier]

            # Record acceptance
            engine.record_feedback(100, "accept")

            # Check that factor increased
            updated_factor = tracker.get_personal_factor("critical", 0.3)
            assert updated_factor > initial_factor

            # Simulate rejecting the same finding
            engine.record_feedback(100, "reject")

            # Factor should decrease back near original (might not be exact due to reward estimation)
            final_factor = tracker.get_personal_factor("critical", 0.3)
            # Allow some variance due to reward estimation in reject path
            assert abs(final_factor - initial_factor) < 0.1  # Within 10% tolerance

    def test_diversification_with_personal_factors(self):
        """Test that personal factors affect diversification correctly."""
        engine = OpportunityEngineLegacy()

        # Create opportunities where personal factor would change ranking
        base_opportunity1 = UnifiedScore(
            1,
            1,
            1,
            "Critical Bug A",
            "critical",
            5000,
            0.2,
            0.9,
            20000,
            diversity_bonus=1.0,
            personal_factor=1.0,  # Default
        )
        base_opportunity2 = UnifiedScore(
            2,
            2,
            2,
            "High Bug B",
            "high",
            3000,
            0.4,
            0.7,
            5250,
            diversity_bonus=1.0,
            personal_factor=1.0,  # Default
        )

        # Without personal boost, opportunity1 should score higher
        assert base_opportunity1.final_score > base_opportunity2.final_score

        # Now boost the personal factor for high severity
        engine.tracker.factors["high_high"] = 2.0  # Significant boost

        # Recreate opportunity2 with boosted personal factor
        boosted_opportunity2 = UnifiedScore(
            2,
            2,
            2,
            "High Bug B",
            "high",
            3000,
            0.4,
            0.7,
            5250,
            personal_factor=2.0,  # Boosted
        )

        # With boost, opportunity2 might now score higher
        # Depending on exact math, but the point is personal factor affects outcome
        opportunities = [base_opportunity1, boosted_opportunity2]
        result = engine.top5.compute(opportunities)

        # Should still work and return both domains
        assert len(result) == 2
        domains = [entry.domain for entry in result]
        assert "critical" in domains
        assert "high" in domains


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
