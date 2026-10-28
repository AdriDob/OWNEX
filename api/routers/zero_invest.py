"""Zero-Invest services API — report factory + data curation + packs + automation.

Un router fino ($0, sin lógica propia): delega a cores.* existentes.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/zero-invest", tags=["zero-invest"])


# ── Report Factory ──
class ReportPackageIn(BaseModel):
    platform: str = "hackerone"
    data: dict[str, Any] = Field(default_factory=dict)
    tier: str = "standard"


@router.get("/report-factory/catalog")
async def zi_report_catalog() -> dict[str, Any]:
    from cores.reports.factory import gig_catalog

    return {"tiers": gig_catalog()}


@router.post("/report-factory/build")
async def zi_report_build(payload: ReportPackageIn) -> dict[str, Any]:
    from cores.reports.factory import build_package

    pkg = build_package(platform=payload.platform, data=payload.data, tier=payload.tier)
    if not pkg:
        raise HTTPException(status_code=422, detail="platform inválida o title faltante")
    return {
        "success": True,
        "id": pkg.id,
        "platform": pkg.platform,
        "tier": pkg.tier,
        "price_usd": pkg.price_usd,
        "checklist": pkg.checklist,
        "markdown": pkg.markdown[:4000],
    }


# ── Data Curation ──
class CurateIn(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "manual"


@router.post("/data-curation/curate")
async def zi_curate(payload: CurateIn) -> dict[str, Any]:
    from cores.data_curation import get_curation_pipeline

    return dict(get_curation_pipeline().curate(payload.items, source=payload.source))


@router.get("/data-curation/package")
async def zi_package(min_quality: float = 0.6) -> dict[str, Any]:
    from cores.data_curation import get_curation_pipeline

    return dict(get_curation_pipeline().package(min_quality=min_quality))


# ── Security Packs ──
@router.get("/security-packs")
async def zi_packs() -> dict[str, Any]:
    from cores.security_packs import pack_list

    return {"total": len(pack_list()), "packs": pack_list()}


@router.get("/security-packs/{pack_id}")
async def zi_pack_detail(pack_id: str) -> dict[str, Any]:
    from cores.security_packs import get_pack, render_pack_md

    pack = get_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found")
    return {**pack, "markdown": (render_pack_md(pack_id) or "")[:4000]}


# ── Automation Service ──
@router.get("/automation/offers")
async def zi_automation_offers() -> dict[str, Any]:
    from cores.automation_service import offer_catalog

    return {"total": len(offer_catalog()), "offers": offer_catalog()}


@router.post("/automation/offers/{offer_id}/quote")
async def zi_automation_quote(offer_id: str, complexity_mult: float = 1.0) -> dict[str, Any]:
    from cores.automation_service import quote_offer

    quote = quote_offer(offer_id, complexity_mult=complexity_mult)
    if not quote:
        raise HTTPException(status_code=404, detail="Offer not found")
    return quote
