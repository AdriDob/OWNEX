"""Universal Discovery API — find, import, and query programs and assets from any source.

Extends the existing discovery router with program import, asset query,
and Knowledge Graph integration.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Reuse the get_db dependency from economic router
from api.routers.economic import get_db
from core.discovery.importer import bulk_import, import_program

logger = logging.getLogger("ownex.api.discovery_universal")

router = APIRouter(prefix="/api/discovery", tags=["discovery_universal"])


class ProgramImportRequest(BaseModel):
    name: str
    platform: str
    program_url: str = ""
    description: str = ""
    domains: list[str] = []
    wildcards: list[str] = []
    technologies: list[str] = []
    estimated_payout: float = 0.0
    raw_payout_range: str = ""
    scope_url: str = ""
    source: str = ""
    confidence: float = 0.8


class BulkImportRequest(BaseModel):
    programs: list[ProgramImportRequest]


@router.post("/programs/import")
def import_single_program(body: ProgramImportRequest, db: Any = Depends(get_db)):
    """Import a single program from scraped data."""
    result = import_program(body.model_dump(), session=db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/programs/import-bulk")
def import_bulk_programs(body: BulkImportRequest, db: Any = Depends(get_db)):
    """Import multiple programs in one transaction."""
    dicts = [p.model_dump() for p in body.programs]
    results = bulk_import(dicts)
    return {"imported": len(results), "results": results}


@router.get("/programs")
def list_programs(
    platform: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Any = Depends(get_db),
):
    """List all programs in the database with stats."""
    from database.models_economic import Program as ProgramModel

    q = db.query(ProgramModel)
    if platform:
        q = q.filter(ProgramModel.platform == platform)
    if status:
        q = q.filter(ProgramModel.status == status)
    total = q.count()
    items = q.order_by(ProgramModel.orion_score.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "name": p.name,
                "platform": p.platform,
                "status": p.status,
                "program_url": p.program_url,
                "orion_score": p.orion_score or 0.0,
                "total_reports": p.total_reports or 0,
                "confirmed_reports": p.confirmed_reports or 0,
                "total_earned": p.total_earned or 0.0,
                "technologies": p.technologies or "",
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in items
        ],
    }


@router.get("/programs/{program_id}/assets")
def list_program_assets(
    program_id: int,
    asset_type: str | None = Query(None),
    db: Any = Depends(get_db),
):
    """List all assets for a program."""
    from database.models_assets import Asset as AssetModel
    from database.models_economic import Program as ProgramModel

    program = db.query(ProgramModel).filter(ProgramModel.id == program_id).first()
    if not program:
        raise HTTPException(404, "Program not found")

    q = db.query(AssetModel).filter(AssetModel.program_id == program_id)
    if asset_type:
        q = q.filter(AssetModel.asset_type == asset_type)
    assets = q.order_by(AssetModel.asset_type, AssetModel.value).all()
    return {
        "program_id": program_id,
        "program_name": program.name,
        "total": len(assets),
        "assets": [
            {
                "id": a.id,
                "asset_type": a.asset_type,
                "value": a.value,
                "protocol": a.protocol,
                "port": a.port,
                "is_active": a.is_active,
                "is_in_scope": a.is_in_scope,
                "source": a.source,
                "confidence": a.confidence,
                "discovered_at": a.discovered_at.isoformat() if a.discovered_at else None,
            }
            for a in assets
        ],
    }


@router.get("/programs/stats")
def program_stats(db: Any = Depends(get_db)):
    """Aggregate program and asset statistics."""
    from database.models_assets import Asset as AssetModel
    from database.models_economic import Program as ProgramModel

    total_programs = db.query(ProgramModel).count()
    by_platform = dict(db.query(ProgramModel.platform, ProgramModel.id.count()).group_by(ProgramModel.platform).all())
    total_assets = db.query(AssetModel).count()
    by_asset_type = dict(db.query(AssetModel.asset_type, AssetModel.id.count()).group_by(AssetModel.asset_type).all())
    total_domains = db.query(AssetModel).filter(AssetModel.asset_type == "domain").count()
    total_wildcards = db.query(AssetModel).filter(AssetModel.asset_type == "wildcard").count()

    return {
        "programs": {
            "total": total_programs,
            "by_platform": by_platform,
        },
        "assets": {
            "total": total_assets,
            "by_type": by_asset_type,
            "domains": total_domains,
            "wildcards": total_wildcards,
        },
    }
