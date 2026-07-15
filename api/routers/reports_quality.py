from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from core.reports.quality.classifier import QualityClassifier
from core.reports.quality.scorer import QualityScorer
from database import db
from database.models import Finding

logger = logging.getLogger("orion.api.reports_quality")

router = APIRouter(prefix="/api/reports/quality", tags=["reports"])


@router.get("/{finding_id}")
def get_finding_quality(finding_id: int):
    """Evaluate report quality for a finding (score 0-100, classification, suggestions)."""
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

        classifier = QualityClassifier()
        classification = classifier.classify(quality_score)

        return {
            "finding_id": finding_id,
            "score": quality_score.to_dict(),
            "classification": classification.to_dict(),
            "verdict": classification.badge,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        logger.exception("Quality gate error for finding %s", finding_id)
        raise HTTPException(status_code=500, detail="Internal quality evaluation error") from None
