import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile
from pydantic import BaseModel

from api.schemas.models import PaginatedResponse
from api.services.data_service import list_evidence
from core.evidence.composer import EvidenceComposer, publish_evidence_event
from cores.platform.system import get_data_dir

logger = logging.getLogger("cateye.api.evidence")

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

_EVIDENCE_DIR = get_data_dir() / "evidence"
_composer = EvidenceComposer()


class ComposeEvidenceRequest(BaseModel):
    """Request body for composing evidence from raw hypothesis data."""

    vulnerability_type: str = "generic"
    endpoint: str = ""
    method: str = "GET"
    confidence: float = 0.5
    severity: str = "medium"
    summary: str = ""
    description: str = ""
    parameters_of_interest: list[str] = []
    test_instructions: list[str] = []
    signals: list[str] = []
    scope_check: str = ""
    reproducibility_notes: str = ""
    alternative_explanations: list[dict] = []
    host: str = ""


@router.get("", response_model=PaginatedResponse)
def get_evidence(
    verdict_id: int | None = Query(None, description="Filter by verdict ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("id"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_evidence(
        verdict_id=verdict_id, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search
    )
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/upload")
async def upload_evidence(file: UploadFile, finding_id: int | None = None):
    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix if file.filename else ""
    stem = uuid.uuid4().hex
    dest = _EVIDENCE_DIR / f"{stem}{ext}"
    try:
        content = await file.read()
        dest.write_bytes(content)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save evidence file") from None
    return {"status": "ok", "path": str(dest), "size": len(content), "finding_id": finding_id}


@router.post("/compose")
def compose_evidence(req: ComposeEvidenceRequest):
    """Compose an evidence bundle from hypothesis data.

    Accepts raw hypothesis fields and returns a complete evidence bundle
    with PoC in multiple formats, CVSS score, CWE/CAPEC, and Nuclei template.
    """
    try:
        bundle = _composer.compose_from_dict(
            req.model_dump(exclude={"host"}),
            host=req.host,
        )
        publish_evidence_event("composed", bundle)
        return {
            "schema_version": "1.0",
            "generated_at": bundle.composed_at,
            "generator": "EvidenceComposer",
            "bundle": bundle.to_dict(),
        }
    except Exception as exc:
        logger.exception("[EVIDENCE] Compose failed")
        raise HTTPException(status_code=500, detail=f"Evidence composition failed: {exc}") from exc
