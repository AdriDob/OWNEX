"""Recon Router API — fingerprint, route, strategies."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from core.recon.fingerprint import Fingerprinter
from core.recon.router import ReconRouter
from core.recon.strategies import list_strategies

logger = logging.getLogger("orion.recon")
router = APIRouter(prefix="/api/recon", tags=["recon"])


@router.post("/fingerprint")
async def fingerprint_target(data: dict[str, Any]):
    """Fingerprint a target domain to detect its technology stack."""
    domain = data.get("domain", "").strip()
    if not domain:
        raise HTTPException(status_code=400, detail="domain is required")

    try:
        fp = Fingerprinter()
        result = fp.fingerprint(domain)
        return {
            "success": True,
            "domain": domain,
            "primary_tech": result.primary_tech,
            "tech_summary": result.tech_summary,
            "technologies": [
                {"name": t.name, "category": t.category, "confidence": round(t.confidence, 2)}
                for t in result.technologies
            ],
            "headers": dict(list(result.headers.items())[:20]),
            "cookies": dict(result.cookies),
        }
    except Exception as e:
        logger.exception("Fingerprint failed for %s", domain)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/route")
async def route_target(data: dict[str, Any]):
    """Run the full recon router on a target domain."""
    domain = data.get("domain", "").strip()
    if not domain:
        raise HTTPException(status_code=400, detail="domain is required")

    try:
        router = ReconRouter()
        result = router.route(domain)
        return {
            "success": True,
            "domain": domain,
            "tech_summary": result.tech_summary,
            "strategies_used": result.strategies_used,
            "probes_attempted": result.probes_attempted,
            "endpoints_found": [
                {
                    "url": ep.get("url"),
                    "method": ep.get("method", "GET"),
                    "status": ep.get("status"),
                    "reason": ep.get("reason", ""),
                    "strategy": ep.get("strategy", ""),
                    "has_graphql_response": ep.get("has_graphql_response", False),
                }
                for ep in result.endpoints_found
            ],
        }
    except Exception as e:
        logger.exception("Route failed for %s", domain)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/strategies")
async def list_recon_strategies():
    """List all available recon strategies."""
    strategies = list_strategies()
    return {
        "success": True,
        "strategies": [
            {
                "name": s.name,
                "description": s.description,
                "tech_targets": s.tech_targets,
                "priority": s.priority,
                "probe_count": len(s.probes),
            }
            for s in strategies
        ],
    }
