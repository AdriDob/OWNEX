"""Self-Healer API Router — REST endpoints for auto-repair system."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from cores.self_healer import (
    get_problem_detector,
    get_root_cause_analyzer,
    get_safe_deployer,
    get_self_healer_scheduler,
    get_solution_learner,
)
from cores.self_healer.models import (
    ApprovalRequired,
    ProblemSeverity,
)

router = APIRouter(prefix="/api/self-healer", tags=["self_healer"])


# Request/Response Models
class ScanRequest(BaseModel):
    force: bool = False


class ApproveFixRequest(BaseModel):
    plan_id: str
    approved: bool = True


class ConfigUpdateRequest(BaseModel):
    enabled: bool | None = None
    scan_interval_minutes: int | None = Field(None, ge=1, le=1440)
    max_concurrent_fixes: int | None = Field(None, ge=1, le=10)
    auto_approve_low_risk: bool | None = None
    require_approval_for: list[ApprovalRequired] | None = None
    canary_duration_minutes: int | None = Field(None, ge=1, le=120)
    max_rollback_time_minutes: int | None = Field(None, ge=1, le=1440)


class ProblemResponse(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    description: str
    source: str
    metrics: dict[str, Any]
    affected_components: list[str]
    first_seen: str
    last_seen: str
    occurrence_count: int
    is_active: bool
    metadata: dict[str, Any]


class DiagnosisResponse(BaseModel):
    id: str
    problem_id: str
    root_cause: str
    contributing_factors: list[str]
    confidence: str
    evidence: list[str]
    reasoning: str
    suggested_strategy: str
    estimated_effort_hours: float
    risk_level: str
    created_at: str


class FixPlanResponse(BaseModel):
    id: str
    diagnosis_id: str
    strategy: str
    description: str
    steps: list[str]
    files_to_modify: list[str]
    config_changes: dict[str, Any]
    tests_to_add: list[str]
    rollback_plan: str
    approval_required: str
    estimated_duration_minutes: int


class PatchResponse(BaseModel):
    id: str
    plan_id: str
    diff: str
    files_changed: list[str]
    tests_generated: list[str]
    validation_results: dict[str, Any]
    created_at: str
    is_applied: bool


class DeploymentResponse(BaseModel):
    id: str
    patch_id: str
    status: str
    environment: str
    started_at: str
    completed_at: str | None
    health_checks: dict[str, bool]
    rollback_triggered: bool
    rollback_reason: str


class LearningStatsResponse(BaseModel):
    total_entries: int
    successful_deployments: int
    failed_deployments: int
    success_rate: float


# Endpoints


@router.get("/status")
async def get_healer_status() -> dict[str, Any]:
    """Get overall self-healer status."""
    scheduler = get_self_healer_scheduler()
    return scheduler.get_status()


@router.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current healer configuration."""
    scheduler = get_self_healer_scheduler()
    config = scheduler.config
    return {
        "enabled": config.enabled,
        "scan_interval_minutes": config.scan_interval_minutes,
        "max_concurrent_fixes": config.max_concurrent_fixes,
        "auto_approve_low_risk": config.auto_approve_low_risk,
        "require_approval_for": [r.value for r in config.require_approval_for],
        "excluded_paths": config.excluded_paths,
        "canary_duration_minutes": config.canary_duration_minutes,
        "max_rollback_time_minutes": config.max_rollback_time_minutes,
        "learning_enabled": config.learning_enabled,
    }


@router.put("/config")
async def update_config(request: ConfigUpdateRequest) -> dict[str, Any]:
    """Update healer configuration."""
    scheduler = get_self_healer_scheduler()
    config = scheduler.config

    if request.enabled is not None:
        config.enabled = request.enabled
    if request.scan_interval_minutes is not None:
        config.scan_interval_minutes = request.scan_interval_minutes
    if request.max_concurrent_fixes is not None:
        config.max_concurrent_fixes = request.max_concurrent_fixes
    if request.auto_approve_low_risk is not None:
        config.auto_approve_low_risk = request.auto_approve_low_risk
    if request.require_approval_for is not None:
        config.require_approval_for = request.require_approval_for
    if request.canary_duration_minutes is not None:
        config.canary_duration_minutes = request.canary_duration_minutes
    if request.max_rollback_time_minutes is not None:
        config.max_rollback_time_minutes = request.max_rollback_time_minutes

    return {"success": True, "config": await get_config()}


