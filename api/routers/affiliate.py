"""Affiliate Content API — reviews con links de afiliado ($0, sin stock).

Contenido orgánico (MPT) + monetización por afiliación. Publicar = Human Gate.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.affiliate import AffiliateNetwork, get_affiliate_engine

router = APIRouter(prefix="/api/affiliate", tags=["affiliate"])


class LinkIn(BaseModel):
    url: str
    product_name: str = ""
    network: AffiliateNetwork = AffiliateNetwork.OTHER
    commission_pct: float = 0.0


class ContentIn(BaseModel):
    product_name: str
    angle: str = "review"
    link_ids: list[str] = Field(default_factory=list)
    price_txt: str = ""


class ConversionIn(BaseModel):
    earned_usd: float = 0.0


@router.get("/status")
async def affiliate_status() -> dict[str, Any]:
    return dict(get_affiliate_engine().get_status())


@router.post("/links")
async def affiliate_add_link(payload: LinkIn) -> dict[str, Any]:
    link = get_affiliate_engine().add_link(
        url=payload.url,
        product_name=payload.product_name,
        network=payload.network,
        commission_pct=payload.commission_pct,
    )
    if not link:
        raise HTTPException(status_code=422, detail="url http(s) requerida")
    return {"success": True, "id": link.id, "network": link.network.value}


@router.get("/links")
async def affiliate_list_links() -> dict[str, Any]:
    rows = get_affiliate_engine().list_links()
    return {
        "total": len(rows),
        "links": [
            {
                "id": link.id,
                "network": link.network.value,
                "product_name": link.product_name,
                "clicks": link.clicks,
                "conversions": link.conversions,
                "earned_usd": link.earned_usd,
            }
            for link in rows[:100]
        ],
    }


@router.post("/links/{link_id}/click")
async def affiliate_click(link_id: str) -> dict[str, Any]:
    link = get_affiliate_engine().record_click(link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"success": True, "clicks": link.clicks}


@router.post("/links/{link_id}/conversion")
async def affiliate_conversion(link_id: str, payload: ConversionIn) -> dict[str, Any]:
    link = get_affiliate_engine().record_conversion(link_id, earned_usd=payload.earned_usd)
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"success": True, "conversions": link.conversions, "earned_usd": link.earned_usd}


@router.post("/contents/plan")
async def affiliate_plan_content(payload: ContentIn) -> dict[str, Any]:
    if not payload.product_name.strip():
        raise HTTPException(status_code=422, detail="product_name is required")
    content = get_affiliate_engine().plan_content(
        product_name=payload.product_name,
        angle=payload.angle,
        link_ids=payload.link_ids,
        price_txt=payload.price_txt,
    )
    return {
        "success": True,
        "id": content.id,
        "hook": content.script_md.splitlines()[0] if content.script_md else "",
        "script_md": content.script_md,
        "hashtags": content.hashtags,
    }


@router.post("/contents/{content_id}/ready")
async def affiliate_mark_ready(content_id: str) -> dict[str, Any]:
    content = get_affiliate_engine().mark_ready(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"success": True, "status": content.status.value}


@router.post("/contents/{content_id}/publish")
async def affiliate_mark_published(content_id: str) -> dict[str, Any]:
    content = get_affiliate_engine().mark_published(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"success": True, "status": content.status.value}
