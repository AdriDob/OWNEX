from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("catseye.ai_security")
router = APIRouter(prefix="/api/ai-security", tags=["ai_security"])


@router.post("/scan-local")
async def scan_local(payload: dict[str, Any]) -> dict[str, Any]:
    model = (payload.get("model") or "qwen3-coder:8b").strip()
    if not model:
        raise HTTPException(400, "model is required")
    return {"status": "ok", "model": model, "findings": []}


@router.get("/opportunities")
async def list_opportunities() -> list[dict[str, Any]]:
    return []


@router.post("/assess")
async def assess_opportunity(payload: dict[str, Any]) -> dict[str, Any]:
    platform = (payload.get("platform") or "").strip()
    challenge_id = (payload.get("challenge_id") or "").strip()
    if not platform or not challenge_id:
        raise HTTPException(400, "platform and challenge_id are required")
    return {"platform": platform, "challenge_id": challenge_id, "score": 0.5}
