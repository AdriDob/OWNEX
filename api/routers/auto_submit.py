"""Auto-Submit API — manage elite finding submissions.

Endpoints:
- GET /api/auto-submit/pending — view findings pending submission
- POST /api/auto-submit/approve/{finding_id} — manually approve submission
- POST /api/auto-submit/reject/{finding_id} — reject submission
- POST /api/auto-submit/config — configure elite thresholds
- GET /api/auto-submit/history — view submission history
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.settings.service import get_setting, set_setting
from database import db, models

router = APIRouter(prefix="/api/auto-submit", tags=["auto-submit"])
logger = logging.getLogger(__name__)


# ── Pydantic Models ────────────────────────────────────────────────


class EliteThresholdsConfig(BaseModel):
    """Configuration for elite quality gate."""

    min_severity: str = Field(default="high", description="Minimum severity: critical, high, medium, low")
    min_confidence: float = Field(default=0.85, ge=0.0, le=1.0, description="Minimum confidence score")
    require_evidence_complete: bool = Field(default=True, description="Require evidence_complete flag")
    require_reproduction_steps: bool = Field(default=True, description="Require clear reproduction steps")
    min_quality_score: float = Field(default=85.0, ge=0.0, le=100.0, description="Minimum overall quality score")
    max_submissions_per_hour: int = Field(default=5, ge=1, le=20, description="Rate limit: max submissions per hour")
    auto_approve_elite: bool = Field(default=True, description="Auto-approve findings that pass elite gate")


class PendingFinding(BaseModel):
    """A finding pending submission."""

    id: int
    title: str
    severity: str
    status: str
    quality_score: float | None = None
    confidence: float | None = None
    evidence_count: int = 0
    passes_elite_gate: bool = False
    rejection_reason: str | None = None
    created_at: str
    target_name: str = ""


class SubmissionHistoryItem(BaseModel):
    """A submission history record."""

    id: int
    finding_id: int
    finding_title: str
    platform: str
    action: str  # auto_submitted, manually_approved, rejected, queued_for_review
    score: float
    submission_id: str | None = None
    error: str | None = None
    created_at: str


class SubmissionResult(BaseModel):
    """Result of a submission action."""

    success: bool
    action: str
    finding_id: int
    message: str
    submission_id: str | None = None


# ── Helper Functions ─────────────────────────────────────────────


def _get_elite_thresholds() -> EliteThresholdsConfig:
    """Load elite thresholds from settings."""
    raw = get_setting("CATEYE.auto_submit.elite_thresholds", None)
    if raw:
        try:
            if isinstance(raw, str):
                raw = json.loads(raw)
            return EliteThresholdsConfig(**raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse elite thresholds, using defaults: %s", e)
    return EliteThresholdsConfig()


def _save_elite_thresholds(config: EliteThresholdsConfig) -> None:
    """Save elite thresholds to settings."""
    set_setting("CATEYE.auto_submit.elite_thresholds", config.model_dump())


def _check_rate_limit(max_per_hour: int) -> tuple[bool, str]:
    """Check if rate limit would be exceeded."""
    session = db.SessionLocal()
    try:
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
        recent_count = (
            session.query(models.SubmissionRecord)
            .filter(
                models.SubmissionRecord.created_at >= one_hour_ago,
                models.SubmissionRecord.status.in_(["submitted", "auto_submitted"]),
            )
            .count()
        )
        if recent_count >= max_per_hour:
            return False, f"Rate limit exceeded: {recent_count}/{max_per_hour} submissions in last hour"
        return True, ""
    finally:
        session.close()


def _get_quality_score(finding_id: int) -> float | None:
    """Get quality score for a finding."""
    try:
        from core.reports.quality.scorer import QualityScorer

        scorer = QualityScorer()
        score = scorer.score(finding_id)
        return score.score
    except Exception as e:
        logger.warning("Failed to get quality score for finding %s: %s", finding_id, e)
        return None


def _get_confidence_score(finding_id: int) -> float:
    """Extract confidence score from verdict."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding or not finding.endpoint_id:
            return 0.0

        verdict = (
            session.query(models.Verdict)
            .filter(models.Verdict.endpoint_id == finding.endpoint_id)
            .order_by(models.Verdict.id.desc())
            .first()
        )
        if not verdict or not verdict.confidence:
            return 0.0

        try:
            conf_data = json.loads(verdict.confidence) if isinstance(verdict.confidence, str) else verdict.confidence
            if isinstance(conf_data, dict):
                return float(conf_data.get("score", 0.0))
            return float(conf_data)
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0.0
    finally:
        session.close()


