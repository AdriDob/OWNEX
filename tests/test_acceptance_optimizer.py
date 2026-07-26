from __future__ import annotations

from core.reports.acceptance.learner import (
    OUTCOME_ACCEPTED,
    OUTCOME_REJECTED,
    AcceptanceLearner,
    OutcomeObservation,
)

_DIMS_STRONG = {
    "evidence": 0.9,
    "reproducibility": 0.85,
    "clarity": 0.8,
    "impact_severity": 0.75,
    "completeness": 0.8,
    "confidence": 0.85,
}

_DIMS_WEAK = {
    "evidence": 0.3,
    "reproducibility": 0.4,
    "clarity": 0.5,
    "impact_severity": 0.6,
    "completeness": 0.35,
    "confidence": 0.4,
}

_DIMS_MEDIUM = {
    "evidence": 0.6,
    "reproducibility": 0.55,
    "clarity": 0.65,
    "impact_severity": 0.7,
    "completeness": 0.6,
    "confidence": 0.65,
}


def _fresh() -> AcceptanceLearner:
    return AcceptanceLearner(load_persisted=False)


def test_learner_init():
    learner = _fresh()
    assert learner.get_observations() == []
    assert learner.get_weights() is not None
    assert sum(learner.get_weights().values()) == 100.0


def test_record_manual_outcome():
    learner = _fresh()
    obs = learner.record_manual_outcome(
        platform="hackerone",
        program="test-program",
        vulnerability_type="idor",
        outcome=OUTCOME_ACCEPTED,
        dimensions=_DIMS_STRONG,
        score=85.0,
        severity="high",
        evidence_count=3,
    )
    assert obs.outcome == OUTCOME_ACCEPTED
    assert obs.platform == "hackerone"
    assert obs.score == 85.0
    assert len(learner.get_observations()) == 1


def test_record_rejection():
    learner = _fresh()
    learner.record_manual_outcome(
        platform="hackerone",
        program="test-program",
        vulnerability_type="xss",
        outcome=OUTCOME_REJECTED,
        dimensions=_DIMS_WEAK,
        score=40.0,
        severity="medium",
        evidence_count=1,
    )
    obs_list = learner.get_observations()
    assert len(obs_list) == 1
    assert obs_list[0]["outcome"] == OUTCOME_REJECTED


def test_profile_after_one_observation():
    learner = _fresh()
    learner.record_manual_outcome(
        platform="bugcrowd",
        program="prog",
        vulnerability_type="ssrf",
        outcome=OUTCOME_ACCEPTED,
        dimensions=_DIMS_STRONG,
        score=80.0,
        evidence_count=2,
    )
    profiles = learner.get_profiles()
    assert "bugcrowd" in profiles
    profile = profiles["bugcrowd"]
    assert profile.total_observations == 1
    assert profile.accepted_count == 1
    assert profile.acceptance_rate == 100.0


def test_profile_dimension_stats():
    learner = _fresh()
    for _ in range(3):
        learner.record_manual_outcome(
            platform="hackerone",
            program="prog",
            vulnerability_type="idor",
            outcome=OUTCOME_ACCEPTED,
            dimensions=_DIMS_STRONG,
            score=85.0,
            evidence_count=3,
        )
    learner.record_manual_outcome(
        platform="hackerone",
        program="prog",
        vulnerability_type="xss",
        outcome=OUTCOME_REJECTED,
        dimensions=_DIMS_WEAK,
        score=40.0,
        evidence_count=1,
    )
    profile = learner.get_platform_profile("hackerone")
    assert profile is not None
    assert profile.total_observations == 4
    assert profile.accepted_count == 3
    assert profile.rejected_count == 1

    dim = profile.dimension_profiles.get("evidence")
    assert dim is not None
    assert dim["accepted_avg"] > dim["rejected_avg"]
    assert dim["accepted_avg"] == 0.9
    assert dim["rejected_avg"] == 0.3


def test_predict_high_acceptance():
    learner = _fresh()
    for _ in range(5):
        learner.record_manual_outcome(
            platform="hackerone",
            program="prog",
            vulnerability_type="idor",
            outcome=OUTCOME_ACCEPTED,
            dimensions=_DIMS_STRONG,
            score=88.0,
            evidence_count=3,
        )
    for _ in range(2):
        learner.record_manual_outcome(
            platform="hackerone",
            program="prog",
            vulnerability_type="xss",
            outcome=OUTCOME_REJECTED,
            dimensions=_DIMS_WEAK,
            score=35.0,
            evidence_count=1,
        )
    pred = learner.predict("hackerone", score=92.0, dimensions=_DIMS_STRONG, evidence_count=4)
    assert pred.probability >= 60.0
    assert pred.platform == "hackerone"
    assert pred.confidence in ("high", "medium")


def test_predict_low_acceptance():
    learner = _fresh()
    for _ in range(3):
        learner.record_manual_outcome(
            platform="bugcrowd",
            program="prog",
            vulnerability_type="idor",
            outcome=OUTCOME_ACCEPTED,
            dimensions=_DIMS_STRONG,
            score=85.0,
            evidence_count=3,
        )
    pred = learner.predict("bugcrowd", score=30.0, dimensions=_DIMS_WEAK, evidence_count=0)
    assert pred.probability <= 70.0
    assert len(pred.recommendations) >= 0


def test_predict_no_profile():
    learner = _fresh()
    pred = learner.predict("unknown-platform", score=70.0, dimensions=_DIMS_MEDIUM, evidence_count=2)
    assert pred.probability == 50.0
    assert pred.confidence == "low"
    assert "Registrar" in pred.recommendations[0]


