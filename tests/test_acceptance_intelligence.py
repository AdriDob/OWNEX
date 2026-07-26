"""Tests for Acceptance Intelligence — learn what gets paid."""

from __future__ import annotations

from core.acceptance import AcceptanceAnalyzer, AcceptanceOptimizer, AcceptancePredictor
from core.acceptance.models import AcceptanceOutcome, OptimizerSuggestion, PlatformProfile, PredictionResult


def make_outcome(
    platform: str,
    vuln_type: str,
    severity: str,
    status: str,
    payout: float = 0,
    **kwargs,
) -> AcceptanceOutcome:
    return AcceptanceOutcome(
        report_id=kwargs.get("report_id", 0),
        platform=platform,
        vulnerability_type=vuln_type,
        severity=severity,
        status=status,
        payout=payout,
        response_time_days=kwargs.get("response_time_days", 0),
        has_poc=kwargs.get("has_poc", False),
        has_evidence=kwargs.get("has_evidence", False),
        description_length=kwargs.get("description_length", 0),
        repro_steps_count=kwargs.get("repro_steps_count", 0),
        cvss_score=kwargs.get("cvss_score", 0),
        cwe_id=kwargs.get("cwe_id", ""),
        submitted_at=kwargs.get("submitted_at"),
    )


# ── Analyzer tests ─────────────────────────────────────────────


def test_analyzer_starts_empty():
    a = AcceptanceAnalyzer()
    s = a.summary()
    assert s["total_outcomes"] == 0
    assert s["total_platforms"] == 0


def test_analyzer_records_single_outcome():
    a = AcceptanceAnalyzer()
    a.record_outcome(make_outcome("hackerone", "idor", "high", "accepted", 500))
    s = a.summary()
    assert s["total_outcomes"] == 1
    assert s["accepted"] == 1
    assert s["total_payout"] == 500.0


def test_analyzer_records_rejection():
    a = AcceptanceAnalyzer()
    a.record_outcome(make_outcome("hackerone", "xss", "medium", "rejected"))
    s = a.summary()
    assert s["total_outcomes"] == 1
    assert s["rejected"] == 1
    assert s["acceptance_rate"] == 0.0


def test_analyzer_batch():
    a = AcceptanceAnalyzer()
    outcomes = [
        make_outcome("hackerone", "idor", "high", "accepted", 500),
        make_outcome("hackerone", "xss", "medium", "rejected"),
        make_outcome("bugcrowd", "sqli", "critical", "accepted", 2000),
    ]
    a.record_batch(outcomes)
    s = a.summary()
    assert s["total_outcomes"] == 3
    assert s["total_platforms"] == 2


def test_platform_profile():
    a = AcceptanceAnalyzer()
    a.record_batch(
        [
            make_outcome("hackerone", "idor", "high", "accepted", 500),
            make_outcome("hackerone", "idor", "high", "accepted", 1500),
            make_outcome("hackerone", "xss", "medium", "rejected"),
        ]
    )
    profile = a.get_profile("hackerone")
    assert profile is not None
    assert profile.total_submissions == 3
    assert profile.accepted == 2
    assert profile.acceptance_rate == 2 / 3


def test_top_vuln_types():
    a = AcceptanceAnalyzer()
    a.record_batch(
        [
            make_outcome("hackerone", "idor", "high", "accepted", 500),
            make_outcome("hackerone", "idor", "high", "accepted", 1500),
            make_outcome("hackerone", "xss", "medium", "rejected"),
            make_outcome("hackerone", "sqli", "critical", "accepted", 2000),
        ]
    )
    top = a.top_vulnerability_types("hackerone", min_samples=1)
    assert len(top) >= 2
    # sqli and idor should be above xss
    sqli = next(t for t in top if t["type"] == "sqli")
    assert sqli["rate"] == 1.0


def test_worst_vuln_types():
    a = AcceptanceAnalyzer()
    a.record_batch(
        [
            make_outcome("hackerone", "idor", "high", "accepted", 500),
            make_outcome("hackerone", "xss", "medium", "rejected"),
            make_outcome("hackerone", "xss", "medium", "rejected"),
        ]
    )
    worst = a.worst_vulnerability_types("hackerone", min_samples=1)
    xss = next(t for t in worst if t["type"] == "xss")
    assert xss["rate"] == 0.0


