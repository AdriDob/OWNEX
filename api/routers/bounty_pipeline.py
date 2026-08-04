"""Bounty Pipeline API — E2E autonomous bounty execution.

Endpoints:
- POST /api/bounty-pipeline/execute — run full bounty pipeline
- GET /api/bounty-pipeline/status — check pipeline status
- POST /api/bounty-pipeline/config — update pipeline configuration
"""

from __future__ import annotations

from logging import getLogger
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.autonomy.bounty_pipeline import get_bounty_pipeline

router = APIRouter(prefix="/api/bounty-pipeline", tags=["bounty-pipeline"])
logger = getLogger(__name__)


class BountyRequest(BaseModel):
    """Request model for bounty execution."""

    bounty_id: str = Field(..., description="Bounty ID from platform")
    repo: str = Field(..., description="GitHub repository (owner/repo)")
    issue_number: int = Field(..., description="Issue number")
    issue_url: str = Field(..., description="Full issue URL")
    title: str = Field(..., description="Issue title")
    description: str = Field(default="", description="Issue description")


class PipelineConfigRequest(BaseModel):
    """Request model for pipeline configuration."""

    auto_claim: bool = Field(default=True, description="Auto-claim bounty")
    auto_submit: bool = Field(default=False, description="Auto-submit PR (requires approval)")
    min_test_pass_rate: float = Field(default=0.8, ge=0.0, le=1.0)
    min_confidence_for_pr: float = Field(default=0.6, ge=0.0, le=1.0)
    max_iterations: int = Field(default=3, ge=1, le=10)
    cleanup_repo: bool = Field(default=True)


@router.post("/execute")
async def execute_bounty(request: BountyRequest) -> dict[str, Any]:
    """Execute full bounty pipeline end-to-end."""
    try:
        pipeline = get_bounty_pipeline()

        result = await pipeline.execute_bounty(
            bounty_id=request.bounty_id,
            repo=request.repo,
            issue_number=request.issue_number,
            issue_url=request.issue_url,
            title=request.title,
            description=request.description,
        )

        return {
            "success": result.success,
            "bounty_id": result.bounty_id,
            "platform": result.platform,
            "verdict": result.verdict,
            "feedback": result.feedback,
            "error": result.error,
            "total_duration_seconds": result.total_duration_seconds,
            "phases": result.phases,
            "repo_info": {
                "clone_success": result.repo_info.clone_success if result.repo_info else False,
                "language": result.repo_info.language if result.repo_info else None,
            }
            if result.repo_info
            else None,
            "issue_analysis": {
                "success": result.issue_analysis.success if result.issue_analysis else False,
                "estimated_reward": result.issue_analysis.estimated_reward if result.issue_analysis else 0,
            }
            if result.issue_analysis
            else None,
            "test_results": {
                "pass_rate": result.test_results.pass_rate if result.test_results else 0,
                "total_tests": result.test_results.total_tests if result.test_results else 0,
            }
            if result.test_results
            else None,
            "pr_result": {
                "success": result.pr_result.success if result.pr_result else False,
                "pr_url": result.pr_result.pr_url if result.pr_result else None,
            }
            if result.pr_result
            else None,
        }
    except Exception as e:
        logger.error("Bounty pipeline execution failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}") from e


@router.get("/status")
def get_pipeline_status() -> dict[str, Any]:
    """Get current pipeline configuration and status."""
    try:
        pipeline = get_bounty_pipeline()
        return {
            "initialized": pipeline is not None,
            "config": {
                "auto_claim": pipeline.config.auto_claim,
                "auto_submit": pipeline.config.auto_submit,
                "min_test_pass_rate": pipeline.config.min_test_pass_rate,
                "min_confidence_for_pr": pipeline.config.min_confidence_for_pr,
                "max_iterations": pipeline.config.max_iterations,
                "cleanup_repo": pipeline.config.cleanup_repo,
            },
        }
    except Exception as e:
        logger.error("Failed to get pipeline status: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}") from e


@router.post("/config")
def update_pipeline_config(request: PipelineConfigRequest) -> dict[str, Any]:
    """Update pipeline configuration."""
    try:
        pipeline = get_bounty_pipeline()

        # Update config
        pipeline.config.auto_claim = request.auto_claim
        pipeline.config.auto_submit = request.auto_submit
        pipeline.config.min_test_pass_rate = request.min_test_pass_rate
        pipeline.config.min_confidence_for_pr = request.min_confidence_for_pr
        pipeline.config.max_iterations = request.max_iterations
        pipeline.config.cleanup_repo = request.cleanup_repo

        logger.info(
            "Pipeline configuration updated: auto_claim=%s, auto_submit=%s", request.auto_claim, request.auto_submit
        )

        return {
            "status": "ok",
            "config": {
                "auto_claim": pipeline.config.auto_claim,
                "auto_submit": pipeline.config.auto_submit,
                "min_test_pass_rate": pipeline.config.min_test_pass_rate,
                "min_confidence_for_pr": pipeline.config.min_confidence_for_pr,
                "max_iterations": pipeline.config.max_iterations,
                "cleanup_repo": pipeline.config.cleanup_repo,
            },
        }
    except Exception as e:
        logger.error("Failed to update pipeline config: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}") from e
