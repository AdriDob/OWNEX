from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from core.ai_bounty.engine import AIBountyEngine
from core.intel.llm_scanner import LLMScanResult, scan_local_model

logger = logging.getLogger("catseye.ai_security")
router = APIRouter(prefix="/api/ai-security", tags=["ai_security"])

_engine: AIBountyEngine | None = None


def _get_engine() -> AIBountyEngine:
    global _engine
    if _engine is None:
        _engine = AIBountyEngine()
    return _engine


@router.post("/scan-local")
async def scan_local(payload: dict[str, Any]) -> LLMScanResult:
    model = (payload.get("model") or "qwen3-coder:8b").strip()
    if not model:
        raise HTTPException(400, "model is required")
    return await scan_local_model(model)


@router.get("/opportunities")
async def list_opportunities() -> list[dict[str, Any]]:
    engine = _get_engine()
    challenges = engine.discover_all()
    results = []
    for c in challenges:
        assessment = engine.assess_opportunity(c.platform, c.challenge_id)
        results.append(assessment)
    return results


@router.post("/assess")
async def assess_opportunity(payload: dict[str, Any]) -> dict[str, Any]:
    platform = (payload.get("platform") or "").strip()
    challenge_id = (payload.get("challenge_id") or "").strip()
    if not platform or not challenge_id:
        raise HTTPException(400, "platform and challenge_id are required")
    result = _get_engine().assess_opportunity(platform, challenge_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result