def test_acceptance_trend():
    a = AcceptanceAnalyzer()
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    a.record_batch(
        [
            make_outcome("hackerone", "idor", "high", "rejected", submitted_at=now - timedelta(days=10)),
            make_outcome("hackerone", "xss", "medium", "accepted", 500, submitted_at=now - timedelta(days=5)),
            make_outcome("hackerone", "sqli", "critical", "accepted", 2000, submitted_at=now - timedelta(days=1)),
        ]
    )
    trend = a.acceptance_trend("hackerone")
    assert "trend" in trend
    assert trend["overall_rate"] > 0


# ── Predictor tests ─────────────────────────────────────────────


def test_predictor_default_probability():
    predictor = AcceptancePredictor()
    report = {"title": "Test", "description": "x" * 100}
    result = predictor.predict(report, platform="hackerone")
    assert 0 < result.probability < 1
    assert result.confidence == "low"


def test_predictor_uses_historical_data():
    a = AcceptanceAnalyzer()
    a.record_batch(
        [
            make_outcome("hackerone", "idor", "high", "accepted", 500),
            make_outcome("hackerone", "idor", "high", "accepted", 1000),
            make_outcome("hackerone", "idor", "high", "accepted", 1500),
            make_outcome("hackerone", "idor", "high", "accepted", 2000),
            make_outcome("hackerone", "idor", "high", "accepted", 2500),
        ]
    )
    predictor = AcceptancePredictor(a)
    report = {
        "title": "IDOR test",
        "vulnerability_type": "idor",
        "severity": "high",
        "description": "x" * 200,
        "cvss_score": 7.5,
        "poc": {"curl": "curl test"},
        "evidence": ["screenshot"],
        "reproduction_steps": ["step 1", "step 2", "step 3"],
    }
    result = predictor.predict(report, platform="hackerone")
    assert result.probability > 0.5
    assert result.confidence == "low"


def test_predictor_platform_alias():
    predictor = AcceptancePredictor()
    r1 = predictor.predict({"title": "test", "description": "x" * 100}, platform="h1")
    r2 = predictor.predict({"title": "test", "description": "x" * 100}, platform="hackerone")
    assert r1.platform == r2.platform


def test_predictor_returns_suggestions():
    predictor = AcceptancePredictor()
    result = predictor.predict({"title": "", "description": ""}, platform="hackerone")
    assert len(result.suggestions) > 3
    assert all(s.expected_boost > 0 for s in result.suggestions)


def test_predictor_factors_include_evidence():
    predictor = AcceptancePredictor()
    # Complete report
    complete = {
        "title": "Test",
        "vulnerability_type": "xss",
        "severity": "high",
        "description": "x" * 200,
        "cvss_score": 9.0,
        "poc": {"curl": "curl test"},
        "evidence": ["screenshot"],
        "reproduction_steps": ["step 1", "step 2", "step 3"],
        "cwe_id": "CWE-79",
        "impact": "Data theft",
    }
    r1 = predictor.predict(complete, platform="hackerone")
    # Empty report
    empty = {"title": "", "description": ""}
    r2 = predictor.predict(empty, platform="hackerone")
    assert r1.probability > r2.probability


# ── Optimizer tests ─────────────────────────────────────────────


def test_optimizer_empty_report():
    opt = AcceptanceOptimizer()
    suggestions = opt.optimize({"title": "", "description": ""}, platform="hackerone")
    assert len(suggestions) >= 5
    assert all(isinstance(s, OptimizerSuggestion) for s in suggestions)


def test_optimizer_good_report_has_fewer_suggestions():
    opt = AcceptanceOptimizer()
    good = {
        "title": "SQL Injection in search endpoint allows database extraction",
        "description": "x" * 200,
        "vulnerability_type": "sqli",
        "severity": "critical",
        "reproduction_steps": ["step 1", "step 2", "step 3"],
        "poc": {"curl": "curl test"},
        "evidence": ["screenshot", "response data"],
        "impact": "Complete database compromise",
        "cvss_score": 9.8,
        "cwe_id": "CWE-89",
        "remediation": "Use parameterized queries",
    }
    poor = {"title": "", "description": ""}
    good_suggestions = opt.optimize(good, platform="hackerone")
    poor_suggestions = opt.optimize(poor, platform="hackerone")
    assert len(good_suggestions) < len(poor_suggestions)


