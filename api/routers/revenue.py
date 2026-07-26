"""Revenue Pipeline API — finding → evidence → report → platform → payout."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.revenue.pipeline import RevenuePipeline, register_revenue_capabilities

logger = logging.getLogger("cateye.api.revenue")

router = APIRouter(prefix="/api/revenue", tags=["revenue"])

_pipeline = RevenuePipeline()

# Register capabilities on module load so COPILOT discovers them
register_revenue_capabilities()


class SubmitReportRequest(BaseModel):
    finding_id: int
    platform: str = Field(..., pattern=r"^(hackerone|bugcrowd|intigriti|yeswehack|synack)$")
    program: str = ""
    api_key: str = ""
    evidence: dict[str, Any] | None = None


class RecordPayoutRequest(BaseModel):
    platform: str = Field(..., pattern=r"^(hackerone|bugcrowd|intigriti|yeswehack|synack)$")
    amount: float = Field(..., gt=0)
    currency: str = "USD"
    program: str = ""
    external_id: str = ""
    submission_record_id: int | None = None


@router.post("/submit")
def submit_report(body: SubmitReportRequest):
    """Submit a finding as a report to a bug bounty platform."""
    result = _pipeline.submit_report(
        finding_id=body.finding_id,
        platform_id=body.platform,
        program=body.program,
        evidence=body.evidence,
        api_key=body.api_key,
    )
    if not result.success and not result.report_id:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "success": result.success,
        "submission_id": result.submission_id,
        "report_id": result.report_id,
        "external_id": result.external_id,
        "url": result.url,
        "status": result.status,
        "error": result.error,
    }


@router.get("/submissions")
def list_submissions(
    status: str | None = Query(None),
    platform: str | None = Query(None, pattern=r"^(hackerone|bugcrowd|intigriti|yeswehack|synack)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """List submission records with optional filters."""
    return _pipeline.list_submissions(status=status, platform=platform, limit=limit)


@router.get("/submissions/{submission_id}")
def get_submission_status(submission_id: int, api_key: str = ""):
    """Check external status of a submission on its platform."""
    result = _pipeline.check_submission_status(submission_id, api_key)
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)
    return {
        "submission_id": result.submission_id,
        "status": result.status,
        "error": result.error,
    }


@router.post("/sync/{platform}")
def sync_payouts(
    platform: str,
    api_key: str = "",
):
    """Sync earnings from a platform and record payouts."""
    results = _pipeline.sync_platform_payouts(platform, api_key)
    return {
        "platform": platform,
        "results": [
            {
                "success": r.success,
                "payout_id": r.payout_id,
                "amount": r.amount,
                "currency": r.currency,
                "error": r.error,
            }
            for r in results
        ],
    }


@router.post("/payouts")
def record_payout(body: RecordPayoutRequest):
    """Record a single payout manually."""
    result = _pipeline.record_payout(
        platform=body.platform,
        amount=body.amount,
        currency=body.currency,
        program=body.program,
        external_id=body.external_id,
        submission_record_id=body.submission_record_id,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "success": result.success,
        "payout_id": result.payout_id,
        "amount": result.amount,
        "currency": result.currency,
    }


@router.get("/summary")
def revenue_summary():
    """Aggregate revenue statistics across all platforms."""
    return _pipeline.revenue_summary()


@router.get("/capital-dashboard")
def capital_dashboard():
    """Unified Capital Dashboard — capital, pipeline, targets, hot targets, program ranking."""
    from core.revenue.metrics import RevenueMetrics

    return RevenueMetrics().capital_dashboard()
