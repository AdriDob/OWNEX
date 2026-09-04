from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.evolution.analyze import get_analyze_engine
from core.evolution.engine import get_evolution_engine

logger = logging.getLogger("orion.api.evolution")

router = APIRouter(prefix="/api/evolution", tags=["evolution"])


# ── Metric events ───────────────────────────────────────


@router.get("/metrics/events")
def list_metric_events(
    module: str | None = Query(None, description="Filter by module"),
    event_type: str | None = Query(None, description="Filter by event type"),
    pipeline: str | None = Query(None, description="Filter by pipeline stage"),
    tool: str | None = Query(None, description="Filter by tool name"),
    status: str | None = Query(None, description="Filter by status"),
    target_id: int | None = Query(None, description="Filter by target ID"),
    since: str | None = Query(None, description="ISO datetime (inclusive)"),
    until: str | None = Query(None, description="ISO datetime (inclusive)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Query raw metric events with optional filters."""
    engine = get_evolution_engine()
    try:
        since_dt = datetime.fromisoformat(since) if since else None
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid 'since' format (use ISO 8601)") from None
    try:
        until_dt = datetime.fromisoformat(until) if until else None
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid 'until' format (use ISO 8601)") from None

    events = engine.query_events(
        module=module,
        event_type=event_type,
        pipeline=pipeline,
        tool=tool,
        status=status,
        target_id=target_id,
        since=since_dt,
        until=until_dt,
        limit=limit,
        offset=offset,
    )
    total = engine.count_events(
        module=module,
        event_type=event_type,
        pipeline=pipeline,
        tool=tool,
        status=status,
        target_id=target_id,
    )
    return {"items": events, "total": total, "limit": limit, "offset": offset}


@router.get("/metrics/summary")
def get_metric_summary(
    granularity: str = Query("daily", pattern="^(hourly|daily)$"),
    module: str | None = Query(None),
    limit: int = Query(30, ge=1, le=365),
):
    """Return pre-aggregated metric rollups."""
    engine = get_evolution_engine()
    return {
        "granularity": granularity,
        "items": engine.get_summary(granularity=granularity, module=module, limit=limit),
    }


@router.post("/analyze")
def run_analysis():
    """Execute the Analyze Engine full cycle (4 levels) and return results.

    This endpoint triggers an on-demand analysis.  The scheduler also runs
    this periodically.
    """
    engine = get_analyze_engine()
    results = engine.run_full_cycle()
    return {
        "status": "ok",
        "run_at": results.get("run_at"),
        "summary": {
            "event_count": results.get("level_1", {}).get("event_count", 0),
            "bottlenecks": len(results.get("level_2", {}).get("bottlenecks", [])),
            "patterns": len(results.get("level_3", {}).get("patterns", [])),
            "assets_created": results.get("level_4", {}).get("count", 0),
        },
    }


@router.get("/bottlenecks")
def list_bottlenecks(
    min_hours: float = Query(0.1, description="Minimum total hours to include"),
):
    """Return current bottleneck analysis (cached from last analyze run)."""
    engine = get_analyze_engine()
    results = engine.results
    bottlenecks = results.get("level_2", {}).get("bottlenecks", [])
    filtered = [b for b in bottlenecks if b.get("total_hours", 0) >= min_hours]
    return {
        "bottlenecks": filtered,
        "count": len(filtered),
        "run_at": results.get("run_at"),
        "window_days": results.get("window_days", 14),
    }


# ── Knowledge assets ────────────────────────────────────


@router.get("/knowledge")
def list_knowledge_assets(
    domain: str | None = Query(None, description="Filter by domain"),
    asset_type: str | None = Query(None, description="Filter by asset type"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List knowledge assets with optional filters."""
    engine = get_evolution_engine()
    items = engine.get_assets(domain=domain, asset_type=asset_type, status=status, limit=limit, offset=offset)
    return {"items": items, "total": len(items), "limit": limit, "offset": offset}


@router.get("/knowledge/{asset_id}")
def get_knowledge_asset(asset_id: int):
    """Get a single knowledge asset by ID."""
    engine = get_evolution_engine()
    asset = engine.get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Knowledge asset not found")
    return asset


@router.post("/knowledge")
def create_knowledge_asset(payload: dict[str, Any]):
    """Create a new knowledge asset."""
    required = ("asset_type", "domain", "title")
    missing = [f for f in required if f not in payload]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    valid_types = {
        "heuristic",
        "pattern",
        "rule",
        "statistic",
        "workflow",
        "benchmark",
        "template",
        "finding_pattern",
        "report_template",
        "optimization",
        "experiment",
        "research",
        "tool_config",
        "playbook",
    }
    if payload["asset_type"] not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid asset_type. Must be one of: {', '.join(sorted(valid_types))}",
        )

    valid_domains = {"cateye", "atlas", "odyssey", "hermes", "core", "cross"}
    if payload["domain"] not in valid_domains:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid domain. Must be one of: {', '.join(sorted(valid_domains))}",
        )

    engine = get_evolution_engine()
    asset_id = engine.create_asset(
        asset_type=payload["asset_type"],
        domain=payload["domain"],
        title=payload["title"],
        description=payload.get("description", ""),
        source=payload.get("source", "manual"),
        source_url=payload.get("source_url"),
        source_confidence=payload.get("source_confidence", 0.5),
        content=payload.get("content"),
        evidence=payload.get("evidence"),
        tags=payload.get("tags"),
    )
    if asset_id < 0:
        raise HTTPException(status_code=500, detail="Failed to create knowledge asset")
    return {"id": asset_id, "message": "Knowledge asset created"}


@router.patch("/knowledge/{asset_id}")
def update_knowledge_asset_status(
    asset_id: int,
    payload: dict[str, Any],
):
    """Update a knowledge asset's status."""
    engine = get_evolution_engine()
    status = payload.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Missing 'status' field")
    valid_statuses = {"draft", "hypothesis", "validated", "production", "deprecated"}
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )
    ok = engine.update_asset_status(
        asset_id,
        status,
        impact_score=payload.get("impact_score"),
        observation_count=payload.get("observation_count"),
        opportunity_cost_hours=payload.get("opportunity_cost_hours"),
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Knowledge asset not found")
    return {"message": f"Asset {asset_id} updated to '{status}'"}


@router.delete("/knowledge/{asset_id}")
def delete_knowledge_asset(asset_id: int):
    """Delete a knowledge asset."""
    engine = get_evolution_engine()
    ok = engine.delete_asset(asset_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Knowledge asset not found")
    return {"message": f"Asset {asset_id} deleted"}
