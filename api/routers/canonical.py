"""
api.routers.canonical — Canonical API endpoints that return official Bundles.

All endpoints consume from the intelligence layer and return artifacts.
No business logic — pure presentation of canonical data.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from cores.intelligence.unified_orchestrator import get_orchestrator

LOG = logging.getLogger("ownex.api.canonical")

router = APIRouter(prefix="/api/canonical", tags=["canonical"])


def _get_artifact(name: str):
    orch = get_orchestrator()
    artifact = orch.get(name)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"{name} not available. Run a pipeline first.")
    return artifact


@router.get("/pipeline")
async def get_pipeline():
    return _get_artifact("PipelineArtifact")


@router.get("/evidence")
async def get_evidence():
    return _get_artifact("EvidenceGraphArtifact")


@router.get("/quickwins")
async def get_quick_wins():
    return _get_artifact("QuickWinsArtifact")


@router.get("/screenshots")
async def get_screenshots():
    return _get_artifact("ScreenshotArtifact")


@router.get("/differential")
async def get_differential():
    return _get_artifact("DifferentialArtifact")


@router.get("/insights")
async def get_insights():
    return _get_artifact("AIInsightArtifact")


@router.get("/execution")
async def get_execution():
    return _get_artifact("ExecutionPlanArtifact")


@router.get("/attack-surface")
async def get_attack_surface():
    return _get_artifact("AttackSurfaceArtifact")


@router.get("/roi")
async def get_roi():
    return _get_artifact("ROIArtifact")


@router.get("/hypotheses")
async def get_hypotheses():
    return _get_artifact("HypothesisArtifact")


@router.get("/artifacts")
async def list_artifacts():
    orch = get_orchestrator()
    stats = orch.stats()
    return {
        "available": stats.get("artifacts_available", []),
        "execution_order": stats.get("dependency_graph", {}).get("execution_order", []),
        "metrics": stats.get("metrics", {}),
    }


@router.get("/events")
async def get_events(
    event_type: str | None = Query(None, description="Filter by event type"),
):
    from cores.intelligence.event_system import get_event_system
    es = get_event_system()
    return {"events": es.get_events(event_type)}


@router.get("/metrics")
async def get_metrics():
    orch = get_orchestrator()
    return {"metrics": orch.stats().get("metrics", {})}


@router.get("/anti-drift")
async def get_anti_drift_report():
    from cores.intelligence.anti_drift import get_enforcer
    enforcer = get_enforcer()
    return enforcer.report()
