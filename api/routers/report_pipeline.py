"""Report Pipeline API — top daily/weekly reports, generate, edit, submit manually."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import PlainTextResponse

from core.report_pipeline import get_pipeline
from database.db import SessionLocal

logger = logging.getLogger("ownex.api.report_pipeline")

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/pipeline/daily")
def get_daily_top(limit: int = Query(7, ge=1, le=20)):
    """Top N reports ready today (last 24h)."""
    pipeline = get_pipeline()
    candidates = pipeline.get_daily_top(limit)
    return {
        "period": "daily",
        "hours_back": 24,
        "count": len(candidates),
        "candidates": [_candidate_to_dict(c) for c in candidates],
    }


@router.get("/pipeline/weekly")
def get_weekly_top(limit: int = Query(15, ge=1, le=50)):
    """Top N reports ready this week (last 168h)."""
    pipeline = get_pipeline()
    candidates = pipeline.get_weekly_top(limit)
    return {
        "period": "weekly",
        "hours_back": 168,
        "count": len(candidates),
        "candidates": [_candidate_to_dict(c) for c in candidates],
    }


@router.post("/pipeline/generate/{finding_id}")
def generate_report(finding_id: int):
    """Generate complete markdown report for a finding."""
    pipeline = get_pipeline()
    candidates = pipeline.get_eligible_findings()
    candidate = next((c for c in candidates if c.finding_id == finding_id), None)
    if not candidate:
        raise HTTPException(status_code=404, detail="Finding not eligible or not found")

    report = pipeline.generate_report(candidate)
    return {
        "status": "generated",
        "stage": report.stage,
        "finding_id": finding_id,
        "file_path": report.file_path,
        "markdown": report.markdown,
        "json_data": report.json_data,
        "submit_url": pipeline.get_submission_url(candidate.platform, candidate.platform_url),
    }


@router.get("/pipeline/{finding_id}/download")
def download_report(finding_id: int, format: str = Query("markdown", pattern="^(markdown|json)$")):
    """Download generated report as markdown or JSON."""
    pipeline = get_pipeline()
    candidates = pipeline.get_eligible_findings()
    candidate = next((c for c in candidates if c.finding_id == finding_id), None)
    if not candidate:
        raise HTTPException(status_code=404, detail="Finding not found")

    report = pipeline.generate_report(candidate)

    if format == "json":
        return report.json_data

    return PlainTextResponse(
        report.markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=report_{finding_id}.md"},
    )


@router.post("/pipeline/{finding_id}/edit")
def edit_report(
    finding_id: int,
    body: dict[str, Any] = Body(...),
):
    """Save edited report (user reviewed/updated markdown)."""
    pipeline = get_pipeline()
    markdown = body.get("markdown", "")
    if not markdown:
        raise HTTPException(status_code=400, detail="markdown field required")

    report = pipeline.mark_ready(finding_id, edited_markdown=markdown)
    if not report:
        raise HTTPException(status_code=404, detail="No draft found for finding")

    return {
        "status": "ready",
        "stage": report.stage,
        "finding_id": finding_id,
        "file_path": report.file_path,
        "submit_url": pipeline.get_submission_url(report.candidate.platform, report.candidate.platform_url),
    }


@router.get("/pipeline/ready")
def get_ready_reports():
    """List all reports marked ready for manual submission."""
    pipeline = get_pipeline()
    reports = pipeline.get_ready_reports()
    return {
        "count": len(reports),
        "reports": [
            {
                "finding_id": r.candidate.finding_id,
                "title": r.candidate.title,
                "severity": r.candidate.severity,
                "program": r.candidate.program_name,
                "platform": r.candidate.platform,
                "submit_url": pipeline.get_submission_url(r.candidate.platform, r.candidate.platform_url),
                "estimated_reward": r.candidate.estimated_reward,
                "evh": r.candidate.evh,
                "file_path": r.file_path,
                "edited_at": r.edited_at,
            }
            for r in reports
        ],
    }


@router.get("/pipeline/{finding_id}/submit-url")
def get_submit_url(finding_id: int):
    """Get the platform submission URL for manual submit button."""
    pipeline = get_pipeline()
    candidates = pipeline.get_eligible_findings()
    candidate = next((c for c in candidates if c.finding_id == finding_id), None)
    if not candidate:
        raise HTTPException(status_code=404, detail="Finding not found")

    return {
        "finding_id": finding_id,
        "platform": candidate.platform,
        "submit_url": pipeline.get_submission_url(candidate.platform, candidate.platform_url),
        "program_url": candidate.platform_url,
    }


@router.post("/pipeline/{finding_id}/mark-submitted")
def mark_submitted(finding_id: int, body: dict[str, Any] = Body(...)):
    """Mark report as manually submitted (after user clicks platform link and submits)."""
    external_id = body.get("external_id", "")
    platform = body.get("platform", "")

    db = SessionLocal()
    try:
        from database.models import Report, SubmissionRecord

        # Find the report
        report = db.query(Report).filter(Report.finding_ids.contains(str(finding_id))).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        report.status = "submitted"
        db.flush()

        submission = SubmissionRecord(
            report_id=report.id,
            platform=platform,
            external_id=external_id,
            status="submitted",
        )
        db.add(submission)
        db.flush()
        db.commit()

        return {"status": "submitted", "submission_id": submission.id, "report_id": report.id}
    except Exception as exc:
        db.rollback()
        logger.exception("mark_submitted failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


def _candidate_to_dict(c) -> dict[str, Any]:
    return {
        "finding_id": c.finding_id,
        "title": c.title,
        "severity": c.severity,
        "vulnerability_type": c.vulnerability_type,
        "target": c.target_name,
        "domain": c.target_domain,
        "program": c.program_name,
        "platform": c.platform,
        "platform_url": c.platform_url,
        "cvss": c.cvss_score,
        "evh": c.evh,
        "confidence": c.confidence,
        "estimated_reward": c.estimated_reward,
        "score": c.score,
        "discovered_at": c.discovered_at,
    }
