"""Fiverr Strategic Integration Engine — API router.

Exposes the Fiverr gig catalog, pricing intelligence, order pipeline planning
and reusable-asset knowledge growth so Mission Control / daily use can consume
the strategy. No auto-submission: Fiverr orders are prepared and surfaced, the
human delivers (Human Control Layer).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from cores.fiverr.engine import FiverrEngine, get_fiverr_engine

logger = logging.getLogger("ownex.api.fiverr")

router = APIRouter(prefix="/fiverr", tags=["fiverr"])


class EthicsRequest(BaseModel):
    text: str


class AssetRequest(BaseModel):
    name: str
    kind: str = "module"
    source_order_id: str = ""
    category: str = ""
    description: str = ""


class PlanRequest(BaseModel):
    order_id: str
    gig_key: str
    title: str = ""


class DeliveryRequest(BaseModel):
    opportunity: dict[str, Any]
    gig_key: str


def _engine() -> FiverrEngine:
    return get_fiverr_engine()


@router.get("/catalog")
async def fiverr_catalog(category: str | None = None) -> dict[str, Any]:
    """The generated gig catalog — one solution per gig, priced per tier."""
    gigs = _engine().catalog(category=category)
    return {
        "count": len(gigs),
        "categories": [
            "python_automation",
            "api_integration",
            "ai_integration",
            "bug_fixing",
            "custom_scripts",
            "desktop_automation",
            "browser_automation",
            "data_processing",
            "developer_utilities",
            "unity_programming",
            "unreal_programming",
        ],
        "gigs": [g.to_dict() for g in gigs],
    }


@router.post("/plan")
async def fiverr_plan(req: PlanRequest) -> dict[str, Any]:
    """Create the per-order delivery pipeline plan (Requirement -> package)."""
    plan = _engine().plan_order(req.order_id, req.gig_key, req.title)
    return plan.to_dict()


@router.post("/delivery/prepare")
async def fiverr_prepare(req: DeliveryRequest) -> dict[str, Any]:
    """Prepare the delivery package files for a gig (human still submits)."""
    return await _engine().prepare_delivery(req.opportunity, req.gig_key)


@router.post("/asset")
async def fiverr_record_asset(req: AssetRequest) -> dict[str, Any]:
    """Register a reusable asset from a completed order (feeds future speed)."""
    rec = _engine().record_asset(req.name, req.kind, req.source_order_id, req.category, req.description)
    return rec.to_dict()


@router.get("/assets")
async def fiverr_assets() -> dict[str, Any]:
    """The reusable asset knowledge base (persistent)."""
    return _engine().assets()


@router.post("/ethics-check")
async def fiverr_ethics(req: EthicsRequest) -> dict[str, Any]:
    """Gate delivery copy for plagiarism / overclaim / ToS red flags."""
    return _engine().validate_deliverable(req.text)


@router.get("/status")
async def fiverr_status() -> dict[str, Any]:
    """Engine status: catalog size, asset count and a pricing sample."""
    engine = _engine()
    catalog = engine.catalog()
    return {
        "gigs": len(catalog),
        "total_assets": engine.assets()["total_assets"],
        "sample_pricing": catalog[0].pricing.to_dict() if catalog else {},
    }
