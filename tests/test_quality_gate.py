from __future__ import annotations

import pytest

from core.reports.quality.classifier import QualityClassifier
from core.reports.quality.scorer import QualityScore, QualityScorer


def test_quality_score_data_class() -> None:
    score = QualityScore(
        finding_id=1,
        score=85.0,
        dimensions={"evidence": 1.0, "reproducibility": 0.8},
        weights={"evidence": 20.0, "reproducibility": 20.0},
        review={"passed": True, "items": []},
        analysis={"status": "report_ready", "confidence": 0.9},
        evidence_count=3,
        verdict_count=1,
    )
    d = score.to_dict()
    assert d["finding_id"] == 1
    assert d["score"] == 85.0
    assert d["evidence_count"] == 3
    assert d["verdict_count"] == 1


def test_quality_classification_elite() -> None:
    score = QualityScore(
        finding_id=1,
        score=92.0,
        dimensions={
            "evidence": 1.0,
            "reproducibility": 1.0,
            "clarity": 1.0,
            "impact_severity": 1.0,
            "completeness": 1.0,
            "confidence": 1.0,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={"passed": True, "items": []},
        evidence_count=3,
        verdict_count=1,
    )
    classifier = QualityClassifier()
    result = classifier.classify(score)
    assert result.label == "elite"
    assert result.badge == "Elite"
    assert result.passed is True


def test_quality_classification_review() -> None:
    score = QualityScore(
        finding_id=2,
        score=72.0,
        dimensions={
            "evidence": 0.8,
            "reproducibility": 0.7,
            "clarity": 0.8,
            "impact_severity": 0.6,
            "completeness": 0.5,
            "confidence": 0.7,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={"passed": False, "items": []},
        evidence_count=1,
        verdict_count=1,
    )
    classifier = QualityClassifier()
    result = classifier.classify(score)
    assert result.label == "review"
    assert result.badge == "Review"
    assert result.passed is True


def test_quality_classification_no_recommend() -> None:
    score = QualityScore(
        finding_id=3,
        score=45.0,
        dimensions={
            "evidence": 0.0,
            "reproducibility": 0.0,
            "clarity": 0.5,
            "impact_severity": 0.3,
            "completeness": 0.2,
            "confidence": 0.2,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={"passed": False, "items": [{"name": "evidence_exists", "status": "failed", "notes": ""}]},
        evidence_count=0,
        verdict_count=0,
    )
    classifier = QualityClassifier()
    result = classifier.classify(score)
    assert result.label == "no_recommend"
    assert result.badge == "No Recomendar"
    assert result.passed is False


def test_classification_suggestions_generated() -> None:
    score = QualityScore(
        finding_id=4,
        score=55.0,
        dimensions={
            "evidence": 0.0,
            "reproducibility": 0.4,
            "clarity": 0.6,
            "impact_severity": 0.3,
            "completeness": 0.2,
            "confidence": 0.5,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={
            "passed": False,
            "items": [
                {"name": "evidence_exists", "status": "failed", "notes": ""},
                {"name": "cvss_assigned", "status": "failed", "notes": ""},
                {"name": "cwe_classified", "status": "failed", "notes": ""},
                {"name": "has_remediation", "status": "failed", "notes": ""},
            ],
        },
        analysis={
            "status": "needs_review",
            "confidence": 0.3,
            "inconsistencies": ["Sin evidencia adjunta al hallazgo"],
            "recommendations": ["Recolectar evidencia antes de continuar"],
        },
        evidence_count=0,
        verdict_count=0,
    )
    classifier = QualityClassifier()
    result = classifier.classify(score)
    assert len(result.improvement_suggestions) > 0
    assert any("evidencia" in s.lower() for s in result.improvement_suggestions)
    assert any("CVSS" in s for s in result.improvement_suggestions)
    assert any("CWE" in s for s in result.improvement_suggestions)


def test_classification_improvement_suggestions_dedup() -> None:
    score = QualityScore(
        finding_id=5,
        score=40.0,
        dimensions={
            "evidence": 0.0,
            "reproducibility": 0.0,
            "clarity": 0.5,
            "impact_severity": 0.3,
            "completeness": 0.2,
            "confidence": 0.2,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={
            "passed": False,
            "items": [
                {"name": "evidence_exists", "status": "failed", "notes": ""},
                {"name": "reproducible", "status": "failed", "notes": ""},
            ],
        },
        analysis={
            "status": "needs_review",
            "confidence": 0.2,
            "inconsistencies": ["Sin evidencia adjunta al hallazgo"],
            "recommendations": ["Recolectar evidencia antes de continuar"],
        },
        evidence_count=0,
        verdict_count=0,
    )
    classifier = QualityClassifier()
    result = classifier.classify(score)
    suggestions_lower = [s.lower() for s in result.improvement_suggestions]
    assert len(suggestions_lower) == len(set(suggestions_lower)), "No duplicate suggestions allowed"


def test_classification_dimension_breakdown() -> None:
    score = QualityScore(
        finding_id=6,
        score=75.0,
        dimensions={
            "evidence": 0.9,
            "reproducibility": 0.8,
            "clarity": 0.7,
            "impact_severity": 0.6,
            "completeness": 0.5,
            "confidence": 0.8,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={"passed": False, "items": []},
        evidence_count=2,
        verdict_count=1,
    )
    classifier = QualityClassifier()
    result = classifier.classify(score)
    assert len(result.dimension_breakdown) == 6
    for dim in result.dimension_breakdown:
        assert "dimension" in dim
        assert "score" in dim
        assert "weight" in dim
        assert "contribution" in dim
    assert result.dimension_breakdown[0]["score"] <= result.dimension_breakdown[-1]["score"]


def test_quality_score_to_dict_full() -> None:
    score = QualityScore(
        finding_id=7,
        score=88.3,
        dimensions={
            "evidence": 1.0,
            "reproducibility": 0.9,
            "clarity": 0.95,
            "impact_severity": 0.85,
            "completeness": 0.8,
            "confidence": 0.9,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={"passed": True, "items": [{"name": "test", "status": "passed", "notes": ""}]},
        analysis={"status": "report_ready", "confidence": 0.9},
        evidence_count=5,
        verdict_count=2,
    )
    d = score.to_dict()
    assert d["score"] == 88.3
    assert d["review"]["passed"] is True
    assert d["analysis"]["status"] == "report_ready"


def test_classification_improvement_suggestions_max_8() -> None:
    many_items = [{"name": f"item_{i}", "status": "failed", "notes": ""} for i in range(15)]
    score = QualityScore(
        finding_id=8,
        score=10.0,
        dimensions={
            "evidence": 0.0,
            "reproducibility": 0.0,
            "clarity": 0.0,
            "impact_severity": 0.0,
            "completeness": 0.0,
            "confidence": 0.0,
        },
        weights={
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        },
        review={"passed": False, "items": many_items},
        evidence_count=0,
        verdict_count=0,
    )
    classifier = QualityClassifier()
    result = classifier.classify(score)
    assert len(result.improvement_suggestions) <= 8


def test_scorer_dimension_computation() -> None:
    scorer = QualityScorer()

    dims = scorer._compute_dimensions(
        review={
            "passed": False,
            "items": [
                {"name": "evidence_exists", "status": "passed", "notes": "3 items"},
                {"name": "reproducible", "status": "passed", "notes": ""},
                {"name": "has_explanation", "status": "passed", "notes": ""},
                {"name": "cvss_assigned", "status": "passed", "notes": "CVSS: 7.5"},
                {"name": "cwe_classified", "status": "passed", "notes": ""},
                {"name": "impact_defined", "status": "passed", "notes": ""},
                {"name": "has_remediation", "status": "passed", "notes": ""},
                {"name": "confidence_adequate", "status": "passed", "notes": ""},
                {"name": "alternatives_checked", "status": "passed", "notes": ""},
            ],
        },
        analysis={
            "status": "report_ready",
            "confidence": 0.9,
            "needs_human": False,
            "inconsistencies": [],
            "recommendations": [],
        },
        verdict={"status": "confirmed", "confidence": 0.85, "reproducibility_score": "0.95"},
        finding={
            "id": "1",
            "title": "Test Finding",
            "description": "A detailed description " * 20,
            "severity": "high",
            "notes": "Some investigation notes",
            "vulnerability_type": "IDOR",
        },
        evidence=[{"id": "1", "consistent": True}, {"id": "2", "consistent": True}, {"id": "3", "consistent": True}],
    )

    assert dims["evidence"] > 0.5
    assert dims["reproducibility"] > 0.8
    assert dims["clarity"] > 0.5
    assert dims["impact_severity"] > 0.5
    assert dims["completeness"] > 0.5
    assert dims["confidence"] > 0.5


def test_scorer_dimension_no_evidence() -> None:
    scorer = QualityScorer()

    dims = scorer._compute_dimensions(
        review={
            "passed": False,
            "items": [
                {"name": "evidence_exists", "status": "failed", "notes": "No se encontró evidencia adjunta"},
                {"name": "reproducible", "status": "failed", "notes": ""},
                {"name": "has_explanation", "status": "failed", "notes": ""},
                {"name": "cvss_assigned", "status": "failed", "notes": ""},
                {"name": "cwe_classified", "status": "failed", "notes": ""},
                {"name": "impact_defined", "status": "failed", "notes": ""},
                {"name": "has_remediation", "status": "failed", "notes": ""},
                {"name": "alternatives_checked", "status": "skipped", "notes": ""},
            ],
        },
        analysis={
            "status": "needs_review",
            "confidence": 0.2,
            "needs_human": True,
            "inconsistencies": ["Sin evidencia"],
            "recommendations": [],
        },
        verdict=None,
        finding={
            "id": "2",
            "title": "Test",
            "description": "",
            "severity": "low",
            "notes": "",
            "vulnerability_type": "unknown",
        },
        evidence=[],
    )

    assert dims["evidence"] == 0.0
    assert dims["reproducibility"] == 0.0
    assert dims["clarity"] < 0.5
    assert dims["impact_severity"] == 0.0
    assert dims["completeness"] < 0.5
    assert dims["confidence"] < 0.5


@pytest.mark.parametrize(
    "repro_raw,expected_range",
    [
        (None, (0.0, 0.1)),
        ('{"score": 0.8}', (0.7, 1.0)),
        ('{"overall": 0.5}', (0.4, 0.7)),
        ("0.9", (0.8, 1.0)),
        ("invalid", (0.7, 1.0)),
    ],
)
def test_scorer_reproducibility_parsing(repro_raw: str | None, expected_range: tuple[float, float]) -> None:
    scorer = QualityScorer()
    verdict = {"reproducibility_score": repro_raw} if repro_raw else None
    score = scorer._score_reproducibility({"status": "passed" if repro_raw else "failed"}, verdict)
    assert expected_range[0] <= score <= expected_range[1], f"Expected {expected_range}, got {score}"


@pytest.mark.parametrize(
    "desc_len,severity,expected_min",
    [
        (400, "critical", 0.8),
        (200, "high", 0.7),
        (80, "medium", 0.5),
        (20, "low", 0.0),
    ],
)
def test_scorer_clarity_and_impact(desc_len: int, severity: str, expected_min: float) -> None:
    scorer = QualityScorer()
    dims = scorer._compute_dimensions(
        review={
            "passed": True,
            "items": [
                {"name": "evidence_exists", "status": "passed", "notes": "1 item"},
                {"name": "reproducible", "status": "passed", "notes": ""},
                {"name": "has_explanation", "status": "passed", "notes": ""},
                {
                    "name": "cvss_assigned",
                    "status": "passed",
                    "notes": "CVSS: 7.5" if severity in ("critical", "high") else "passed",
                },
                {"name": "cwe_classified", "status": "passed", "notes": ""},
                {"name": "impact_defined", "status": "passed", "notes": ""},
                {"name": "has_remediation", "status": "passed", "notes": ""},
                {"name": "alternatives_checked", "status": "passed", "notes": ""},
            ],
        },
        analysis={
            "status": "report_ready",
            "confidence": 0.9,
            "needs_human": False,
            "inconsistencies": [],
            "recommendations": [],
        },
        verdict={"status": "confirmed", "confidence": 0.85},
        finding={
            "id": "1",
            "title": "T" * 30,
            "description": "D" * desc_len,
            "severity": severity,
            "notes": "Some notes for completeness",
            "vulnerability_type": "IDOR",
        },
        evidence=[{"id": "1", "consistent": True}],
    )
    total = sum(dims[dim] * (scorer.WEIGHTS[dim] / 100.0) for dim in scorer.WEIGHTS) * 100.0
    assert total >= expected_min * 100.0 * 0.3
