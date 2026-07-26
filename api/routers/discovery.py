"""Discovery router — bounty program discovery endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cores.bounty_scraper.changes import get_change_tracker
from cores.bounty_scraper.monitor import get_discovery_monitor
from cores.bounty_scraper.scraper import BountyScraper

logger = logging.getLogger("cateye.api.discovery")
router = APIRouter(prefix="/api/discovery", tags=["discovery"])

_scraper = BountyScraper()


class ImportRequest(BaseModel):
    auto_recon: bool = False


class ImportAllRequest(BaseModel):
    platform: str | None = None


class ScanDomainsRequest(BaseModel):
    domains: list[str] = []


@router.get("/programs")
def list_programs(
    platform: str | None = Query(None),
    source: str | None = Query(None),
    imported: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List discovered bounty programs."""
    programs = _scraper.get_programs() if hasattr(_scraper, "get_programs") else _scraper._programs
    filtered = list(programs)
    if platform:
        filtered = [p for p in filtered if p.platform == platform]
    if source:
        filtered = [p for p in filtered if hasattr(p, "source") and p.source == source]
    total = len(filtered)
    return {
        "programs": [
            {
                "name": p.name,
                "platform": p.platform,
                "source": getattr(p, "source", p.platform),
                "program_url": p.program_url,
                "has_rewards": p.has_rewards,
                "estimated_payout": p.estimated_payout,
                "is_new": p.is_new,
                "domains": p.domains,
            }
            for p in filtered[offset : offset + limit]
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/stats")
def discovery_stats():
    """Get discovery statistics."""
    monitor = get_discovery_monitor()
    programs = getattr(_scraper, "_programs", [])
    platforms: dict[str, int] = {}
    sources: dict[str, int] = {}
    for p in programs:
        platforms[p.platform] = platforms.get(p.platform, 0) + 1
        src = getattr(p, "source", p.platform)
        sources[src] = sources.get(src, 0) + 1
    return {
        "stats": {
            "total_discovered": len(programs),
            "by_platform": platforms,
            "by_source": sources,
        },
        "monitor": monitor.get_status(),
    }


@router.post("/scan")
async def run_discovery(body: ScanDomainsRequest | None = None):
    """Run all discovery sources now with change detection."""
    domains = body.domains if body else []
    programs, diff = _scraper.scrape_with_changes(domains=domains)
    return {
        "total": len(programs),
        "programs": [p.name for p in programs],
        "new_programs": len(diff.new_programs),
        "removed_programs": len(diff.removed_programs),
        "updated_programs": len(diff.updated_programs),
        "changes": {
            "new": [
                {"name": p.name, "platform": p.platform, "payout": p.estimated_payout} for p in diff.new_programs[:20]
            ],
            "updated": diff.updated_programs[:20],
        },
    }


@router.get("/changes")
def get_changes():
    """Get the latest discovery change diff."""
    tracker = get_change_tracker()
    return {
        "tracked_programs": tracker.get_known_count(),
        "tracker": tracker.to_dict(),
    }


@router.get("/programs/ranked")
def list_ranked_programs(
    platform: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List discovered programs ranked by estimated value."""
    programs = getattr(_scraper, "_programs", [])
    if platform:
        programs = [p for p in programs if p.platform == platform]
    ranked = _scraper.prioritize(programs)
    return {
        "ranked": [
            {
                "name": p.name,
                "platform": p.platform,
                "program_url": p.program_url,
                "estimated_payout": p.estimated_payout,
                "average_payout": p.estimated_payout,
                "is_new": p.is_new,
                "has_rewards": p.has_rewards,
                "technologies": p.technologies,
                "confidence": p.confidence,
            }
            for p in ranked[:limit]
        ],
        "total": len(ranked),
    }


@router.post("/programs/{program_url:path}/import")
async def import_program(program_url: str, body: ImportRequest | None = None):
    """Import a discovered program into the database."""
    from database import db, models

    session = db.SessionLocal()
    try:
        existing = session.query(models.Target).filter(models.Target.name == program_url).first()
        if existing:
            return {"success": True, "message": "Already imported"}
        target = models.Target(
            name=program_url,
            in_scope=True,
        )
        session.add(target)
        session.commit()
        return {"success": True, "target_id": target.id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(e)) from e
    finally:
        session.close()


@router.post("/import-all")
async def import_all_programs(body: ImportAllRequest | None = None):
    """Import all non-imported discovered programs."""
    programs = getattr(_scraper, "_programs", [])
    if body and body.platform:
        programs = [p for p in programs if p.platform == body.platform]
    from database import db, models

    session = db.SessionLocal()
    imported = 0
    try:
        for prog in programs:
            existing = session.query(models.Target).filter(models.Target.name == prog.program_url).first()
            if not existing:
                target = models.Target(name=prog.program_url, in_scope=True)
                session.add(target)
                imported += 1
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
    return {"imported": imported, "total": len(programs)}


@router.get("/monitor")
def monitor_status():
    """Get discovery monitor status."""
    monitor = get_discovery_monitor()
    return monitor.get_status()


@router.post("/monitor/start")
async def start_monitor():
    """Start the background discovery monitor."""
    monitor = get_discovery_monitor()
    await monitor.start()
    return {"status": "started"}


@router.post("/monitor/stop")
async def stop_monitor():
    """Stop the background discovery monitor."""
    monitor = get_discovery_monitor()
    await monitor.stop()
    return {"status": "stopped"}
