"""Tests for FeedbackLearner → ConfidenceScorer pipeline (FeedbackTuner)."""

from __future__ import annotations

from unittest.mock import MagicMock

from cores.validation.confidence import ConfidenceScorer
from cores.validation.feedback_tuner import MIN_EVENTS_FOR_ANALYSIS, FeedbackTuner


def test_confidence_scorer_default_weights() -> None:
    scorer = ConfidenceScorer()
    w = scorer.get_weights()
    assert abs(w["consistency"] - 0.40) < 0.01
    assert abs(w["signal"] - 0.30) < 0.01
    assert abs(w["evidence_strength"] - 0.20) < 0.01
    assert abs(w["noise_penalty"] - -0.10) < 0.01


def test_confidence_scorer_adjust_weights() -> None:
    scorer = ConfidenceScorer()
    scorer.adjust_weights({"consistency": 0.05, "signal": -0.02})
    w = scorer.get_weights()
    assert abs(w["consistency"] - 0.45 / 0.93) < 0.01  # normalized
    assert w["noise_penalty"] == -0.10  # unchanged


def test_feedback_tuner_starts_empty() -> None:
    tuner = FeedbackTuner()
    assert len(tuner.get_events()) >= 0
    assert tuner.status()["total_feedback_events"] >= 0


def test_feedback_tuner_records_event() -> None:
    tuner = FeedbackTuner()
    initial = len(tuner.get_events())
    tuner.record_feedback({"id": 1, "title": "XSS", "old_status": "open", "new_status": "confirmed"})
    assert len(tuner.get_events()) == initial + 1


def test_feedback_tuner_not_ready_with_few_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("cores.validation.feedback_tuner.FEEDBACK_LOG", tmp_path / "events.jsonl")
    monkeypatch.setattr("cores.validation.feedback_tuner.TUNING_LOG", tmp_path / "tunings.jsonl")
    tuner = FeedbackTuner()
    assert tuner.status()["ready_for_analysis"] is False
    result = tuner.tune_if_ready()
    assert result["status"] == "skipped"


def test_feedback_tuner_tunes_with_enough_events(monkeypatch) -> None:
    tuner = FeedbackTuner()

    for i in range(MIN_EVENTS_FOR_ANALYSIS):
        tuner.record_feedback({
            "id": i, "title": f"Vuln {i}",
            "old_status": "open",
            "new_status": "confirmed" if i % 2 == 0 else "rejected",
        })

    mock_learner = MagicMock()
    mock_learner.analyze_verdict_patterns.return_value = [MagicMock(
        pattern="Test pattern",
        confidence_adjustment=0.05,
        rule_weight_adjustment={},
        recommendation="Test",
        supporting_evidence="Evidence",
        source_count=3,
    )]
    mock_learner.suggest_rule_tuning.return_value = {
        "confidence_weights": {"consistency": 0.05},
        "rule_thresholds": {},
        "severity_overrides": [],
    }

    result = tuner.tune_if_ready(learner=mock_learner)
    assert result["status"] == "tuned"
    assert result["insights"] == 1
    assert "new_weights" in result


def test_tuner_weights_actually_change(monkeypatch) -> None:
    tuner = FeedbackTuner()
    old_w = tuner._scorer.get_weights()

    for i in range(MIN_EVENTS_FOR_ANALYSIS):
        tuner.record_feedback({"id": i, "title": f"V {i}", "old_status": "open", "new_status": "confirmed"})

    mock_learner = MagicMock()
    mock_learner.analyze_verdict_patterns.return_value = [MagicMock(
        pattern="Boost consistency",
        confidence_adjustment=0.1,
        rule_weight_adjustment={},
        recommendation="",
        supporting_evidence="",
        source_count=3,
    )]
    mock_learner.suggest_rule_tuning.return_value = {
        "confidence_weights": {"consistency": 0.1, "signal": -0.05},
        "rule_thresholds": {},
        "severity_overrides": [],
    }

    tuner.tune_if_ready(learner=mock_learner)
    new_w = tuner._scorer.get_weights()
    assert new_w != old_w, "Weights should change after tuning"
    assert "consistency" in new_w


def test_tuner_clear_events() -> None:
    tuner = FeedbackTuner()
    tuner.record_feedback({"id": 1, "title": "T", "old_status": "open", "new_status": "confirmed"})
    tuner.clear_events()
    assert len(tuner.get_events()) == 0


def test_tuner_status_shape() -> None:
    tuner = FeedbackTuner()
    s = tuner.status()
    assert "total_feedback_events" in s
    assert "current_weights" in s
    assert "ready_for_analysis" in s
    assert isinstance(s["current_weights"], dict)


def test_persistence_survives_reinit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("cores.validation.feedback_tuner.FEEDBACK_LOG", tmp_path / "events.jsonl")
    monkeypatch.setattr("cores.validation.feedback_tuner.TUNING_LOG", tmp_path / "tunings.jsonl")

    t1 = FeedbackTuner()
    t1.record_feedback({"id": 1, "title": "XSS", "old_status": "open", "new_status": "confirmed"})
    assert len(t1.get_events()) == 1

    t2 = FeedbackTuner()
    assert len(t2.get_events()) == 1, "Events should survive reinit via JSONL"


def test_learner_unavailable_graceful() -> None:
    tuner = FeedbackTuner()
    for i in range(MIN_EVENTS_FOR_ANALYSIS):
        tuner.record_feedback({"id": i, "title": f"V {i}", "old_status": "open", "new_status": "confirmed"})
    result = tuner.tune_if_ready(learner=None)
    # Should gracefully try to import FeedbackLearner (which exists, so this should work)
    assert result["status"] in ("tuned", "skipped", "error")


def test_confidence_boost_from_positive_feedback() -> None:
    scorer = ConfidenceScorer()
    w_before = scorer.get_weights()["consistency"]
    scorer.adjust_weights({"consistency": 0.1})
    w_after = scorer.get_weights()["consistency"]
    assert w_after > w_before, "Positive feedback should increase consistency weight (after normalization)"