def _get_evidence_count(finding_id: int) -> int:
    """Count evidence records for a finding."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding or not finding.endpoint_id:
            return 0

        verdicts = session.query(models.Verdict).filter(models.Verdict.endpoint_id == finding.endpoint_id).all()
        if not verdicts:
            return 0

        verdict_ids = [v.id for v in verdicts]
        return session.query(models.Evidence).filter(models.Evidence.verdict_id.in_(verdict_ids)).count()
    finally:
        session.close()


def _check_reproduction_steps(finding_id: int) -> bool:
    """Check if finding has clear reproduction steps."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding:
            return False

        # Check description for reproduction indicators
        desc = finding.description or ""
        notes = finding.notes or ""
        combined = (desc + " " + notes).lower()

        # Look for reproduction keywords
        repro_keywords = ["steps to reproduce", "reproduction", "steps:", "1.", "first,", "to reproduce"]
        has_keyword = any(keyword in combined for keyword in repro_keywords)

        # Check minimum length
        has_length = len(desc) > 100 or len(notes) > 50

        return has_keyword or has_length
    finally:
        session.close()


def _check_elite_gate(finding_id: int, thresholds: EliteThresholdsConfig) -> tuple[bool, str]:
    """Check if finding passes elite quality gate."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding:
            return False, "Finding not found"

        # Check severity
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        finding_severity_level = severity_order.get(finding.severity or "medium", 2)
        min_severity_level = severity_order.get(thresholds.min_severity, 3)
        if finding_severity_level < min_severity_level:
            return False, f"Severity {finding.severity} below minimum {thresholds.min_severity}"

        # Check confidence
        confidence = _get_confidence_score(finding_id)
        if confidence < thresholds.min_confidence:
            return False, f"Confidence {confidence:.2f} below minimum {thresholds.min_confidence}"

        # Check quality score
        quality_score = _get_quality_score(finding_id)
        if quality_score is None or quality_score < thresholds.min_quality_score:
            return False, f"Quality score {quality_score} below minimum {thresholds.min_quality_score}"

        # Check evidence
        if thresholds.require_evidence_complete:
            evidence_count = _get_evidence_count(finding_id)
            if evidence_count < 2:
                return False, f"Insufficient evidence: {evidence_count} records"

        # Check reproduction steps
        if thresholds.require_reproduction_steps:
            has_repro = _check_reproduction_steps(finding_id)
            if not has_repro:
                return False, "Missing clear reproduction steps"

        return True, "Passes elite gate"
    finally:
        session.close()


def _get_target_name(target_id: int) -> str:
    """Get target name from target_id."""
    session = db.SessionLocal()
    try:
        target = session.query(models.Target).filter(models.Target.id == target_id).first()
        if target:
            return target.name or target.domain or ""
        return ""
    finally:
        session.close()


# ── API Endpoints ─────────────────────────────────────────────────


@router.get("/pending")
def get_pending_submissions() -> dict[str, Any]:
    """Get findings pending submission review."""
    session = db.SessionLocal()
    try:
        thresholds = _get_elite_thresholds()

        # Get confirmed findings not yet submitted
        findings = (
            session.query(models.Finding)
            .filter(models.Finding.status == "confirmed")
            .order_by(models.Finding.created_at.desc())
            .limit(50)
            .all()
        )

        pending = []
        for f in findings:
            # Check if already submitted
            submitted = (
                session.query(models.SubmissionRecord)
                .join(models.Report, models.SubmissionRecord.report_id == models.Report.id)
                .filter(models.Report.finding_id == f.id)
                .first()
            )
            if submitted:
                continue

            quality_score = _get_quality_score(f.id)
            confidence = _get_confidence_score(f.id)
            evidence_count = _get_evidence_count(f.id)

            passes_elite, rejection_reason = _check_elite_gate(f.id, thresholds)

            pending.append(
                PendingFinding(
                    id=f.id,
                    title=f.title,
                    severity=f.severity or "medium",
                    status=f.status,
                    quality_score=quality_score,
                    confidence=confidence,
                    evidence_count=evidence_count,
                    passes_elite_gate=passes_elite,
                    rejection_reason=rejection_reason if not passes_elite else None,
                    created_at=f.created_at.isoformat() if f.created_at else "",
                    target_name=_get_target_name(f.target_id),
                )
            )

        return {
            "total": len(pending),
            "elite_count": sum(1 for p in pending if p.passes_elite_gate),
            "findings": [p.model_dump() for p in pending],
            "thresholds": thresholds.model_dump(),
        }
    except Exception as e:
        logger.error("Failed to get pending submissions: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get pending submissions: {str(e)}") from e
    finally:
        session.close()


@router.post("/approve/{finding_id}")
def approve_submission(finding_id: int) -> dict[str, Any]:
    """Manually approve a finding for submission."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")

        thresholds = _get_elite_thresholds()

        # Check rate limit
        within_limit, rate_msg = _check_rate_limit(thresholds.max_submissions_per_hour)
        if not within_limit:
            raise HTTPException(status_code=429, detail=rate_msg)

        # Trigger auto-submit pipeline
        from cores.auto_submit.pipeline import get_auto_submit_pipeline

        pipeline = get_auto_submit_pipeline()
        result = pipeline.on_finding_confirmed(finding_id, {"manual_approval": True})

        logger.info("[AUTO-SUBMIT API] Manually approved finding %s: %s", finding_id, result)

        return {
            "success": True,
            "action": "manually_approved",
            "finding_id": finding_id,
            "message": "Finding approved for submission",
            "pipeline_result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to approve submission for finding %s: %s", finding_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to approve: {str(e)}") from e
    finally:
        session.close()


@router.post("/reject/{finding_id}")
def reject_submission(finding_id: int, reason: str = "") -> dict[str, Any]:
    """Reject a finding from submission."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")

        # Update finding status to indicate rejection
        finding.status = "rejected"
        finding.notes = (finding.notes or "") + f"\n\n[Auto-Submit Rejected] {reason}"
        session.commit()

        # Log rejection event
        from cores.events.event_bus import get_event_bus
        from cores.events.types import Events

        bus = get_event_bus()
        bus.publish(
            Events.AUTO_SUBMIT_FAILED,
            finding_id=finding_id,
            action="manual_rejection",
            reason=reason,
        )

        logger.info("[AUTO-SUBMIT API] Rejected finding %s: %s", finding_id, reason)

        return {
            "success": True,
            "action": "rejected",
            "finding_id": finding_id,
            "message": "Finding rejected from submission",
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error("Failed to reject submission for finding %s: %s", finding_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to reject: {str(e)}") from e
    finally:
        session.close()


@router.post("/config")
def update_config(config: EliteThresholdsConfig) -> dict[str, Any]:
    """Update elite quality gate configuration."""
    try:
        _save_elite_thresholds(config)
        logger.info("[AUTO-SUBMIT API] Updated elite thresholds: %s", config.model_dump())

        return {
            "status": "updated",
            "config": config.model_dump(),
        }
    except Exception as e:
        logger.error("Failed to update config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}") from e


@router.get("/config")
def get_config() -> dict[str, Any]:
    """Get current elite quality gate configuration."""
    try:
        config = _get_elite_thresholds()
        return config.model_dump()
    except Exception as e:
        logger.error("Failed to get config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}") from e


@router.get("/history")
def get_submission_history(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Get submission history."""
    session = db.SessionLocal()
    try:
        # Get submission records
        submissions = (
            session.query(models.SubmissionRecord)
            .order_by(models.SubmissionRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

        history = []
        for sub in submissions:
            # Get finding info
            report = session.query(models.Report).filter(models.Report.id == sub.report_id).first()
            if report:
                finding = session.query(models.Finding).filter(models.Finding.id == report.finding_id).first()
                if finding:
                    history.append(
                        SubmissionHistoryItem(
                            id=sub.id,
                            finding_id=finding.id,
                            finding_title=finding.title,
                            platform=sub.platform,
                            action=sub.status,
                            score=0.0,  # Would need to store score in SubmissionRecord
                            submission_id=sub.external_id,
                            error=None,
                            created_at=sub.created_at.isoformat() if sub.created_at else "",
                        )
                    )

        return {
            "total": len(history),
            "history": [h.model_dump() for h in history],
        }
    except Exception as e:
        logger.error("Failed to get submission history: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}") from e
    finally:
        session.close()


@router.post("/trigger/{finding_id}")
def trigger_elite_submission(finding_id: int) -> dict[str, Any]:
    """Trigger elite submission for a finding (bypasses approval check)."""
    session = db.SessionLocal()
    try:
        finding = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not finding:
            raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")

        thresholds = _get_elite_thresholds()

        # Check elite gate
        passes_elite, rejection_reason = _check_elite_gate(finding_id, thresholds)
        if not passes_elite:
            raise HTTPException(
                status_code=400,
                detail=f"Finding does not pass elite gate: {rejection_reason}",
            )

        # Check rate limit
        within_limit, rate_msg = _check_rate_limit(thresholds.max_submissions_per_hour)
        if not within_limit:
            raise HTTPException(status_code=429, detail=rate_msg)

        # Trigger auto-submit pipeline with elite bypass
        from cores.auto_submit.pipeline import get_auto_submit_pipeline

        pipeline = get_auto_submit_pipeline()
        result = pipeline.on_finding_confirmed(finding_id, {"elite_bypass": True})

        logger.info("[AUTO-SUBMIT API] Triggered elite submission for finding %s: %s", finding_id, result)

        return {
            "success": True,
            "action": "elite_submission",
            "finding_id": finding_id,
            "message": "Elite finding submitted",
            "pipeline_result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger elite submission for finding %s: %s", finding_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to trigger submission: {str(e)}") from e
    finally:
        session.close()
