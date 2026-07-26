"""API endpoints for Acceptance Intelligence."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from core.acceptance.analyzer import AcceptanceAnalyzer
from core.acceptance.models import AcceptanceOutcome
from core.acceptance.optimizer import AcceptanceOptimizer
from core.acceptance.predictor import AcceptancePredictor
from database.db import SessionLocal
from database.models import Finding

router = APIRouter(prefix="/api/acceptance", tags=["acceptance"])

_analyzer = AcceptanceAnalyzer()
_predictor = AcceptancePredictor(_analyzer)
_optimizer = AcceptanceOptimizer(_analyzer)


@router.post("/outcome")
def record_submission_outcome(body: dict):
    """Record a submission outcome for learning."""
    outcome = AcceptanceOutcome(
        report_id=body.get("report_id", 0),
        platform=body.get("platform", "unknown"),
        vulnerability_type=body.get("vulnerability_type", ""),
        severity=body.get("severity", ""),
        status=body.get("status", "pending"),
        payout=float(body.get("payout", 0)),
        response_time_days=float(body.get("response_time_days", 0)),
        has_poc=bool(body.get("has_poc", False)),
        has_evidence=bool(body.get("has_evidence", False)),
        description_length=int(body.get("description_length", 0)),
        repro_steps_count=int(body.get("repro_steps_count", 0)),
        cvss_score=float(body.get("cvss_score", 0)),
        cwe_id=body.get("cwe_id", ""),
    )
    _analyzer.record_outcome(outcome)
    return {"status": "recorded", "platform": outcome.platform, "vuln_type": outcome.vulnerability_type}


@router.post("/batch-outcomes")
def record_batch_outcomes(body: dict):
    """Record multiple outcomes at once."""
    outcomes = []
    for item in body.get("outcomes", []):
        outcomes.append(
            AcceptanceOutcome(
                report_id=item.get("report_id", 0),
                platform=item.get("platform", "unknown"),
                vulnerability_type=item.get("vulnerability_type", ""),
                severity=item.get("severity", ""),
                status=item.get("status", "pending"),
                payout=float(item.get("payout", 0)),
                response_time_days=float(item.get("response_time_days", 0)),
                has_poc=bool(item.get("has_poc", False)),
                has_evidence=bool(item.get("has_evidence", False)),
                description_length=int(item.get("description_length", 0)),
                repro_steps_count=int(item.get("repro_steps_count", 0)),
                cvss_score=float(item.get("cvss_score", 0)),
                cwe_id=item.get("cwe_id", ""),
            )
        )
    _analyzer.record_batch(outcomes)
    return {"status": "recorded", "count": len(outcomes)}


@router.get("/profile/{platform}")
def get_platform_profile(platform: str):
    """Get the learned acceptance profile for a platform."""
    profile = _analyzer.get_profile(platform)
    if not profile:
        raise HTTPException(404, f"No data for platform: {platform}")
    return profile.to_dict()


@router.get("/profiles")
def list_profiles():
    """List all platform profiles."""
    profiles = _analyzer.all_profiles()
    return {p: pf.to_dict() for p, pf in profiles.items()}


@router.get("/summary")
def get_acceptance_summary():
    """Get comprehensive acceptance intelligence summary."""
    return _analyzer.summary()


@router.get("/trend/{platform}")
def get_acceptance_trend(platform: str):
    """Get acceptance rate trend for a platform."""
    return _analyzer.acceptance_trend(platform)


@router.post("/predict")
def predict_acceptance(report: dict, platform: str = Query("hackerone")):
    """Predict acceptance probability for a report."""
    result = _predictor.predict(report, platform=platform)
    return {
        "probability": result.probability,
        "confidence": result.confidence,
        "platform": result.platform,
        "top_factors": result.top_factors,
        "suggestions": [s.__dict__ for s in result.suggestions],
    }


@router.post("/optimize")
def optimize_report(report: dict, platform: str = Query("hackerone")):
    """Get improvement suggestions for a report."""
    suggestions = _optimizer.optimize(report, platform=platform)
    return {
        "suggestions": [s.__dict__ for s in suggestions],
        "total": len(suggestions),
    }


@router.get("/top-types/{platform}")
def top_vulnerability_types(platform: str, min_samples: int = Query(3, ge=1)):
    """Get vulnerability types sorted by acceptance rate."""
    return {"platform": platform, "types": _analyzer.top_vulnerability_types(platform, min_samples=min_samples)}


@router.get("/worst-types/{platform}")
def worst_vulnerability_types(platform: str, min_samples: int = Query(3, ge=1)):
    """Get vulnerability types sorted by rejection rate."""
    return {"platform": platform, "types": _analyzer.worst_vulnerability_types(platform, min_samples=min_samples)}


@router.get("/finding/{finding_id}/predict")
def predict_finding_acceptance(finding_id: int, platform: str = Query("hackerone")):
    """Predict acceptance probability for an existing finding."""
    session = SessionLocal()
    try:
        finding = session.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(404, "Finding not found")

        report = {
            "title": finding.title or "",
            "description": finding.description or "",
            "vulnerability_type": finding.vulnerability_type or "",
            "severity": finding.severity or "",
            "cvss_score": getattr(finding, "cvss_score", 0) or 0,
            "cwe_id": getattr(finding, "cwe_id", "") or "",
            "has_poc": bool(getattr(finding, "poc", None)),
            "poc": getattr(finding, "poc", None),
            "evidence": getattr(finding, "evidence", []),
            "reproduction_steps": getattr(finding, "reproduction_steps", []),
            "impact": getattr(finding, "impact", "") or getattr(finding, "business_impact", ""),
        }

        result = _predictor.predict(report, platform=platform)
        return {
            "finding_id": finding_id,
            "platform": result.platform,
            "probability": result.probability,
            "confidence": result.confidence,
            "top_factors": result.top_factors,
            "suggestions": [s.__dict__ for s in result.suggestions],
        }
    finally:
        session.close()


@router.get("/finding/{finding_id}/optimize")
def optimize_finding_report(finding_id: int, platform: str = Query("hackerone")):
    """Get optimization suggestions for an existing finding's report."""
    session = SessionLocal()
    try:
        finding = session.query(Finding).filter(Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(404, "Finding not found")

        report = {
            "title": finding.title or "",
            "description": finding.description or "",
            "vulnerability_type": finding.vulnerability_type or "",
            "severity": finding.severity or "",
            "cvss_score": getattr(finding, "cvss_score", 0) or 0,
            "cwe_id": getattr(finding, "cwe_id", "") or "",
            "poc": getattr(finding, "poc", None),
            "evidence": getattr(finding, "evidence", []),
            "reproduction_steps": getattr(finding, "reproduction_steps", []),
            "impact": getattr(finding, "impact", "") or getattr(finding, "business_impact", ""),
            "asset_type": getattr(finding, "asset_type", ""),
            "tags": getattr(finding, "tags", []),
        }

        suggestions = _optimizer.optimize(report, platform=platform)
        return {
            "finding_id": finding_id,
            "platform": platform,
            "suggestions": [s.__dict__ for s in suggestions],
            "total": len(suggestions),
        }
    finally:
        session.close()
