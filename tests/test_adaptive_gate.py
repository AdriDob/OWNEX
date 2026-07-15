"""Tests for Adaptive Report Gate — per-vulnerability-type confidence thresholds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cores.validation.gate import DEFAULT_CONFIDENCE_THRESHOLD, ReportGate, get_report_gate, reset_report_gate


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


# ── Context-aware tests ─────────────────────────────


def test_context_modifier_b2b_saas_idor() -> None:
    gate = ReportGate()
    # B2B SaaS: idor threshold drops by 0.05
    threshold = gate.get_threshold("idor", "b2b_saas")
    assert threshold == pytest.approx(0.80, abs=0.001)


def test_context_modifier_critical_all() -> None:
    gate = ReportGate()
    # Critical: all thresholds drop by 0.10
    threshold = gate.get_threshold("rce", "critical")
    assert threshold == pytest.approx(0.80, abs=0.001)


def test_context_modifier_default_no_change() -> None:
    gate = ReportGate()
    assert gate.get_threshold("idor", "default") == 0.85


def test_admit_with_context() -> None:
    gate = ReportGate()
    # idor=0.85 normally, but 0.80 in b2b_saas -> 0.82 passes
    verdict = _make_verdict("confirmed", 0.82, "idor")
    assert gate.admit(verdict, "default") is False  # 0.82 < 0.85
    assert gate.admit(verdict, "b2b_saas") is True  # 0.82 >= 0.80


# ── Acceptance stats tests ─────────────────────────


def test_acceptance_stats_tracked() -> None:
    gate = ReportGate()
    gate.admit(_make_verdict("confirmed", 0.90, "idor"), "default")  # admitted
    gate.admit(_make_verdict("confirmed", 0.50, "ssrf"), "default")  # rejected
    gate.admit(_make_verdict("rejected", 0.90, "idor"), "default")  # rejected
    stats = gate.get_acceptance_stats()
    assert "idor" in stats
    assert stats["idor"]["accepted"] == 1
    assert stats["idor"]["rejected"] == 1
    assert "ssrf" in stats
    assert stats["ssrf"]["accepted"] == 0


def test_get_acceptance_rate() -> None:
    gate = ReportGate()
    assert gate.get_acceptance_rate("idor") is None  # no data yet
    gate.admit(_make_verdict("confirmed", 0.90, "idor"), "default")
    gate.admit(_make_verdict("confirmed", 0.90, "idor"), "default")
    rate = gate.get_acceptance_rate("idor")
    assert rate == 1.0


def test_reset_acceptance_stats() -> None:
    gate = ReportGate()
    gate.admit(_make_verdict("confirmed", 0.90, "idor"), "default")
    gate.reset_acceptance_stats()
    assert gate.get_acceptance_rate("idor") is None


# ── Feedback tuning tests ─────────────────────────


def test_tune_from_feedback_updates_threshold() -> None:
    gate = ReportGate()
    updated = gate.tune_from_feedback({"idor_threshold": 0.90, "ssrf_threshold": 0.80})
    assert updated == 2
    assert gate.get_threshold("idor") == 0.90
    assert gate.get_threshold("ssrf") == 0.80


def test_tune_from_feedback_clamps_values() -> None:
    gate = ReportGate()
    gate.tune_from_feedback({"idor_threshold": 1.5, "ssrf_threshold": -0.5})
    assert gate.get_threshold("idor") == 1.0
    assert gate.get_threshold("ssrf") == 0.0


def test_tune_from_feedback_unknown_type_sets_default() -> None:
    gate = ReportGate()
    updated = gate.tune_from_feedback({"unknown_threshold": 0.70})
    assert updated == 1
    assert gate.get_threshold("unknown") == 0.70


def test_tune_from_feedback_ignores_unknown_keys() -> None:
    gate = ReportGate()
    updated = gate.tune_from_feedback({"random_key": 0.90})
    assert updated == 0


def test_tune_from_feedback_persists_state() -> None:
    gate = ReportGate()
    gate.tune_from_feedback({"ssrf_threshold": 0.85})
    # Verify state file was written
    state_file = Path.home() / ".orion" / "gate_state.json"
    assert state_file.exists()
    with open(state_file) as f:
        data = json.load(f)
    assert data["thresholds"].get("ssrf") == 0.85
    # Clean up
    state_file.unlink(missing_ok=True)


# ── Singleton tests ────────────────────────────────


def test_get_report_gate_returns_singleton() -> None:
    reset_report_gate()
    g1 = get_report_gate()
    g2 = get_report_gate()
    assert g1 is g2


def test_reset_report_gate_clears_singleton() -> None:
    reset_report_gate()
    g1 = get_report_gate()
    reset_report_gate()
    g2 = get_report_gate()
    assert g1 is not g2


# ── Reject reason tests ────────────────────────────


def test_reject_reason_with_context() -> None:
    gate = ReportGate()
    verdict = _make_verdict("confirmed", 0.82, "idor")
    reason_default = gate.reject_reason(verdict, "default")
    reason_b2b = gate.reject_reason(verdict, "b2b_saas")
    assert "0.85" in reason_default or "0.85" in reason_default
    # In b2b_saas context (0.80), this should pass
    assert "confirmed" in reason_b2b.lower()


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
