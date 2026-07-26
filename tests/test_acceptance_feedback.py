"""Tests for Acceptance Intelligence auto feedback loop."""

from __future__ import annotations

from core.acceptance.analyzer import AcceptanceAnalyzer
from core.acceptance.feedback import on_finding_status_changed


def test_feedback_confirmed_records_accepted():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 1,
            "finding_id": 1,
            "new_status": "confirmed",
            "vulnerability_type": "idor",
            "severity": "high",
            "platform": "hackerone",
            "payout": 500,
        },
        analyzer=a,
    )
    assert result["recorded"] is True
    assert result["status"] == "accepted"
    assert a.summary()["accepted"] == 1


def test_feedback_won_records_accepted():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 1,
            "new_status": "won",
            "vulnerability_type": "sqli",
            "severity": "critical",
            "platform": "bugcrowd",
            "payout": 2000,
        },
        analyzer=a,
    )
    assert result["recorded"] is True
    assert result["status"] == "won"
    assert a.summary()["accepted"] == 1


def test_feedback_rejected_records_rejected():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 2,
            "new_status": "rejected",
            "vulnerability_type": "xss",
            "severity": "medium",
            "platform": "hackerone",
        },
        analyzer=a,
    )
    assert result["recorded"] is True
    assert result["status"] == "rejected"
    assert a.summary()["rejected"] == 1


def test_feedback_false_positive_maps_to_rejected():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 3,
            "new_status": "false_positive",
            "vulnerability_type": "xss",
            "severity": "low",
            "platform": "hackerone",
        },
        analyzer=a,
    )
    assert result["recorded"] is True
    assert result["status"] == "rejected"


def test_feedback_duplicate_maps_to_rejected():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 4,
            "new_status": "duplicate",
            "vulnerability_type": "idor",
            "severity": "high",
            "platform": "hackerone",
        },
        analyzer=a,
    )
    assert result["recorded"] is True
    assert result["status"] == "rejected"


def test_feedback_pending_does_not_record():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 5,
            "new_status": "pending",
            "vulnerability_type": "xss",
            "severity": "medium",
        },
        analyzer=a,
    )
    assert result["recorded"] is False
    assert "Unmapped" in result["reason"]


def test_feedback_open_does_not_record():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 6,
            "new_status": "open",
            "vulnerability_type": "xss",
            "severity": "high",
        },
        analyzer=a,
    )
    assert result["recorded"] is False


def test_feedback_without_analyzer_still_returns():
    result = on_finding_status_changed(
        {
            "id": 7,
            "new_status": "confirmed",
            "vulnerability_type": "sqli",
            "severity": "critical",
            "platform": "hackerone",
        }
    )
    # Should not crash, but not recorded (no analyzer)
    assert result["recorded"] is True
    assert result["status"] == "accepted"


def test_feedback_accumulates_in_analyzer():
    a = AcceptanceAnalyzer()
    events = [
        {"id": i, "new_status": s, "vulnerability_type": "xss", "severity": "medium", "platform": "hackerone"}
        for i, s in enumerate(["confirmed", "rejected", "confirmed", "rejected", "confirmed"])
    ]
    for evt in events:
        on_finding_status_changed(evt, analyzer=a)

    s = a.summary()
    assert s["total_outcomes"] == 5
    assert s["accepted"] == 3
    assert s["rejected"] == 2
    assert a.get_profile("hackerone").acceptance_rate == 0.6


def test_feedback_with_evidence_and_poc():
    a = AcceptanceAnalyzer()
    result = on_finding_status_changed(
        {
            "id": 8,
            "new_status": "accepted",
            "vulnerability_type": "ssrf",
            "severity": "high",
            "platform": "intigriti",
            "poc": {"curl": "curl test"},
            "evidence": ["screenshot", "har"],
            "description": "x" * 200,
            "reproduction_steps": ["step 1", "step 2", "step 3"],
            "cvss_score": 8.5,
            "cwe_id": "CWE-918",
            "payout": 1000,
        },
        analyzer=a,
    )
    assert result["recorded"] is True
    profile = a.get_profile("intigriti")
    assert profile is not None
    assert profile.total_submissions == 1
    assert profile.accepted == 1


def test_feedback_multiple_platforms():
    a = AcceptanceAnalyzer()
    on_finding_status_changed(
        {
            "id": 10,
            "new_status": "confirmed",
            "vulnerability_type": "idor",
            "severity": "high",
            "platform": "hackerone",
        },
        analyzer=a,
    )
    on_finding_status_changed(
        {
            "id": 11,
            "new_status": "confirmed",
            "vulnerability_type": "sqli",
            "severity": "critical",
            "platform": "bugcrowd",
        },
        analyzer=a,
    )
    on_finding_status_changed(
        {
            "id": 12,
            "new_status": "rejected",
            "vulnerability_type": "xss",
            "severity": "medium",
            "platform": "hackerone",
        },
        analyzer=a,
    )

    s = a.summary()
    assert s["total_platforms"] == 2
    assert s["total_outcomes"] == 3
    assert s["accepted"] == 2
