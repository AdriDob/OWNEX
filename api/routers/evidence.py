import os
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile

from api.schemas.models import PaginatedResponse
from api.services.data_service import list_evidence

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

_EVIDENCE_DIR = Path(os.path.expanduser("~")) / ".orion" / "evidence"


@router.get("", response_model=PaginatedResponse)
def get_evidence(
    verdict_id: int | None = Query(None, description="Filter by verdict ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    sort_by: str = Query("id"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: str = Query("", max_length=200),
):
    items, total = list_evidence(verdict_id=verdict_id, skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
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
        raise HTTPException(status_code=500, detail="Failed to save evidence file")
    return {"status": "ok", "path": str(dest), "size": len(content), "finding_id": finding_id}
