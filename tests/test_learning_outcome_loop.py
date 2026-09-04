"""Tests for Outcome Learning Loop."""

from __future__ import annotations

import pytest

from core.learning.outcome_loop import (
    get_outcome_learning_loop,
)


@pytest.fixture()
def clean_learning():
    """Provide a clean learning engine for each test."""
    from database.db import Base, engine

    # Drop and recreate all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    loop = get_outcome_learning_loop()
    yield loop

    # Cleanup
    Base.metadata.drop_all(bind=engine)


class TestOutcomeLearningLoop:
    """Tests for Outcome Learning Loop."""

    def test_record_outcome(self, clean_learning):
        """Test recording an outcome."""
        outcome = clean_learning.record_outcome(
            outcome_id="test_outcome_1",
            mission_id="mission-1",
            platform="hackerone",
            category="web",
            predicted_reward_usd=500.0,
            predicted_acceptance_prob=0.7,
            predicted_time_hours=10.0,
            actual_reward_usd=450.0,
            actual_accepted=1,
            actual_time_hours=8.0,
        )
        assert outcome["outcome_id"] == "test_outcome_1"
        assert outcome["platform"] == "hackerone"
        assert outcome["actual_accepted"] == 1
        assert outcome["prediction_error"] == pytest.approx(0.1111, rel=0.01)
        assert outcome["acceptance_error"] == pytest.approx(0.69, rel=0.01)
        assert outcome["calibration_score"] > 0

    def test_calibration(self, clean_learning):
        """Test calibration computation."""
        # Record a few outcomes
        for i in range(3):
            clean_learning.record_outcome(
                outcome_id=f"test_outcome_{i}",
                mission_id=f"mission-{i}",
                platform="hackerone",
                category="web",
                predicted_reward_usd=500.0,
                predicted_acceptance_prob=0.7,
                predicted_time_hours=10.0,
                actual_reward_usd=450.0,
                actual_accepted=1,
                actual_time_hours=8.0,
            )

        cal = clean_learning.compute_calibration(platform="hackerone", days_back=30)
        assert cal.platform == "hackerone"
        assert cal.sample_count == 3
        assert cal.avg_prediction_error == pytest.approx(0.1111, rel=0.01)
        assert cal.avg_acceptance_error == pytest.approx(0.69, rel=0.01)
        assert cal.trust_level in ("HIGH", "MEDIUM", "LOW", "CRITICAL")

    def test_calibration_report(self, clean_learning):
        """Test calibration report generation."""
        clean_learning.record_outcome(
            outcome_id="test_outcome_1",
            mission_id="mission-1",
            platform="hackerone",
            category="web",
            predicted_reward_usd=500.0,
            predicted_acceptance_prob=0.7,
            predicted_time_hours=10.0,
            actual_reward_usd=450.0,
            actual_accepted=1,
            actual_time_hours=8.0,
        )

        report = clean_learning.compute_calibration_report(days_back=30)
        assert report["total_outcomes"] == 1
        assert "overall_calibration" in report
        assert "platform_calibrations" in report
        assert "category_calibrations" in report
        assert "alert" in report

    def test_calibration_alerts(self, clean_learning):
        """Test calibration alerts."""
        clean_learning.record_outcome(
            outcome_id="test_outcome_1",
            mission_id="mission-1",
            platform="hackerone",
            category="web",
            predicted_reward_usd=500.0,
            predicted_acceptance_prob=0.7,
            predicted_time_hours=10.0,
            actual_reward_usd=450.0,
            actual_accepted=1,
            actual_time_hours=8.0,
        )

        alerts = clean_learning.check_calibration_alerts(threshold=0.3)
        assert len(alerts) >= 1
        assert any(a["type"] == "CALIBRATION_DRIFT" for a in alerts)


class TestOutcomeLearningIntegration:
    """Integration tests for the learning loop."""

    def test_record_outcome_from_mission(self, clean_learning):
        """Test recording outcomes from completed missions."""
        # This would require a mission with revenue entries
        # For now, just verify the method exists and runs without error
        outcomes = clean_learning.record_outcome_from_mission("nonexistent-mission")
        assert isinstance(outcomes, list)

    def test_recalibration(self, clean_learning):
        """Test recalibration functions."""
        # Record some outcomes first
        for i in range(3):
            clean_learning.record_outcome(
                outcome_id=f"test_outcome_{i}",
                mission_id=f"mission-{i}",
                platform="hackerone",
                category="web",
                predicted_reward_usd=500.0,
                predicted_acceptance_prob=0.7,
                predicted_time_hours=10.0,
                actual_reward_usd=450.0,
                actual_accepted=1,
                actual_time_hours=8.0,
            )

        # Test recalibration
        from core.learning.outcome_loop import run_learning_recalibration

        result = run_learning_recalibration()
        assert "scorer" in result
        assert "recommender" in result
        assert "report" in result
        assert "alerts" in result
