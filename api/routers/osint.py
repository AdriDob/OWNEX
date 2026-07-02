"""OSINT integration router — exposes external threat intelligence APIs."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.recon.osint_api import CLIENTS, query_all

logger = logging.getLogger("catseye.api.osint")
router = APIRouter(prefix="/api/osint", tags=["osint"])


class QueryRequest(BaseModel):
    service: str
    target: str


@router.get("/services")
async def list_services():
    """List all available OSINT services with their key status."""
    return {
        "services": [
            {
                "name": name,
                "configured": bool(client.api_key) or name in ("threatfox", "spoofcheck"),
            }
            for name, client in CLIENTS.items()
        ],
        "total": len(CLIENTS),
    }


@router.post("/query")
async def query_osint(req: QueryRequest):
    """Query an OSINT service about a target.

    Supported services: shodan, censys, virustotal, securitytrails,
    alienvault, urlscan, hunter, builtwith, hibp, greynoise, intelx,
    pulsedive, threatfox, ipinfo, spoofcheck.
    """
    result = await query_all(req.service, req.target)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/query-bulk")
async def query_bulk(queries: list[QueryRequest]):
    """Query multiple OSINT services in parallel."""
    import asyncio

    async def run_one(q: QueryRequest):
        try:
            return await query_all(q.service, q.target)
        except Exception as e:
            return {"service": q.service, "target": q.target, "error": str(e)}

    results = await asyncio.gather(*[run_one(q) for q in queries])
    return {"results": results}
