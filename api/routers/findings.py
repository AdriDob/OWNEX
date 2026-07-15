from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from api.schemas.models import PaginatedResponse
from api.services.data_service import create_finding as svc_create_finding
from api.services.data_service import list_findings
from database import db, models

logger = logging.getLogger("cateye.api.findings")

router = APIRouter(prefix="/api/findings", tags=["findings"])


class FindingCreate(BaseModel):
    target_id: int
    endpoint_id: int | None = None
    title: str
    severity: str | None = "medium"
    description: str | None = None


class StatusUpdate(BaseModel):
    status: str


class FindingUpdate(BaseModel):
    notes: str | None = None
    status: str | None = None


def _finding_to_dict(f) -> dict[str, Any]:
    return {
        "id": f.id,
        "target_id": f.target_id,
        "endpoint_id": f.endpoint_id,
        "title": f.title or f"Finding #{f.id}",
        "severity": f.severity or "medium",
        "description": f.description,
        "status": getattr(f, "status", "open"),
        "notes": getattr(f, "notes", "") or "",
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


@router.post("")
def create_finding(body: FindingCreate):
    try:
        result = svc_create_finding(
            target_id=body.target_id,
            title=body.title,
            severity=body.severity or "medium",
            description=body.description,
            endpoint_id=body.endpoint_id,
        )
        try:
            from cores.events.event_bus import get_event_bus

            bus = get_event_bus()
            bus.publish(
                "finding:created",
                {
                    "id": result.get("id"),
                    "title": body.title,
                    "severity": body.severity or "medium",
                    "target_id": body.target_id,
                },
            )
        except Exception:
            logger.exception("Failed to publish finding:created event")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("", response_model=PaginatedResponse)
def get_findings(
    target_id: int | None = Query(None, description="Filter by target ID"),
    endpoint_id: int | None = Query(None, description="Filter by endpoint ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("severity"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_findings(
        target_id=target_id,
        endpoint_id=endpoint_id,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/stats")
def get_findings_stats():
    """Return aggregate statistics for findings."""
    session = db.SessionLocal()
    try:
        total = session.query(models.Finding).count()
        severity_counts = {}
        for row in session.query(models.Finding.severity, db.func.count()).group_by(models.Finding.severity).all():
            severity_counts[row[0] or "unknown"] = row[1]
        new_24h = (
            session.query(models.Finding)
            .filter(models.Finding.created_at >= db.func.now() - db.text("INTERVAL '24 hours'"))
            .count()
        )
        return {
            "total": total,
            "by_severity": severity_counts,
            "new_24h": new_24h,
        }
    finally:
        session.close()


@router.get("/{finding_id}")
def get_finding(finding_id: int):
    """Return a single finding by ID."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        return _finding_to_dict(f)
    finally:
        session.close()


@router.put("/{finding_id}/status")
def update_finding_status(finding_id: int, body: StatusUpdate):
    """Update finding status (open/confirmed/rejected/in_progress)."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        old_status = f.status
        f.status = body.status
        session.commit()
        result = _finding_to_dict(f)
        if old_status != body.status:
            try:
                from cores.events.event_bus import get_event_bus

                bus = get_event_bus()
                bus.publish(
                    "finding:status_changed",
                    {
                        "id": finding_id,
                        "title": f.title,
                        "severity": f.severity,
                        "old_status": old_status,
                        "new_status": body.status,
                        "target_id": f.target_id,
                    },
                )
            except Exception:
                logger.exception("Failed to publish finding:status_changed event")
        return result
    finally:
        session.close()


@router.patch("/{finding_id}")
def update_finding(finding_id: int, body: FindingUpdate):
    """Update finding notes and/or status."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        if body.notes is not None:
            f.notes = body.notes
        if body.status is not None:
            old_status = getattr(f, "status", "")
            f.status = body.status
            if old_status != body.status:
                try:
                    from cores.events.event_bus import get_event_bus

                    bus = get_event_bus()
                    bus.publish(
                        "finding:status_changed",
                        {
                            "id": finding_id,
                            "title": f.title,
                            "severity": f.severity,
                            "old_status": old_status,
                            "new_status": body.status,
                            "target_id": f.target_id,
                        },
                    )
                except Exception:
                    logger.exception("Failed to publish finding:status_changed event")
        session.commit()
        return _finding_to_dict(f)
    finally:
        session.close()


@router.post("/{finding_id}/classification")
def classify_finding(finding_id: int) -> dict[str, Any]:
    """Run automated classification on a finding (simple rule-based)."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        desc = (f.description or "").lower()
        if any(kw in desc for kw in ["sql", "injection", "sqli"]):
            classification = "sqli"
        elif any(kw in desc for kw in ["xss", "cross-site", "script"]):
            classification = "xss"
        elif any(kw in desc for kw in ["csrf", "cross-site request"]):
            classification = "csrf"
        elif any(kw in desc for kw in ["rce", "remote code", "command injection"]):
            classification = "rce"
        elif any(kw in desc for kw in ["ssrf", "server-side request"]):
            classification = "ssrf"
        elif any(kw in desc for kw in ["idor", "insecure direct"]):
            classification = "idor"
        elif any(kw in desc for kw in ["open redirect", "redirect"]):
            classification = "open-redirect"
        else:
            classification = "other"
        return {"finding_id": finding_id, "classification": classification}
    finally:
        session.close()


@router.get("/{finding_id}/evidence")
def get_finding_evidence(finding_id: int):
    """Return evidence items associated with a finding."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        evidence = (
            session.query(models.Evidence).filter(models.Evidence.finding_id == finding_id).all()
            if hasattr(models.Evidence, "finding_id")
            else []
        )
        return {
            "items": [
                {
                    "id": e.id,
                    "response_status": getattr(e, "response_status", None),
                    "consistent": getattr(e, "consistent", None),
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in evidence
            ],
            "total": len(evidence),
        }
    finally:
        session.close()


@router.post("/{finding_id}/regen-narrative")
def regen_narrative(finding_id: int) -> dict[str, Any]:
    """Regenerate narrative for a finding (placeholder — returns current data)."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        return _finding_to_dict(f)
    finally:
        session.close()


@router.post("/{finding_id}/generate-report")
def generate_report(finding_id: int) -> dict[str, Any]:
    """Generate a draft report from a finding."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        return {
            "finding_id": finding_id,
            "title": f.title or f"Finding #{f.id}",
            "severity": f.severity or "medium",
            "description": f.description or "",
            "remediation": "No se especificó remediación.",
        }
    finally:
        session.close()


@router.get("/{finding_id}/export-markdown")
def export_finding_markdown(finding_id: int):
    """Export finding as Markdown."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        md = f"""# {f.title or f"Finding #{f.id}"}

**Severidad:** {f.severity or "medium"}
**Target ID:** {f.target_id}
**Endpoint ID:** {f.endpoint_id or "N/A"}

## Descripción

{f.description or "Sin descripción."}

---
*Generado por CATEYE — {__import__("datetime").datetime.now().isoformat()}*
"""
        return Response(
            content=md,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=finding_{finding_id}.md"},
        )
    finally:
        session.close()


@router.get("/{finding_id}/export-pdf")
def export_finding_pdf(finding_id: int):
    """Export finding as PDF (returns a simple HTML version for now)."""
    session = db.SessionLocal()
    try:
        f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="Finding not found")
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{f.title}</title></head>
<body style="font-family: monospace; background: #050505; color: #e0f0e0; padding: 2rem;">
<h1 style="color: #00ff41;">{f.title or f"Finding #{f.id}"}</h1>
<p><strong>Severidad:</strong> {f.severity or "medium"}</p>
<p><strong>Target:</strong> {f.target_id}</p>
<p><strong>Endpoint:</strong> {f.endpoint_id or "N/A"}</p>
<h2>Descripción</h2>
<p>{f.description or "Sin descripción."}</p>
<hr>
<small>Generado por CATEYE</small>
</body></html>"""
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=finding_{finding_id}.html"},
        )
    finally:
        session.close()
