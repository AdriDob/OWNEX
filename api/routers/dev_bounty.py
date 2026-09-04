"""API Router for Dev Bounty Pipeline."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.autonomy.dev_bounty_pipeline import (
    DevBountyPipelineConfig,
    get_dev_bounty_pipeline,
)

router = APIRouter(prefix="/dev-bounty", tags=["dev-bounty"])


class DevBountyExecuteRequest(BaseModel):
    """Request to execute a dev bounty pipeline."""

    bounty_id: str = Field(..., description="Unique bounty identifier")
    platform: str = Field(..., description="Platform: freelancer, opire, issuehunt, mindrift, outlier")
    repo_url: str = Field(..., description="Repository URL (GitHub/GitLab)")
    issue_number: int = Field(..., description="Issue/PR number")
    issue_url: str = Field(..., description="Full issue URL")
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Issue description/body")


class DevBountyConfigRequest(BaseModel):
    """Request to update pipeline configuration."""

    clone_timeout: int | None = None
    analysis_timeout: int | None = None
    generation_timeout: int | None = None
    test_timeout: int | None = None
    pr_timeout: int | None = None
    submit_timeout: int | None = None
    min_test_pass_rate: float | None = None
    min_confidence_for_pr: float | None = None
    max_iterations: int | None = None
    freelancer_token: str | None = None
    opire_token: str | None = None
    issuehunt_token: str | None = None
    mindrift_token: str | None = None
    outlier_token: str | None = None
    auto_submit: bool | None = None
    cleanup_repo: bool | None = None


class DevBountyResponse(BaseModel):
    """Response from dev bounty pipeline execution."""

    success: bool
    bounty_id: str
    platform: str
    verdict: str
    feedback: str
    total_duration_seconds: float
    phases: dict[str, float]
    error: str | None = None
    repo_info: dict | None = None
    issue_analysis: dict | None = None
    generation_plan: dict | None = None
    test_results: dict | None = None
    pr_result: dict | None = None
    submit_result: dict | None = None


@router.post("/execute", response_model=DevBountyResponse)
async def execute_dev_bounty(request: DevBountyExecuteRequest) -> DevBountyResponse:
    """Execute full dev bounty pipeline end-to-end."""
    pipeline = get_dev_bounty_pipeline()

    result = await pipeline.execute_dev_bounty(
        bounty_id=request.bounty_id,
        platform=request.platform,
        repo_url=request.repo_url,
        issue_number=request.issue_number,
        issue_url=request.issue_url,
        title=request.title,
        description=request.description,
    )

    return DevBountyResponse(
        success=result.success,
        bounty_id=result.bounty_id,
        platform=result.platform,
        verdict=result.verdict,
        feedback=result.feedback,
        total_duration_seconds=result.total_duration_seconds,
        phases=result.phases,
        error=result.error,
        repo_info={"path": str(result.repo_info.path), "language": result.repo_info.language}
        if result.repo_info
        else None,
        issue_analysis={
            "issue_id": result.issue_analysis.issue_id,
            "title": result.issue_analysis.title,
            "issue_type": result.issue_analysis.issue_type,
            "severity": result.issue_analysis.severity,
            "confidence": result.issue_analysis.confidence,
        }
        if result.issue_analysis
        else None,
        generation_plan={
            "estimated_confidence": result.generation_plan.estimated_confidence,
            "changes_count": len(result.generation_plan.changes),
            "summary": result.generation_plan.summary,
        }
        if result.generation_plan
        else None,
        test_results={
            "overall_success": result.test_results.overall_success,
            "language": result.test_results.language,
            "passed": result.test_results.best_result.passed if result.test_results.best_result else 0,
            "failed": result.test_results.best_result.failed if result.test_results.best_result else 0,
            "total_duration": result.test_results.total_duration,
        }
        if result.test_results
        else None,
        pr_result={
            "success": result.pr_result.success,
            "pr_url": result.pr_result.pr_url,
            "pr_number": result.pr_result.pr_number,
            "branch_name": result.pr_result.branch_name,
        }
        if result.pr_result
        else None,
        submit_result={
            "success": result.submit_result.success,
            "action": result.submit_result.action,
            "target": result.submit_result.target,
            "message": result.submit_result.message,
        }
        if result.submit_result
        else None,
    )


@router.get("/config")
async def get_config() -> DevBountyPipelineConfig:
    """Get current pipeline configuration."""
    pipeline = get_dev_bounty_pipeline()
    return pipeline.config


@router.put("/config")
async def update_config(request: DevBountyConfigRequest) -> DevBountyPipelineConfig:
    """Update pipeline configuration."""
    pipeline = get_dev_bounty_pipeline()

    # Update only provided fields
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(pipeline.config, field, value)

    return pipeline.config


@router.get("/executors")
async def list_executors() -> dict:
    """List available executors."""
    pipeline = get_dev_bounty_pipeline()
    return {"executors": {name: {"platform": name} for name in pipeline.executors.keys()}}


@router.get("/health")
async def health() -> dict:
    """Health check for dev bounty pipeline."""
    pipeline = get_dev_bounty_pipeline()
    return {
        "status": "ok",
        "name": "dev_bounty_pipeline",
        "executors_count": len(pipeline.executors),
        "executors": list(pipeline.executors.keys()),
    }
