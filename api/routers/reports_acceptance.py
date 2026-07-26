from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from core.reports.acceptance.learner import AcceptanceLearner
from core.reports.quality.scorer import QualityScorer

logger = logging.getLogger("orion.api.reports_acceptance")

router = APIRouter(prefix="/api/reports/acceptance", tags=["reports"])

_learner: AcceptanceLearner | None = None


def _get_learner() -> AcceptanceLearner:
    global _learner
    if _learner is None:
        _learner = AcceptanceLearner()
    return _learner


@router.get("/summary")
def get_acceptance_summary():
    """Get overall acceptance optimizer summary with per-platform profiles."""
    learner = _get_learner()
    return learner.get_summary()


@router.get("/predict")
def predict_acceptance(
    finding_id: int = Query(..., description="Finding ID to evaluate"),
    platform: str = Query("hackerone", description="Target platform"),
):
    """Predict acceptance probability for a finding on a given platform."""
    from database import db
    from database.models import Finding

    session = db.SessionLocal()
    try:
        f = session.query(Finding).filter(Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
    finally:
        session.close()

    try:
        scorer = QualityScorer()
        quality_score = scorer.score(finding_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        logger.exception("Quality scoring failed for finding %s", finding_id)
        raise HTTPException(status_code=500, detail="Internal quality scoring error") from None

    learner = _get_learner()
    prediction = learner.predict(
        platform=platform,
        score=quality_score.score,
        dimensions=quality_score.dimensions,
        evidence_count=quality_score.evidence_count,
    )

    return {
        "finding_id": finding_id,
        "prediction": prediction.to_dict(),
        "quality_score": quality_score.to_dict(),
    }


@router.post("/record-outcome")
def record_submission_outcome(
    submission_id: int = Query(..., description="SubmissionRecord ID"),
):
    """Record a submission outcome (accepted/rejected) and update learner."""
    learner = _get_learner()
    result = learner.record_outcome(submission_id)
    if result is None:
        raise HTTPException(
            status_code=400,
            detail="Could not record outcome. Submission must have a terminal status (accepted/rejected).",
        )
    return {
        "recorded": True,
        "outcome": result.outcome,
        "platform": result.platform,
        "score": result.score,
        "summary": learner.get_summary(),
    }


@router.post("/record-manual")
def record_manual_outcome(
    platform: str = Query(..., description="Platform name"),
    program: str = Query("", description="Program name"),
    vulnerability_type: str = Query("unknown", description="Vulnerability type"),
    outcome: str = Query(..., description="accepted or rejected"),
    score: float = Query(0.0, ge=0, le=100, description="Quality score"),
    severity: str = Query("medium", description="Severity"),
    evidence_count: int = Query(0, ge=0, description="Evidence count"),
):
    """Manually record an acceptance/rejection outcome for learning."""
    if outcome not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="outcome must be 'accepted' or 'rejected'")

    learner = _get_learner()
    obs = learner.record_manual_outcome(
        platform=platform.lower().strip(),
        program=program or "unknown",
        vulnerability_type=vulnerability_type,
        outcome=outcome,
        score=score,
        severity=severity,
        evidence_count=evidence_count,
    )
    return {
        "recorded": True,
        "outcome": obs.to_dict(),
        "summary": learner.get_summary(),
    }


@router.get("/profiles")
def list_platform_profiles():
    """List all platform profiles learned from outcomes."""
    learner = _get_learner()
    profiles = learner.get_profiles()
    return {
        "profiles": {p: profile.to_dict() for p, profile in profiles.items()},
        "total_platforms": len(profiles),
    }


@router.get("/profiles/{platform}")
def get_platform_profile(platform: str):
    """Get detailed profile for a specific platform."""
    learner = _get_learner()
    profile = learner.get_platform_profile(platform.lower().strip())
    if not profile:
        raise HTTPException(status_code=404, detail=f"No profile for platform '{platform}'")
    return profile.to_dict()


@router.get("/observations")
def list_observations(limit: int = Query(50, ge=1, le=500)):
    """List recent outcome observations."""
    learner = _get_learner()
    return {
        "observations": learner.get_observations(limit=limit),
        "total": len(learner.get_observations(limit=10000)),
    }


@router.post("/sync")
def sync_from_db():
    """Sync all historical submission outcomes from the database."""
    learner = _get_learner()
    count = learner.sync_from_db()
    return {
        "synced": count,
        "summary": learner.get_summary(),
    }


@router.post("/sync-hacktivity")
def sync_hacktivity(max_pages: int = Query(3, ge=1, le=10)):
    """Scrape HackerOne hacktivity and feed disclosed reports into the learner."""
    from core.reports.acceptance.scraper import feed_hacktivity_to_learner

    count = feed_hacktivity_to_learner(max_pages=max_pages, delay=1.5)
    learner = _get_learner()
    return {
        "synced": count,
        "summary": learner.get_summary(),
    }


@router.get("/weights")
def get_adapted_weights():
    """Get the adapted quality weights learned from acceptance outcomes."""
    learner = _get_learner()
    return {
        "adapted_weights": learner.get_weights(),
        "summary": learner.get_summary(),
    }