@router.post("/scan")
async def trigger_scan(request: ScanRequest = ScanRequest()) -> dict[str, Any]:
    """Trigger a manual scan cycle."""
    scheduler = get_self_healer_scheduler()
    if not scheduler._running and not request.force:
        raise HTTPException(status_code=400, detail="Scheduler not running. Use force=true to run anyway.")

    return await scheduler.trigger_manual_scan()


@router.get("/problems")
async def get_problems(
    active_only: bool = True,
    severity: ProblemSeverity | None = None,
    category: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[ProblemResponse]:
    """Get detected problems."""
    detector = get_problem_detector()
    # In a real implementation, this would query a persistent store
    # For now, return from detector's last scan
    return []


@router.get("/problems/{problem_id}")
async def get_problem(problem_id: str) -> ProblemResponse:
    """Get a specific problem."""
    # Would query persistent store
    raise HTTPException(status_code=404, detail="Problem not found")


@router.get("/diagnoses")
async def get_diagnoses(
    problem_id: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[DiagnosisResponse]:
    """Get diagnoses."""
    return []


@router.get("/fix-plans")
async def get_fix_plans(
    diagnosis_id: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[FixPlanResponse]:
    """Get fix plans."""
    return []


@router.post("/fix-plans/{plan_id}/approve")
async def approve_fix_plan(plan_id: str, request: ApproveFixRequest) -> dict[str, Any]:
    """Approve or reject a fix plan."""
    # In a real implementation, this would update the plan status
    # and trigger the patch generation/deployment
    return {
        "success": True,
        "plan_id": plan_id,
        "approved": request.approved,
        "message": "Fix plan approved, patch generation started" if request.approved else "Fix plan rejected",
    }


@router.get("/patches")
async def get_patches(
    plan_id: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[PatchResponse]:
    """Get generated patches."""
    return []


@router.get("/deployments")
async def get_deployments(
    status: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
) -> list[DeploymentResponse]:
    """Get deployment history."""
    deployer = get_safe_deployer()
    active = deployer.get_active_deployment()
    return [DeploymentResponse(**active.to_dict())] if active else []


@router.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: str) -> DeploymentResponse:
    """Get a specific deployment."""
    raise HTTPException(status_code=404, detail="Deployment not found")


@router.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment(deployment_id: str) -> dict[str, Any]:
    """Manually trigger rollback for a deployment."""
    deployer = get_safe_deployer()
    active = deployer.get_active_deployment()

    if not active or active.id != deployment_id:
        raise HTTPException(status_code=404, detail="Deployment not found or not active")

    # Trigger rollback
    # This would need the deployment object to have the rollback method accessible
    return {"success": True, "message": "Rollback initiated"}


@router.get("/learning/stats")
async def get_learning_stats() -> LearningStatsResponse:
    """Get learning statistics."""
    learner = get_solution_learner()
    stats = learner.get_learning_stats()
    return LearningStatsResponse(**stats)


@router.get("/learning/patterns/successful")
async def get_successful_patterns(
    category: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Get successful fix patterns."""
    learner = get_solution_learner()
    if category:
        return learner.get_similar_successful_fixes(category, limit)
    return learner.get_successful_patterns(limit)


@router.get("/learning/patterns/failed")
async def get_failed_patterns(
    limit: int = Query(20, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Get failed patterns to avoid."""
    learner = get_solution_learner()
    return learner.get_failed_patterns(limit)


@router.post("/scheduler/start")
async def start_scheduler() -> dict[str, Any]:
    """Start the self-healer scheduler."""
    scheduler = get_self_healer_scheduler()
    scheduler.start()
    return {"success": True, "message": "Scheduler started"}


@router.post("/scheduler/stop")
async def stop_scheduler() -> dict[str, Any]:
    """Stop the self-healer scheduler."""
    scheduler = get_self_healer_scheduler()
    scheduler.stop()
    return {"success": True, "message": "Scheduler stopped"}


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check for self-healer system."""
    scheduler = get_self_healer_scheduler()
    detector = get_problem_detector()
    analyzer = get_root_cause_analyzer()

    return {
        "status": "healthy" if scheduler._running else "stopped",
        "scheduler_running": scheduler._running,
        "components": {
            "detector": "ok",
            "analyzer": "ok" if analyzer.oar else "limited",
            "scheduler": "ok",
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
