"""Tests for Adaptive Report Gate — per-vulnerability-type confidence thresholds."""

from __future__ import annotations

from cores.validation.gate import DEFAULT_CONFIDENCE_THRESHOLD, ReportGate


def test_default_threshold_for_unknown_type() -> None:
    gate = ReportGate()
    assert gate.get_threshold("unknown") == DEFAULT_CONFIDENCE_THRESHOLD


def test_threshold_for_specific_type() -> None:
    gate = ReportGate()
    assert gate.get_threshold("idor") == 0.85
    assert gate.get_threshold("ssrf") == 0.90
    assert gate.get_threshold("xss") == 0.80
    assert gate.get_threshold("auth_bypass") == 0.95


def test_threshold_is_case_insensitive() -> None:
    gate = ReportGate()
    assert gate.get_threshold("IDOR") == 0.85
    assert gate.get_threshold("SsRf") == 0.90


def test_set_threshold_overrides() -> None:
    gate = ReportGate()
    gate.set_threshold("idor", 0.90)
    assert gate.get_threshold("idor") == 0.90


def test_set_threshold_clamps_to_range() -> None:
    gate = ReportGate()
    gate.set_threshold("xss", 2.0)
    assert gate.get_threshold("xss") == 1.0
    gate.set_threshold("xss", -1.0)
    assert gate.get_threshold("xss") == 0.0


def test_reset_thresholds_restores_defaults() -> None:
    gate = ReportGate()
    gate.set_threshold("idor", 0.99)
    gate.set_threshold("ssrf", 0.50)
    gate.reset_thresholds()
    assert gate.get_threshold("idor") == 0.85
    assert gate.get_threshold("ssrf") == 0.90


def test_get_thresholds_returns_copy() -> None:
    gate = ReportGate()
    t = gate.get_thresholds()
    t["idor"] = 0.0
    assert gate.get_threshold("idor") == 0.85  # original unchanged


def test_admits_confirmed_above_threshold() -> None:
    gate = ReportGate()
    verdict = _make_verdict("confirmed", 0.90, "idor")
    assert gate.admit(verdict) is True


def test_rejects_confirmed_below_threshold() -> None:
    gate = ReportGate()
    verdict = _make_verdict("confirmed", 0.80, "idor")  # idor needs 0.85
    assert gate.admit(verdict) is False


def test_rejects_rejected_status() -> None:
    gate = ReportGate()
    verdict = _make_verdict("rejected", 0.90, "xss")
    assert gate.admit(verdict) is False


def test_rejects_inconclusive_status() -> None:
    gate = ReportGate()
    verdict = _make_verdict("inconclusive", 0.90, "xss")
    assert gate.admit(verdict) is False


def test_all_vuln_types_have_thresholds() -> None:
    gate = ReportGate()
    for vuln_type in (
        "idor",
        "ssrf",
        "xss",
        "sqli",
        "auth_bypass",
        "rce",
        "lfi",
        "open_redirect",
        "csrf",
        "information_disclosure",
        "directory_listing",
    ):
        t = gate.get_threshold(vuln_type)
        assert 0.0 <= t <= 1.0, f"{vuln_type} threshold {t} out of range"


def test_reject_reason_includes_threshold() -> None:
    gate = ReportGate()
    verdict = _make_verdict("confirmed", 0.80, "idor")
    reason = gate.reject_reason(verdict)
    assert "idor" in reason.lower()
    assert "0.85" in reason


def test_different_types_have_different_thresholds() -> None:
    gate = ReportGate()
    assert gate.get_threshold("auth_bypass") > gate.get_threshold("information_disclosure")


def test_unknown_type_uses_default() -> None:
    gate = ReportGate()
    assert gate.get_threshold("nonexistent_type") == DEFAULT_CONFIDENCE_THRESHOLD


def test_confirmed_at_exact_threshold_admits() -> None:
    gate = ReportGate()
    verdict = _make_verdict("confirmed", 0.85, "idor")
    assert gate.admit(verdict) is True


def test_confirmed_just_below_threshold_rejects() -> None:
    gate = ReportGate()
    verdict = _make_verdict("confirmed", 0.8499, "idor")
    assert gate.admit(verdict) is False


def _make_verdict(status: str, confidence: float, vuln_type: str = "unknown"):
    from cores.validation.confidence import ConfidenceScore
    from cores.validation.gate import Verdict
    from cores.validation.rules import ValidationReport

    return Verdict(
        hot_path_id="test",
        status=status,  # type: ignore[arg-type]
        confidence=confidence,
        reproducibility_score=0.5,
        validation=ValidationReport(passed=False, passed_rules=[], failed_rules=[], details={}),
        confidence_details=ConfidenceScore(score=confidence, breakdown={}, level="medium"),
        evidence_links=[],
        reason="test",
        retry_count=0,
        timestamp="2026-01-01T00:00:00",
        vulnerability_type=vuln_type,
    )
