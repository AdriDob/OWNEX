"""Secrets Management API — Enhanced credentials vault with rotation, audit, and scanning."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.credentials.vault import (
    get_audit_log,
    get_platform_credentials,
    get_secret_scan_results,
    rotate_credential,
)

logger = logging.getLogger("ownex.api.secrets")

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


class RotateRequest(BaseModel):
    platform: str
    field: str
    new_value: str


@router.get("/audit")
def get_audit(limit: int = 100):
    """Get recent audit log entries for credential access."""
    try:
        entries = get_audit_log(limit)
        return {
            "success": True,
            "entries": entries,
            "total": len(entries),
        }
    except Exception as e:
        logger.error(f"Failed to get audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rotate")
def rotate_secret(request: RotateRequest):
    """Rotate a credential (update value and log to audit trail)."""
    try:
        result = rotate_credential(request.platform, request.field, request.new_value)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Rotation failed"))
        return result
    except Exception as e:
        logger.error(f"Failed to rotate credential: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan")
def scan_secrets():
    """Scan codebase for leaked secrets."""
    try:
        results = get_secret_scan_results()
        return results
    except Exception as e:
        logger.error(f"Secret scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platform/{platform}")
def get_platform(platform: str):
    """Get credentials for a specific platform (audit logged)."""
    try:
        creds = get_platform_credentials(platform)
        return {
            "platform": platform,
            "credentials": creds,
            "has_credentials": len(creds) > 0,
        }
    except Exception as e:
        logger.error(f"Failed to get platform credentials: {e}")
        raise HTTPException(status_code=500, detail=str(e))
