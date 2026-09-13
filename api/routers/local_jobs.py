"""Local Jobs AR — read-only board aggregation (ZonaJobs/Bumeran/Computrabajo).

Junior/no-experience friendly, Zona Sur + CABA. Boards are read-only:
application is always MANUAL (external action, Human Gate by nature).
Never raises: a dead board degrades to its curated fallback inside the adapter.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter

from cores.opportunity.adapters.ar_jobs import (
    BumeranAdapter,
    ComputrabajoAdapter,
    ZonaJobsAdapter,
    build_ar_search_url,
)

router = APIRouter(prefix="/api/local-jobs", tags=["local-jobs"])

_BOARDS = ("zonajobs", "bumeran", "computrabajo")

_ADAPTERS = {
    "zonajobs": ZonaJobsAdapter,
    "bumeran": BumeranAdapter,
    "computrabajo": ComputrabajoAdapter,
}


def _serialize(raw: Any) -> dict[str, Any]:
    try:
        data = asdict(raw)
    except Exception:
        return {"id": "", "name": "", "platform": "", "url": "", "apply": "MANUAL"}
    meta = data.get("metadata") or {}
    return {
        "id": str(data.get("id", "")),
        "name": str(data.get("name", "")),
        "description": str(data.get("description", ""))[:500],
        "platform": str(data.get("platform", "")),
        "url": str(data.get("url", "") or ""),
        "tags": list(data.get("tags", []) or []),
        "apply": str(meta.get("apply", "MANUAL")),
        "modality": str(meta.get("modality", "presencial")),
        "zone": str(meta.get("zone", "")),
    }


@router.get("/search")
async def local_jobs_search(query: str = "junior", zone: str = "Zona Sur", board: str = "all") -> dict[str, Any]:
    """Aggregate junior-friendly listings across AR boards (read-only)."""
    wanted = [board] if board in _ADAPTERS else list(_BOARDS)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for name in wanted:
        try:
            adapter = _ADAPTERS[name]({"zone": zone})
            items = await adapter.fetch_opportunities()
            for raw in items:
                entry = _serialize(raw)
                entry["board"] = name
                results.append(entry)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}")
    return {
        "query": query,
        "zone": zone,
        "total": len(results),
        "results": results[:60],
        "errors": errors,
        "apply": "MANUAL — la postulación se hace en el sitio del aviso.",
    }


@router.get("/boards")
async def local_jobs_boards(query: str = "junior", zone: str = "Zona Sur") -> dict[str, Any]:
    """Deep-links to board search pages (no scraping, always live links)."""
    return {
        "zone": zone,
        "boards": [
            {"board": name, "url": build_ar_search_url(name, query, zone), "apply": "MANUAL"} for name in _BOARDS
        ],
    }
