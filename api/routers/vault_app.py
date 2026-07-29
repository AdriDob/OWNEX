"""Vault App API — Wealth/Finance platforms (CoinGecko, Firefly, Binance, DeFi Llama)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from database.db import SessionLocal
from database.models_cycles import CycleOpportunity, CycleSyncLog

router = APIRouter(prefix="/api/vault", tags=["vault"])

VAULT_PLATFORMS = ["coingecko", "firefly", "binance", "defillama"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/platforms")
def list_platforms():
    """List available Vault platforms."""
    return {"platforms": VAULT_PLATFORMS}


@router.get("/opportunities")
def list_opportunities(
    platform: str | None = Query(None),
    status: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(CycleOpportunity).filter(CycleOpportunity.cycle_slug == "vault")
    if platform:
        query = query.filter(CycleOpportunity.platform == platform)
    if status:
        query = query.filter(CycleOpportunity.status == status)

    order_fn = desc if sort_order == "desc" else asc
    query = query.order_by(order_fn(getattr(CycleOpportunity, sort_by, CycleOpportunity.created_at)))

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/sync-logs")
def list_sync_logs(
    platform: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(CycleSyncLog).filter(CycleSyncLog.cycle_slug == "vault")
    if platform:
        query = query.filter(CycleSyncLog.platform == platform)
    query = query.order_by(desc(CycleSyncLog.started_at))
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/sync")
def trigger_sync(platform: str | None = Query(None), db: Session = Depends(get_db)):
    """Trigger a sync for one or all Vault platforms."""
    platforms = [platform] if platform else VAULT_PLATFORMS
    logs = []
    for p in platforms:
        log = CycleSyncLog(cycle_slug="vault", platform=p, status="queued")
        db.add(log)
        logs.append(log)
    db.commit()
    return {
        "message": f"Queued sync for {len(platforms)} platform(s)",
        "sync_logs": [{"id": log.id, "platform": log.platform, "status": log.status} for log in logs],
    }


@router.patch("/opportunities/{opportunity_id}")
def update_opportunity_status(
    opportunity_id: int,
    status: str = Query(...),
    db: Session = Depends(get_db),
):
    opp = db.query(CycleOpportunity).filter(CycleOpportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opp.status = status
    opp.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"success": True, "status": opp.status}