def test_weights_adapt_with_data():
    learner = _fresh()
    for _ in range(6):
        learner.record_manual_outcome(
            platform="hackerone",
            program="prog",
            vulnerability_type="idor",
            outcome=OUTCOME_ACCEPTED,
            dimensions=_DIMS_STRONG,
            score=85.0,
            evidence_count=3,
        )
    weights = learner.get_weights()
    assert sum(weights.values()) == 100.0
    for dim in _DIMS_STRONG:
        assert dim in weights


def test_weights_not_adapted_with_few_obs():
    learner = _fresh()
    assert learner.get_weights()["evidence"] == 20.0
    learner.record_manual_outcome(
        platform="hackerone",
        program="prog",
        vulnerability_type="idor",
        outcome=OUTCOME_ACCEPTED,
        dimensions=_DIMS_STRONG,
        score=85.0,
        evidence_count=3,
    )
    assert learner.get_weights()["evidence"] == 20.0


def test_summary():
    learner = _fresh()
    learner.record_manual_outcome(
        platform="hackerone",
        program="p1",
        vulnerability_type="idor",
        outcome=OUTCOME_ACCEPTED,
        dimensions=_DIMS_STRONG,
        score=90.0,
        evidence_count=3,
    )
    learner.record_manual_outcome(
        platform="bugcrowd",
        program="p2",
        vulnerability_type="xss",
        outcome=OUTCOME_REJECTED,
        dimensions=_DIMS_WEAK,
        score=30.0,
        evidence_count=1,
    )
    summary = learner.get_summary()
    assert summary["total_observations"] == 2
    assert summary["accepted"] == 1
    assert summary["rejected"] == 1
    assert "hackerone" in summary["platforms"]
    assert "bugcrowd" in summary["platforms"]


def test_weak_dimensions_in_prediction():
    learner = _fresh()
    for _ in range(3):
        learner.record_manual_outcome(
            platform="hackerone",
            program="prog",
            vulnerability_type="idor",
            outcome=OUTCOME_ACCEPTED,
            dimensions=_DIMS_STRONG,
            score=88.0,
            evidence_count=3,
        )
    weak_dims = {
        "evidence": 0.2,
        "reproducibility": 0.85,
        "clarity": 0.8,
        "impact_severity": 0.75,
        "completeness": 0.8,
        "confidence": 0.85,
    }
    pred = learner.predict("hackerone", score=70.0, dimensions=weak_dims, evidence_count=1)
    assert len(pred.weak_dimensions) >= 1
    has_evidence_weak = any(d["dimension"] == "evidence" for d in pred.weak_dimensions)
    assert has_evidence_weak


def test_observation_round_trip():
    obs = OutcomeObservation(
        platform="hackerone",
        program="prog",
        vulnerability_type="idor",
        outcome=OUTCOME_ACCEPTED,
        dimensions=_DIMS_STRONG,
        score=85.0,
        severity="high",
        evidence_count=3,
    )
    d = obs.to_dict()
    assert d["platform"] == "hackerone"
    assert d["outcome"] == OUTCOME_ACCEPTED
    assert d["score"] == 85.0
    assert d["evidence_count"] == 3


def test_sync_from_db_empty():
    learner = _fresh()
    count = learner.sync_from_db()
    assert count >= 0


def test_record_invalid_outcome():
    learner = _fresh()
    result = learner.record_manual_outcome(
        platform="hackerone",
        program="prog",
        vulnerability_type="idor",
        outcome="invalid_outcome",
        score=50.0,
    )
    assert result.outcome == "invalid_outcome"
    assert len(learner.get_observations()) == 1


def test_multiple_platforms():
    learner = _fresh()
    platforms = ["hackerone", "bugcrowd", "intigriti"]
    for p in platforms:
        for _ in range(3):
            learner.record_manual_outcome(
                platform=p,
                program="prog",
                vulnerability_type="idor",
                outcome=OUTCOME_ACCEPTED,
                dimensions=_DIMS_STRONG,
                score=85.0,
                evidence_count=3,
            )
    profiles = learner.get_profiles()
    assert len(profiles) == 3
    for p in platforms:
        assert p in profiles
        assert profiles[p].total_observations == 3


def test_profile_top_vuln_types():
    learner = _fresh()
    learner.record_manual_outcome(
        platform="hackerone",
        program="p1",
        vulnerability_type="idor",
        outcome=OUTCOME_ACCEPTED,
        dimensions=_DIMS_STRONG,
        score=85.0,
        evidence_count=3,
    )
    learner.record_manual_outcome(
        platform="hackerone",
        program="p2",
        vulnerability_type="xss",
        outcome=OUTCOME_REJECTED,
        dimensions=_DIMS_WEAK,
        score=30.0,
        evidence_count=1,
    )
    profile = learner.get_platform_profile("hackerone")
    assert profile is not None
    assert "idor" in profile.top_vuln_types


def test_predict_after_single_outcome():
    learner = _fresh()
    learner.record_manual_outcome(
        platform="hackerone",
        program="prog",
        vulnerability_type="ssrf",
        outcome=OUTCOME_ACCEPTED,
        dimensions=_DIMS_STRONG,
        score=90.0,
        evidence_count=3,
    )
    pred = learner.predict("hackerone", score=80.0, dimensions=_DIMS_STRONG, evidence_count=2)
    assert pred.probability > 0
