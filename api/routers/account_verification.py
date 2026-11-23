"""Account Verification API — Guided Earning Fase 1.1.

Per-platform reusable verification state machine. One verified account
unlocks every opportunity on that platform.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.opportunity import account_verification as av

logger = logging.getLogger("ownex.api.account_verification")

router = APIRouter(prefix="/api/account-verification", tags=["account-verification"])


class ConfirmBody(BaseModel):
    field: str
    value: str
    method: str = "OWNER_CONFIRMED"
    evidence_ref: str = ""
    notes: str = ""


@router.get("/{platform}")
def get_account_verification(platform: str) -> dict:
    """Verification record + pre-registration research + checklist."""
    return av.verification_view(platform)


@router.post("/{platform}/confirm")
def confirm_verification(platform: str, body: ConfirmBody) -> dict:
    """Record a status confirmation (owner or authorized integration)."""
    try:
        rec = av.confirm(
            platform,
            body.field,
            body.value,
            method=body.method,
            evidence_ref=body.evidence_ref,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"platform": platform, "record": rec, "view": av.verification_view(platform)}


@router.post("/{platform}/pause")
def pause_verification(platform: str) -> dict:
    av.set_paused(platform, True)
    return {"platform": platform, "paused": True}


@router.post("/{platform}/resume")
def resume_verification(platform: str) -> dict:
    av.set_paused(platform, False)
    return {"platform": platform, "paused": False}


@router.get("/list/all")
def list_all_verifications() -> dict:
    return {"verifications": av.list_verifications()}
