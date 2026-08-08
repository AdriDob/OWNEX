"""API Router for Auto-dispute."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.auto_dispute import get_dispute_client, open_auto_dispute

router = APIRouter(prefix="/api/dispute", tags=["dispute"])


class OpenDisputeRequest(BaseModel):
    platform: str  # "hackerone" | "gitcoin"
    finding_id: str
    reason: str
    evidence: dict[str, Any]
    platform_ref: str | None = None  # report_id or bounty_id


@router.post("/open")
def open_dispute(req: OpenDisputeRequest):
    """Abrir disputa automática en HackerOne o Gitcoin."""
    result = open_auto_dispute(req.platform, req.finding_id, req.reason, req.evidence, req.platform_ref)
    if not result["remote"].get("success"):
        raise HTTPException(status_code=400, detail=result["remote"].get("error", "Dispute failed"))
    return result


@router.get("/list")
def list_disputes():
    """Listar disputas locales guardadas."""
    client = get_dispute_client()
    return {"items": client.list_local_disputes(), "total": len(client.list_local_disputes())}


@router.get("/status/{dispute_id}")
def get_dispute_status(dispute_id: str):
    """Consultar estado de disputa local."""
    client = get_dispute_client()
    for d in client.list_local_disputes():
        if d["dispute_id"] == dispute_id:
            return d
    raise HTTPException(status_code=404, detail="Dispute not found")


@router.post("/check-h1/{report_id}")
async def check_h1_report(report_id: str):
    """Consultar estado de reporte en HackerOne."""
    client = get_dispute_client()
    result = await client.h1_check_report(report_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