def test_optimizer_platform_specific():
    opt = AcceptanceOptimizer()
    report = {"title": "Test", "description": "x" * 200}

    h1 = opt.optimize(report, platform="hackerone")
    h1_fields = {s.field for s in h1}
    assert "asset_type" in h1_fields

    inti = opt.optimize(report, platform="intigriti")
    inti_fields = {s.field for s in inti}
    assert "tags" in inti_fields


def test_optimizer_weak_language():
    opt = AcceptanceOptimizer()
    report = {
        "title": "Test",
        "description": "This might be a vulnerability. I think it could be an XSS issue maybe.",
        "vulnerability_type": "xss",
        "severity": "high",
        "reproduction_steps": ["step 1", "step 2", "step 3"],
        "poc": {"curl": "curl test"},
        "evidence": ["screenshot"],
        "impact": "test",
        "cvss_score": 5.0,
        "cwe_id": "CWE-79",
    }
    suggestions = opt.optimize(report, platform="hackerone")
    weak_suggestions = [
        s
        for s in suggestions
        if "weak" in s.reason.lower() or "speculative" in s.suggestion.lower() or "confident" in s.suggestion.lower()
    ]
    assert len(weak_suggestions) > 0


def test_optimizer_no_evidence():
    opt = AcceptanceOptimizer()
    report = {
        "title": "Test vulnerability",
        "description": "x" * 200,
        "vulnerability_type": "xss",
        "severity": "high",
        "reproduction_steps": ["step 1", "step 2", "step 3"],
        "poc": {"curl": "curl test"},
        "evidence": [],
        "impact": "test",
        "cvss_score": 7.5,
        "cwe_id": "CWE-79",
        "remediation": "Fix it",
    }
    suggestions = opt.optimize(report, platform="hackerone")
    evidence_suggestions = [s for s in suggestions if s.field == "evidence"]
    assert len(evidence_suggestions) >= 1
    assert "None" in evidence_suggestions[0].current or "1 item" in evidence_suggestions[0].current


# ── PlatformProfile tests ───────────────────────────────────────


def test_platform_profile_update():
    p = PlatformProfile(platform="hackerone")
    assert p.total_submissions == 0
    assert p.acceptance_rate == 0.0

    p.update(make_outcome("hackerone", "idor", "high", "accepted", 500))
    assert p.total_submissions == 1
    assert p.accepted == 1
    assert p.acceptance_rate == 1.0
    assert p.by_type["idor"]["total"] == 1
    assert p.by_type["idor"]["accepted"] == 1

    p.update(make_outcome("hackerone", "xss", "medium", "rejected"))
    assert p.total_submissions == 2
    assert p.accepted == 1
    assert p.rejected == 1
    assert p.acceptance_rate == 0.5


def test_platform_profile_to_dict():
    p = PlatformProfile(platform="hackerone")
    p.update(make_outcome("hackerone", "idor", "high", "accepted", 500))
    d = p.to_dict()
    assert d["platform"] == "hackerone"
    assert d["accepted"] == 1
    assert d["total_submissions"] == 1
    assert "by_type" in d
    assert "by_severity" in d


# ── OptimizerSuggestion tests ───────────────────────────────────


def test_optimizer_suggestion_defaults():
    s = OptimizerSuggestion(
        field="test", current="bad", suggestion="good", reason="reason", impact="high", expected_boost=0.1
    )
    assert s.field == "test"
    assert s.impact == "high"
    assert s.expected_boost == 0.1


# ── PredictionResult tests ──────────────────────────────────────


def test_prediction_result_defaults():
    r = PredictionResult(probability=0.75, confidence="medium", platform="hackerone")
    assert r.probability == 0.75
    assert r.confidence == "medium"
    assert r.top_factors == []
    assert r.suggestions == []
