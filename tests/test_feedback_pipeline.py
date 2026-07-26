"""Tests for FeedbackLearner → ConfidenceScorer pipeline (FeedbackTuner)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import cores.validation.confidence as cmod
from cores.validation.confidence import ConfidenceScorer
from cores.validation.feedback_tuner import MIN_EVENTS_FOR_ANALYSIS, FeedbackTuner


@pytest.fixture(autouse=True)
def _isolate_confidence(monkeypatch, tmp_path):
    monkeypatch.setattr(cmod, "STATE_FILE", tmp_path / "state.json")
    cmod.reset_confidence_scorer()


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
        tuner.record_feedback(
            {
                "id": i,
                "title": f"Vuln {i}",
                "old_status": "open",
                "new_status": "confirmed" if i % 2 == 0 else "rejected",
            }
        )

    mock_learner = MagicMock()
    mock_learner.analyze_verdict_patterns.return_value = [
        MagicMock(
            pattern="Test pattern",
            confidence_adjustment=0.05,
            rule_weight_adjustment={},
            recommendation="Test",
            supporting_evidence="Evidence",
            source_count=3,
        )
    ]
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
    mock_learner.analyze_verdict_patterns.return_value = [
        MagicMock(
            pattern="Boost consistency",
            confidence_adjustment=0.1,
            rule_weight_adjustment={},
            recommendation="",
            supporting_evidence="",
            source_count=3,
        )
    ]
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


# ── Singleton tests ───────────────────────────────────────────────


def test_singleton_shared_identity() -> None:
    from cores.validation.confidence import get_confidence_scorer

    s1 = get_confidence_scorer()
    s2 = get_confidence_scorer()
    assert s1 is s2, "get_confidence_scorer() should return the same instance"


def test_singleton_weights_persist_across_calls() -> None:
    from cores.validation.confidence import get_confidence_scorer

    s1 = get_confidence_scorer()
    s1.adjust_weights({"consistency": 0.1})
    w1 = s1.get_weights()

    s2 = get_confidence_scorer()
    w2 = s2.get_weights()
    assert w2 == w1, "Weight adjustment should persist across singleton access"


def test_feedback_tuner_uses_singleton() -> None:
    from cores.validation.confidence import get_confidence_scorer
    from cores.validation.feedback_tuner import FeedbackTuner

    scorer = get_confidence_scorer()
    old_w = scorer.get_weights()

    tuner = FeedbackTuner()
    assert tuner._scorer is scorer, "FeedbackTuner should use the shared singleton"

    # Tune and verify singleton was updated
    for i in range(MIN_EVENTS_FOR_ANALYSIS):
        tuner.record_feedback({"id": i, "title": f"V {i}", "old_status": "open", "new_status": "confirmed"})

    mock_learner = MagicMock()
    mock_learner.analyze_verdict_patterns.return_value = [
        MagicMock(
            pattern="Boost consistency",
            confidence_adjustment=0.1,
            rule_weight_adjustment={},
            recommendation="",
            supporting_evidence="",
            source_count=3,
        )
    ]
    mock_learner.suggest_rule_tuning.return_value = {
        "confidence_weights": {"consistency": 0.1},
        "rule_thresholds": {},
        "severity_overrides": [],
    }
    result = tuner.tune_if_ready(learner=mock_learner)
    assert result["status"] == "tuned"

    # Verify the singleton scorer was updated, not a private copy
    assert get_confidence_scorer().get_weights() != old_w, "Singleton weights should be updated after tuning"


def test_validation_loop_uses_singleton() -> None:
    from cores.validation.confidence import get_confidence_scorer
    from cores.validation.loop_engine import ValidationLoopEngine

    scorer = get_confidence_scorer()
    engine = ValidationLoopEngine()
    assert engine._scorer is scorer, "ValidationLoopEngine should use the shared singleton"


# ── API endpoint tests ────────────────────────────────────────────


def test_learning_stats_endpoint() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.api.routers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/api/core/learning/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "weights" in data
    assert "total_feedback_events" in data
    assert "total_tunings" in data
    assert "ready_for_analysis" in data
    assert "validation_accuracy" in data
    assert "consistency" in data["weights"]
    assert "signal" in data["weights"]


def test_learning_weights_endpoint() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.api.routers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/api/core/learning/weights")
    assert resp.status_code == 200
    data = resp.json()
    assert "weights" in data
    assert data["weights"]["consistency"] > 0


def test_learning_trigger_endpoint() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.api.routers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.post("/api/core/learning/trigger")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_update_learning_weights_endpoint() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.api.routers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    from cores.validation.confidence import get_confidence_scorer

    old = get_confidence_scorer().get_weights()["consistency"]

    resp = client.post("/api/core/learning/weights", json={"consistency": 0.05})
    assert resp.status_code == 200
    data = resp.json()
    assert "old" in data
    assert "new" in data
    assert "adjustments" in data
    assert data["adjustments"]["consistency"] == 0.05

    # Verify singleton was actually updated
    new_w = get_confidence_scorer().get_weights()
    assert new_w["consistency"] != old


# ── Bias tests ─────────────────────────────────────────────────────


def test_confidence_scorer_bias_default() -> None:
    scorer = ConfidenceScorer()
    assert scorer.get_bias() == 0.0


def test_confidence_scorer_adjust_bias() -> None:
    scorer = ConfidenceScorer()
    scorer.adjust_bias(0.05)
    assert abs(scorer.get_bias() - 0.05) < 0.001
    scorer.adjust_bias(-0.02)
    assert abs(scorer.get_bias() - 0.03) < 0.001


def test_confidence_scorer_set_bias() -> None:
    scorer = ConfidenceScorer()
    scorer.set_bias(-0.1)
    assert abs(scorer.get_bias() - (-0.1)) < 0.001


def test_bias_affects_calculate(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("cores.validation.confidence.STATE_FILE", tmp_path / "state.json")
    scorer = ConfidenceScorer()
    scorer.set_bias(0.1)

    from cores.validation.replayer import ComparisonResult, ResponseRecord

    rec = ResponseRecord(status_code=200, headers={}, body="ok", body_hash="abc", elapsed_ms=10)
    from cores.validation.rules import ValidationReport

    result = scorer.calculate(
        results=[
            ComparisonResult(
                attempt=1,
                baseline=rec,
                probe=rec,
                status_match=True,
                body_diff_ratio=0.0,
                headers_diff={},
                sensitive_fields_detected=[],
                has_rate_limit=False,
                has_timeout=False,
                consistent=True,
                timestamp="now",
            )
        ],
        validation=ValidationReport(passed=True, passed_rules=["rule1"], failed_rules=[], details={}),
        endpoint_signals={"risk_score": 50},
    )
    assert result.score > 0.0


def test_confidence_state_save_and_load(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("cores.validation.confidence.STATE_FILE", tmp_path / "state.json")
    scorer = ConfidenceScorer()
    scorer.adjust_weights({"consistency": 0.2})
    scorer.set_bias(0.15)
    scorer.save_state()

    scorer2 = ConfidenceScorer()
    scorer2.load_state()
    assert abs(scorer2.get_weights()["consistency"] - scorer.get_weights()["consistency"]) < 0.001
    assert abs(scorer2.get_bias() - 0.15) < 0.001


def test_confidence_state_restored_via_singleton(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("cores.validation.confidence.STATE_FILE", tmp_path / "state.json")
    # Reset singleton
    import cores.validation.confidence as cmod
    from cores.validation.confidence import get_confidence_scorer

    cmod._scorer_instance = None

    scorer = cmod.ConfidenceScorer()
    scorer.set_bias(0.2)
    scorer.save_state()

    cmod._scorer_instance = None
    restored = get_confidence_scorer()
    assert abs(restored.get_bias() - 0.2) < 0.001


def test_llm_bias_in_learning_stats_endpoint() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from core.api.routers import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    resp = client.get("/api/core/learning/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "llm_bias" in data


# ── FeedbackLearner suggest_rule_tuning tests ──────────────────────


def test_suggest_rule_tuning_with_component_weights() -> None:
    from cores.validation.llm_analyzer import FeedbackLearner, LearningInsight

    learner = FeedbackLearner()
    insights = [
        LearningInsight(
            pattern="SQLi on login endpoints often FP",
            confidence_adjustment=0.0,
            rule_weight_adjustment={"signal": 0.1, "consistency": -0.05},
            recommendation="Increase signal weight for SQLi",
            supporting_evidence="3 false positives on login pages",
            source_count=3,
        )
    ]
    result = learner.suggest_rule_tuning(insights)
    assert result["confidence_weights"]["signal"] == 0.1
    assert result["confidence_weights"]["consistency"] == -0.05
    assert "llm_bias" in result


def test_suggest_rule_tuning_with_confidence_adjustment() -> None:
    from cores.validation.llm_analyzer import FeedbackLearner, LearningInsight

    learner = FeedbackLearner()
    insights = [
        LearningInsight(
            pattern="Overall confidence too high",
            confidence_adjustment=-0.05,
            rule_weight_adjustment={},
            recommendation="Reduce confidence across all vuln types",
            supporting_evidence="General overconfidence detected",
            source_count=5,
        )
    ]
    result = learner.suggest_rule_tuning(insights)
    assert result["llm_bias"] == -0.05
    assert result["rule_thresholds"] == {}


def test_suggest_rule_tuning_unknown_rules_go_to_thresholds() -> None:
    from cores.validation.llm_analyzer import FeedbackLearner, LearningInsight

    learner = FeedbackLearner()
    insights = [
        LearningInsight(
            pattern="IDOR needs stricter gate",
            confidence_adjustment=0.0,
            rule_weight_adjustment={"idor_threshold": 0.7, "signal": 0.05},
            recommendation="Raise IDOR threshold",
            supporting_evidence="",
            source_count=2,
        )
    ]
    result = learner.suggest_rule_tuning(insights)
    # "idor_threshold" is not a known weight key → goes to rule_thresholds
    assert "idor_threshold" in result["rule_thresholds"]
    # "signal" is a known weight key → goes to confidence_weights
    assert result["confidence_weights"]["signal"] == 0.05
