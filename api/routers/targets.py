from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.schemas.models import PaginatedResponse, TargetSummaryOut
from api.services.data_service import create_target as svc_create_target
from api.services.data_service import get_target, list_targets

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get("/ev-ranking")
def ev_ranking(limit: int = Query(20, ge=1, le=100)):
    """Return targets ranked by Expected Value (USD/hour)."""
    from core.target_intelligence.prioritizer import TargetPrioritizer
    from database import db, models

    session = db.SessionLocal()
    try:
        targets = session.query(models.Target).all()
        intel_map: dict[int, Any] = {}
        for t in targets:
            from cores.targets.models import TargetIntel

            intel = session.query(TargetIntel).filter(TargetIntel.target_id == t.id).first()
            if intel:
                intel_map[t.id] = intel

        prioritizer = TargetPrioritizer()
        _, results = prioritizer.prioritize(targets, intel_map)

        ranked = []
        for r in results[:limit]:
            ranked.append(
                {
                    "target_id": r.target_id,
                    "target_name": r.target_name,
                    "expected_value": round(r.expected_value, 2),
                    "estimated_reward": round(r.estimated_reward, 2),
                    "acceptance_probability": round(r.acceptance_probability, 2),
                    "confidence": round(r.confidence, 2),
                    "priority_score": round(r.priority_score, 2),
                    "attack_plan": r.attack_plan.to_dict() if r.attack_plan else None,
                }
            )

        return {
            "ranked": ranked,
            "total_targets": len(targets),
        }
    finally:
        session.close()


class ScanTriggerRequest(BaseModel):
    mode: str = "quick"


class TargetCreate(BaseModel):
    name: str
    domain: str | None = None
    mode: str | None = "FAST"


@router.post("")
def create_target(body: TargetCreate):
    result = svc_create_target(name=body.name, domain=body.domain)
    # Notify COPILOT for engagement plan
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        bus.publish(
            "target:created",
            {
                "id": result.get("id"),
                "name": result.get("name", body.name),
                "domain": result.get("domain", body.domain),
            },
        )
    except Exception:
        pass
    return result


@router.get("", response_model=PaginatedResponse)
def get_targets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_targets(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/{target_id}", response_model=TargetSummaryOut)
def get_target_detail(target_id: int):
    t = get_target(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    return t


@router.post("/{target_id}/scan")
async def trigger_target_scan(target_id: int, body: ScanTriggerRequest):
    from cores.orchestrator.scan_service import launch_scan
    from database import db

    t = get_target(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    session = db.SessionLocal()
    try:
        result = await launch_scan(
            target_name=t["name"],
            target_domain=t.get("domain", ""),
            target_mode=body.mode.upper(),
            session=session,
        )
        return result
    finally:
        session.close()


@router.get("/{target_id}/summary")
def get_target_summary(target_id: int):
    from database import db, models

    t = get_target(target_id)
    if not t:
        raise HTTPException(status_code=404, detail="Target not found")
    from cores.engine.unified_classifier import classify as unified_classify
    from cores.engine.unified_scoring import score_target as unified_score_target

    session = db.SessionLocal()
    try:
        endpoints_raw = session.query(models.Endpoint).filter(models.Endpoint.target_id == target_id).all()
    finally:
        session.close()
    entries = []
    has_api = False
    multi_tenant = False
    has_admin = False
    has_graphql = False
    for ep in endpoints_raw:
        params = ep.parsed_params if hasattr(ep, "parsed_params") else {}
        metadata = unified_classify(ep.path, ep.method, params)
        labels = metadata.get("labels", [])
        entries.append({"path": ep.path, "method": ep.method, "labels": labels})
        if not has_api and "api" in labels:
            has_api = True
        if not multi_tenant and ("org" in labels or "tenant" in labels):
            multi_tenant = True
        if not has_admin and "admin" in labels:
            has_admin = True
        if not has_graphql and "graphql" in labels:
            has_graphql = True
    sc = unified_score_target(
        {
            "is_saas": bool(t.get("domain")),
            "has_api": has_api,
            "multi_tenant": multi_tenant,
            "has_admin": has_admin,
            "has_graphql": has_graphql,
        }
    )
    return {"target": t, "endpoints": entries, "score": sc}
