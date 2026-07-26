from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.auto_submit.pipeline import AutoSubmitPipeline, get_auto_submit_pipeline
from core.revenue.pipeline import PipelineResult


@pytest.fixture(autouse=True)
def reset_singleton():
    import core.auto_submit.pipeline as mod

    mod._PIPELINE = None
    yield


@pytest.fixture
def pipeline():
    return AutoSubmitPipeline(elite_threshold=85.0, review_threshold=60.0)


def _make_finding(
    id_: int = 1,
    target_id: int | None = 1,
    title: str = "Test IDOR",
    description: str = "An IDOR vulnerability was found",
    vulnerability_type: str = "idor",
    severity: str = "high",
    status: str = "confirmed",
):
    finding = MagicMock()
    finding.id = id_
    finding.target_id = target_id
    finding.title = title
    finding.description = description
    finding.vulnerability_type = vulnerability_type
    finding.severity = severity
    finding.status = status
    return finding


def _make_finding_direct(id_: int = 1):
    return _make_finding(id_=id_)


def _make_quality_score(score: float = 85.0):
    qs = MagicMock()
    qs.score = score
    return qs


def _make_classification(passed: bool = True):
    cls = MagicMock()
    cls.passed = passed
    cls.label = "elite" if passed else "review"
    return cls


# ── on_finding_confirmed ──────────────────────────────────────


@patch("core.auto_submit.pipeline.QualityClassifier")
@patch("core.auto_submit.pipeline.QualityScorer")
@patch("core.auto_submit.pipeline.db")
def test_skip_below_review(mock_db, mock_scorer_cls, mock_classifier_cls, pipeline):
    mock_session = MagicMock()
    mock_db.SessionLocal.return_value = mock_session
    mock_session.query.return_value.filter.return_value.first.return_value = _make_finding(id_=1)
    scorer = MagicMock()
    scorer.score.return_value = _make_quality_score(30.0)
    mock_scorer_cls.return_value = scorer
    result = pipeline.on_finding_confirmed(1)
    assert result["action"] == "skip"
    assert result["score"] == 30.0


@patch("core.auto_submit.pipeline.QualityClassifier")
@patch("core.auto_submit.pipeline.QualityScorer")
@patch("core.auto_submit.pipeline.db")
def test_review_between_thresholds(mock_db, mock_scorer_cls, mock_classifier_cls, pipeline):
    mock_session = MagicMock()
    mock_db.SessionLocal.return_value = mock_session
    mock_session.query.return_value.filter.return_value.first.return_value = _make_finding(id_=1)
    scorer = MagicMock()
    scorer.score.return_value = _make_quality_score(70.0)
    mock_scorer_cls.return_value = scorer
    classifier = MagicMock()
    classifier.classify.return_value = _make_classification(passed=False)
    mock_classifier_cls.return_value = classifier
    result = pipeline.on_finding_confirmed(1)
    assert result["action"] == "queued_for_review"
    assert result["score"] == 70.0


@patch("core.auto_submit.pipeline.QualityClassifier")
@patch("core.auto_submit.pipeline.QualityScorer")
@patch("core.auto_submit.pipeline.db")
@patch("core.auto_submit.pipeline.get_bus")
@patch("core.auto_submit.pipeline.get_vault")
@patch("core.auto_submit.pipeline.get_revenue_pipeline")
def test_elite_auto_submits(
    mock_get_revenue, mock_get_vault, mock_get_bus, mock_db, mock_scorer_cls, mock_classifier_cls, pipeline
):
    mock_db.SessionLocal.side_effect = None
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = _make_finding(id_=1)
    mock_session2 = MagicMock()
    mock_session2.query.return_value.filter.return_value.first.return_value = None  # no target
    mock_db.SessionLocal.return_value = mock_session

    scorer = MagicMock()
    scorer.score.return_value = _make_quality_score(90.0)
    mock_scorer_cls.return_value = scorer
    classifier = MagicMock()
    classifier.classify.return_value = _make_classification(passed=True)
    mock_classifier_cls.return_value = classifier

    mock_vault = MagicMock()
    mock_vault.get.return_value = "test-key-123"
    mock_get_vault.return_value = mock_vault

    pipeline_result = PipelineResult(success=True, submission_id=42)
    mock_revenue = MagicMock()
    mock_revenue.submit_report.return_value = pipeline_result
    mock_get_revenue.return_value = mock_revenue

    mock_bus = MagicMock()
    mock_get_bus.return_value = mock_bus

    result = pipeline.on_finding_confirmed(1)
    assert result["action"] == "auto_submitted"

    scorer = MagicMock()
    scorer.score.return_value = _make_quality_score(90.0)
    mock_scorer_cls.return_value = scorer
    classifier = MagicMock()
    classifier.classify.return_value = _make_classification(passed=True)
    mock_classifier_cls.return_value = classifier

    mock_vault = MagicMock()
    mock_vault.get.return_value = "test-key-123"
    mock_get_vault.return_value = mock_vault

    pipeline_result = PipelineResult(success=True, submission_id=42)
    mock_revenue = MagicMock()
    mock_revenue.submit_report.return_value = pipeline_result
    mock_get_revenue.return_value = mock_revenue

    mock_bus = MagicMock()
    mock_get_bus.return_value = mock_bus

    result = pipeline.on_finding_confirmed(1)
    assert result["action"] == "auto_submitted"
    assert result["score"] == 90.0
    assert result["submission_id"] == 42
    mock_revenue.submit_report.assert_called_once()
    mock_bus.publish.assert_called_once_with(
        "auto_submit:executed",
        finding_id=1,
        platform="hackerone",
        score=90.0,
        success=True,
        submission_id=42,
        error=None,
    )


