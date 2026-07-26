from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from core.intel.cve_intel import CVEResult, prioritize_cves
from core.intel.finance import FinanceIntel, get_finance_intel
from core.intel.llm_scanner import LLMScanResult, scan_llm_endpoint

logger = logging.getLogger("catseye.intel")
router = APIRouter(prefix="/api/intel", tags=["intel"])


@router.post("/llm-scan")
async def run_llm_scan(payload: dict[str, Any]) -> LLMScanResult:
    endpoint = payload.get("endpoint", "").strip()
    api_key = payload.get("api_key", "").strip() or None
    if not endpoint:
        raise HTTPException(400, "endpoint is required")
    result = await scan_llm_endpoint(endpoint, api_key)
    return result


@router.post("/cve-prioritize")
async def run_cve_prioritize(payload: dict[str, Any]) -> list[CVEResult]:
    tech_stack = payload.get("tech_stack", [])
    if not tech_stack:
        raise HTTPException(400, "tech_stack is required")
    results = await prioritize_cves(tech_stack)
    return results


@router.get("/finance")
async def finance_intel() -> FinanceIntel:
    return await get_finance_intel()


@router.get("/health")
async def intel_health() -> dict[str, str]:
    return {"status": "ok", "module": "intel"}
