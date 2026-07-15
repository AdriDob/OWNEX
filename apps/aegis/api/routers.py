"""AEGIS API — FastAPI routers for offensive security operations."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from apps.aegis.engines.recon import ReconEngine
from apps.aegis.engines.reporter import ReporterEngine
from apps.aegis.engines.scanner import ScannerEngine
from apps.aegis.models import AegisTarget, KnowHow, ScanReport, ScanResult, VulnFinding
from core.database.manager import get_db_manager

logger = logging.getLogger("orion.aegis.api")
router = APIRouter(prefix="/api/aegis", tags=["aegis"])


# ── Targets ──


@router.get("/targets")
async def list_targets(limit: int = 50, offset: int = 0):
    db = get_db_manager().get_session("aegis")
    try:
        targets = db.query(AegisTarget).order_by(AegisTarget.updated_at.desc()).offset(offset).limit(limit).all()
        total = db.query(AegisTarget).count()
        return {
            "targets": [
                {
                    "id": t.id,
                    "name": t.name,
                    "domain": t.domain,
                    "status": t.status,
                    "priority": t.priority,
                    "tags": t.tags,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in targets
            ],
            "total": total,
        }
    finally:
        db.close()


@router.get("/targets/active")
async def active_targets():
    db = get_db_manager().get_session("aegis")
    try:
        count = db.query(AegisTarget).filter(AegisTarget.status == "active").count()
        return {"count": count}
    finally:
        db.close()


@router.get("/targets/{target_id}")
async def get_target(target_id: int):
    db = get_db_manager().get_session("aegis")
    try:
        t = db.query(AegisTarget).filter(AegisTarget.id == target_id).first()
        if not t:
            return {"error": "target not found"}
        return {
            "id": t.id,
            "name": t.name,
            "domain": t.domain,
            "scope": t.scope,
            "status": t.status,
            "priority": t.priority,
            "tags": t.tags,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
    finally:
        db.close()


@router.post("/targets")
async def create_target(name: str, domain: str | None = None, scope: str | None = None):
    db = get_db_manager().get_session("aegis")
    try:
        t = AegisTarget(name=name, domain=domain, scope=scope)
        db.add(t)
        db.commit()
        db.refresh(t)
        return {"id": t.id, "name": t.name, "status": "created"}
    finally:
        db.close()


# ── Scans ──


@router.get("/scans")
async def list_scans(limit: int = 50, offset: int = 0):
    db = get_db_manager().get_session("aegis")
    try:
        scans = db.query(ScanResult).order_by(ScanResult.created_at.desc()).offset(offset).limit(limit).all()
        total = db.query(ScanResult).count()
        return {
            "scans": [
                {
                    "id": s.id,
                    "target_id": s.target_id,
                    "scan_type": s.scan_type,
                    "tool": s.tool,
                    "severity": s.severity,
                    "title": s.title,
                    "endpoint": s.endpoint,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in scans
            ],
            "total": total,
        }
    finally:
        db.close()


@router.get("/scans/today")
async def scans_today():
    db = get_db_manager().get_session("aegis")
    try:
        today = datetime.now(timezone.utc).date()
        count = db.query(ScanResult).filter(text("date(created_at) = date(:today)")).params(today=today).count()
        return {"count": count}
    finally:
        db.close()


@router.post("/scans/recon")
async def run_recon(target_id: int):
    engine = ReconEngine()
    result = await engine.run(target_id)
    return result


@router.post("/scans/full")
async def run_full_scan(target_id: int):
    engine = ScannerEngine()
    result = await engine.run_full(target_id)
    return result


# ── Findings ──


@router.get("/findings")
async def list_findings(limit: int = 50, offset: int = 0, severity: str | None = None):
    db = get_db_manager().get_session("aegis")
    try:
        q = db.query(VulnFinding)
        if severity:
            q = q.filter(VulnFinding.severity == severity)
        findings = q.order_by(VulnFinding.created_at.desc()).offset(offset).limit(limit).all()
        total = q.count()
        return {
            "findings": [
                {
                    "id": f.id,
                    "target_id": f.target_id,
                    "title": f.title,
                    "severity": f.severity,
                    "cvss": f.cvss,
                    "cve": f.cve,
                    "status": f.status,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in findings
            ],
            "total": total,
        }
    finally:
        db.close()


@router.get("/findings/open")
async def open_findings():
    db = get_db_manager().get_session("aegis")
    try:
        count = db.query(VulnFinding).filter(VulnFinding.status == "open").count()
        return {"count": count}
    finally:
        db.close()


# ── Reports ──


@router.get("/reports")
async def list_reports(limit: int = 20):
    db = get_db_manager().get_session("aegis")
    try:
        reports = db.query(ScanReport).order_by(ScanReport.created_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "target_id": r.target_id,
                "title": r.title,
                "format": r.format,
                "severity_counts": r.severity_counts,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]
    finally:
        db.close()


@router.post("/reports/generate")
async def generate_report(target_id: int, format: str = "markdown"):
    engine = ReporterEngine()
    result = await engine.generate(target_id, format)
    return result


# ── Knowledge ──


@router.get("/knowledge")
async def list_knowledge(category: str | None = None):
    db = get_db_manager().get_session("aegis")
    try:
        q = db.query(KnowHow)
        if category:
            q = q.filter(KnowHow.category == category)
        items = q.order_by(KnowHow.updated_at.desc()).all()
        return [
            {
                "id": k.id,
                "title": k.title,
                "category": k.category,
                "tags": k.tags,
                "source": k.source,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in items
        ]
    finally:
        db.close()


# ── Deep Study ──


@router.post("/deep-study/{target_id}")
async def deep_study_target(target_id: int):
    """Run AEGIS Deep Study Mode on a target — tech fingerprinting, hypotheses, playbooks, and COPILOT plan."""
    try:
        from apps.aegis.engines.deep_study import DeepStudyEngine
        from cores.tools.httpx import HttpxTool

        engine = DeepStudyEngine(httpx_tool=HttpxTool())
        result = await engine.run(target_id)
        return {
            "status": "ok",
            "study": {
                "target_name": result.target_name,
                "domain": result.domain,
                "score": result.score,
                "endpoints_analyzed": result.endpoints_analyzed,
                "technologies": result.technologies,
                "hypotheses": result.hypotheses[:10],
                "playbook_actions": result.playbook_actions,
                "attack_surfaces": result.attack_surfaces,
                "recommendations": result.recommendations,
                "summary": result.summary,
            },
        }
    except Exception as exc:
        logger.warning("[DEEP_STUDY] Error for target %d: %s", target_id, exc)
        return {"status": "error", "detail": str(exc)}


@router.get("/deep-study/{target_id}")
async def get_deep_study_meta(target_id: int):
    """Return metadata about what a deep study would analyze for a target."""
    from api.services.data_service import get_target as svc_get_target
    from api.services.data_service import list_endpoints

    target = svc_get_target(target_id)
    if not target:
        return {"status": "error", "detail": "Target not found"}
    endpoints, total = [], 0
    from contextlib import suppress

    with suppress(Exception):
        endpoints, total = list_endpoints(target_id, limit=5)
    return {
        "status": "ok",
        "target": {"name": target.get("name"), "domain": target.get("domain"), "id": target_id},
        "total_endpoints": total,
        "sample_endpoints": endpoints[:5],
        "note": "POST to /api/aegis/deep-study/{id} to run the full analysis",
    }


# ── Health ──


@router.get("/health")
async def aegis_health():
    db = get_db_manager().get_session("aegis")
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        db.close()
    return {"status": "ok", "db": db_ok, "timestamp": datetime.now(timezone.utc).isoformat()}