@patch("core.auto_submit.pipeline.QualityClassifier")
@patch("core.auto_submit.pipeline.QualityScorer")
@patch("core.auto_submit.pipeline.db")
@patch("core.auto_submit.pipeline.get_bus")
@patch("core.auto_submit.pipeline.get_vault")
@patch("core.auto_submit.pipeline.get_revenue_pipeline")
def test_elite_no_api_key_falls_back_to_review(
    mock_get_revenue, mock_get_vault, mock_get_bus, mock_db, mock_scorer_cls, mock_classifier_cls, pipeline
):
    mock_session = MagicMock()
    mock_db.SessionLocal.return_value = mock_session
    mock_session.query.return_value.filter.return_value.first.return_value = _make_finding(id_=1)
    scorer = MagicMock()
    scorer.score.return_value = _make_quality_score(90.0)
    mock_scorer_cls.return_value = scorer
    classifier = MagicMock()
    classifier.classify.return_value = _make_classification(passed=True)
    mock_classifier_cls.return_value = classifier

    mock_vault = MagicMock()
    mock_vault.get.return_value = None
    mock_get_vault.return_value = mock_vault

    mock_bus = MagicMock()
    mock_get_bus.return_value = mock_bus

    result = pipeline.on_finding_confirmed(1)
    assert result["action"] == "queued_for_review"
    assert result["score"] == 90.0


# ── _detect_platform ────────────────────────────────────────────


@patch("core.auto_submit.pipeline.db")
def test_detect_platform_no_target(mock_db, pipeline):
    finding = _make_finding(target_id=None)
    assert pipeline._detect_platform(finding) == "hackerone"


@patch("core.auto_submit.pipeline.db")
def test_detect_platform_from_target_name(mock_db, pipeline):
    mock_session = MagicMock()
    mock_db.SessionLocal.return_value = mock_session
    mock_target = MagicMock()
    mock_target.name = "bugcrowd_myprogram"
    mock_session.query.return_value.filter.return_value.first.return_value = mock_target
    finding = _make_finding(target_id=5)
    assert pipeline._detect_platform(finding) == "bugcrowd"


@patch("core.auto_submit.pipeline.db")
def test_detect_platform_unknown_prefix(mock_db, pipeline):
    mock_session = MagicMock()
    mock_db.SessionLocal.return_value = mock_session
    mock_target = MagicMock()
    mock_target.name = "custom_vdp"
    mock_session.query.return_value.filter.return_value.first.return_value = mock_target
    finding = _make_finding(target_id=5)
    assert pipeline._detect_platform(finding) == "hackerone"


# ── _get_api_key ──────────────────────────────────────────────


@patch("core.auto_submit.pipeline.get_vault")
def test_get_api_key_from_vault(mock_get_vault, pipeline):
    mock_vault = MagicMock()
    mock_vault.get.return_value = "vault-key-123"
    mock_get_vault.return_value = mock_vault
    assert pipeline._get_api_key("hackerone") == "vault-key-123"


@patch("core.auto_submit.pipeline.get_vault")
def test_get_api_key_fallback_env(mock_get_vault, pipeline):
    mock_vault = MagicMock()
    mock_vault.get.return_value = None
    mock_get_vault.return_value = mock_vault
    with patch.dict("os.environ", {"HACKERONE_API_KEY": "env-key-456"}):
        assert pipeline._get_api_key("hackerone") == "env-key-456"


# ── singleton ─────────────────────────────────────────────────


def test_get_auto_submit_pipeline_singleton():
    p1 = get_auto_submit_pipeline()
    p2 = get_auto_submit_pipeline()
    assert p1 is p2


def test_get_auto_submit_pipeline_defaults():
    p = get_auto_submit_pipeline()
    assert p.elite_threshold == 85.0
    assert p.review_threshold == 60.0


# ── finding not found ──────────────────────────────────────────


@patch("core.auto_submit.pipeline.QualityScorer")
@patch("core.auto_submit.pipeline.db")
def test_on_finding_confirmed_not_found(mock_db, mock_scorer_cls, pipeline):
    mock_session = MagicMock()
    mock_db.SessionLocal.return_value = mock_session
    mock_session.query.return_value.filter.return_value.first.return_value = None
    result = pipeline.on_finding_confirmed(999)
    assert result["action"] == "error"
    assert "not found" in result["reason"]
