"""E-commerce API — Droppinglabel + MercadoLibre + IG/WA from OWNEX.

Zero-stock model: supplier -> customer. No fake data: adapters report
honest unavailable when credentials are missing; publishing needs human approval.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel, Field

from cores.ecommerce.adapters import adapter_health
from cores.ecommerce.engine import get_ecommerce_engine
from cores.ecommerce.models import (
    Marketplace,
    OrderItem,
    OrderStatus,
    Product,
    ProductStatus,
    Supplier,
    SupplierType,
)
from cores.ecommerce.pipeline import (
    get_content_planner,
    get_listing_optimizer,
    get_order_orchestrator,
    get_sourcing_engine,
    run_ecommerce_competitor_watch,
    run_ecommerce_listing_health,
    run_ecommerce_order_sync,
    run_ecommerce_review_request,
    run_ecommerce_supplier_scorecards,
)

router = APIRouter(prefix="/api/ecommerce", tags=["ecommerce"])


class SupplierIn(BaseModel):
    id: str
    name: str
    type: SupplierType = SupplierType.OTHER
    processing_time_days: int = 3
    is_active: bool = True
    website: str = ""
    instagram: str = ""
    reseller_program: bool = False
    api_endpoint: str = ""


class ProductIn(BaseModel):
    id: str
    sku: str
    name: str
    description: str = ""
    category: str = ""
    brand: str = ""
    supplier_id: str = ""
    authenticity: str = "unknown"  # official | licensed | replica | unknown
    cost_usd: float = 0.0
    sale_price_usd: float = 0.0
    sale_price_ars: float = 0.0
    currency: str = "USD"
    images: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, str] = Field(default_factory=dict)


class SourcingScoreIn(BaseModel):
    cost_usd: float = 0.0
    sale_price_usd: float = 0.0
    processing_days: int = 3
    shipping_usd: float = 0.0
    marketplace_fee_pct: float = 13.0
    platform_fee_pct: float = 0.0
    tax_pct: float = 0.0
    other_costs_usd: float = 0.0


@router.get("/status")
async def ecommerce_status() -> dict[str, Any]:
    engine = get_ecommerce_engine()
    return {**engine.get_status(), "adapters": adapter_health()}


@router.get("/adapters/health")
async def ecommerce_adapters_health() -> dict[str, Any]:
    return adapter_health()


@router.post("/suppliers")
async def ecommerce_add_supplier(payload: SupplierIn) -> dict[str, Any]:
    engine = get_ecommerce_engine()
    supplier = Supplier(
        id=payload.id,
        name=payload.name,
        type=payload.type,
        processing_time_days=payload.processing_time_days,
        is_active=payload.is_active,
        website=payload.website,
        instagram=payload.instagram,
        reseller_program=payload.reseller_program,
        api_endpoint=payload.api_endpoint,
    )
    engine.add_supplier(supplier)
    return {"success": True, "id": supplier.id}


@router.get("/suppliers")
async def ecommerce_list_suppliers() -> dict[str, Any]:
    engine = get_ecommerce_engine()
    suppliers = engine.list_suppliers(active_only=False)
    # Enrich with outreach status so front needs 1 call, not N
    try:
        from cores.ecommerce.models import zero_capital_gate
        from cores.ecommerce.outreach import get_outreach_store, next_step_for_status, niche_for

        outreach = get_outreach_store().list_all()
    except Exception:
        outreach = {}

        def next_step_for_status(status: str) -> str:  # type: ignore[no-redef]
            return "Contactar por WhatsApp (1 click)"

        def niche_for(supplier_id: str, supplier_name: str) -> str:  # type: ignore[no-redef]
            return "generic"

        def zero_capital_gate(supplier: Any) -> dict[str, Any]:  # type: ignore[no-redef]
            return {"status": "future", "reasons": ["gate no disponible"]}

    return {
        "total": len(suppliers),
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "type": s.type.value,
                "active": s.is_active,
                "website": s.website,
                "instagram": getattr(s, "instagram", ""),
                "reseller_program": bool(getattr(s, "reseller_program", False)),
                "niche": niche_for(s.id, s.name),
                "commission_rate": float(s.commission_rate) if s.commission_rate else None,
                "processing_time_days": s.processing_time_days,
                "notes": s.notes,
                "zero_capital": zero_capital_gate(s),
                "outreach": outreach.get(s.id).to_dict()
                if s.id in outreach and outreach.get(s.id) is not None
                else {"status": "pending", "next_step": next_step_for_status("pending")},
            }
            for s in sorted(suppliers, key=lambda x: x.id)
        ],
    }


@router.get("/suppliers/outreach/summary")
async def ecommerce_outreach_summary() -> dict[str, Any]:
    from cores.ecommerce.outreach import build_message, get_outreach_store

    store = get_outreach_store()
    return {"summary": store.summary(), "templates": list(build_message("x", "Demo").keys())}


@router.get("/suppliers/{supplier_id}/outreach")
async def ecommerce_supplier_outreach(supplier_id: str, canal: str = "meli") -> dict[str, Any]:
    from cores.ecommerce.outreach import CANALES_VALIDOS, build_message, build_reseller_pitch, get_outreach_store

    if canal not in CANALES_VALIDOS:
        raise HTTPException(status_code=422, detail="canal debe ser meli|ig")
    engine = get_ecommerce_engine()
    sup = engine.get_supplier(supplier_id)
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")
    msg = build_message(sup.id, sup.name, canal=canal)
    rec = get_outreach_store().get(supplier_id)
    return {
        "supplier": {"id": sup.id, "name": sup.name, "website": sup.website},
        "message": msg,
        "reseller_pitch": build_reseller_pitch(sup.id, sup.name),
        "record": rec.to_dict() if rec else None,
    }


@router.post("/suppliers/{supplier_id}/outreach/contact")
async def ecommerce_supplier_mark_contacted(supplier_id: str, notes: str = "", canal: str = "meli") -> dict[str, Any]:
    from cores.ecommerce.outreach import CANALES_VALIDOS, build_message, get_outreach_store

    if canal not in CANALES_VALIDOS:
        raise HTTPException(status_code=422, detail="canal debe ser meli|ig")
    engine = get_ecommerce_engine()
    sup = engine.get_supplier(supplier_id)
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")
    msg = build_message(sup.id, sup.name, canal=canal)
    rec = get_outreach_store().mark_contacted(supplier_id, wa_url=msg["wa_url"], message=msg["body"], notes=notes)
    return {"success": True, "record": rec.to_dict(), "wa_url": msg["wa_url"]}


@router.post("/suppliers/{supplier_id}/outreach/status")
async def ecommerce_supplier_set_status(supplier_id: str, status: str, notes: str = "") -> dict[str, Any]:
    from cores.ecommerce.outreach import get_outreach_store

    if status not in ("pending", "contacted", "replied", "verified", "rejected"):
        raise HTTPException(status_code=422, detail="status must be pending|contacted|replied|verified|rejected")
    rec = get_outreach_store().mark(supplier_id, status=status, notes=notes)
    if not rec:
        raise HTTPException(status_code=404, detail="No outreach yet — use /contact first")
    return {"success": True, "record": rec.to_dict()}


@router.post("/suppliers/{supplier_id}/verify")
async def ecommerce_supplier_mark_verified(supplier_id: str, notes: str = "") -> dict[str, Any]:
    """Marca términos $0 confirmados (las 5 preguntas por WA respondidas OK).

    Activa el gate ACTIVE si además no hay capital/abono/mínimo. Reversible
    con verified=False vía update. Distinto del outreach 'verified' (contacto):
    esto confirma PLATA, no conversación.
    """
    from datetime import UTC, datetime

    from cores.ecommerce.models import zero_capital_gate

    engine = get_ecommerce_engine()
    sup = engine.get_supplier(supplier_id)
    if not sup:
        raise HTTPException(status_code=404, detail="Supplier not found")
    engine.update_supplier(supplier_id, verified=True, verified_at=datetime.now(UTC))
    if notes.strip():
        engine.update_supplier(supplier_id, notes=f"{sup.notes} | Verificado: {notes.strip()}".strip(" |"))
    return {"success": True, "id": supplier_id, "zero_capital": zero_capital_gate(sup)}


@router.post("/suppliers/{supplier_id}/sync-catalog")
async def ecommerce_sync_supplier_catalog(supplier_id: str, limit: int = 50) -> dict[str, Any]:
    """Mirror a supplier website catalog into DRAFT products.

    New items enter as DRAFT: nothing publishes to Meli without human
    review (price via /sourcing/score, ACTIVE status, approved payload).
    """
    engine = get_ecommerce_engine()
    if engine.get_supplier(supplier_id) is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return await engine.sync_supplier_catalog(supplier_id, limit=limit)


@router.post("/products")
async def ecommerce_add_product(payload: ProductIn) -> dict[str, Any]:
    from cores.ecommerce.models import AUTHENTICITY_VALUES

    if payload.authenticity not in AUTHENTICITY_VALUES:
        raise HTTPException(status_code=422, detail="authenticity debe ser official|licensed|replica|unknown")
    engine = get_ecommerce_engine()
    product = Product(
        id=payload.id,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        brand=payload.brand,
        supplier_id=payload.supplier_id,
        authenticity=payload.authenticity,
        cost_usd=Decimal(str(payload.cost_usd)),
        sale_price_usd=Decimal(str(payload.sale_price_usd)),
        sale_price_ars=Decimal(str(payload.sale_price_ars)),
        currency=payload.currency,
        images=list(payload.images),
        tags=list(payload.tags),
        attributes=dict(payload.attributes),
        status=ProductStatus.ACTIVE,
    )
    engine.add_product(product)
    return {
        "success": True,
        "id": product.id,
        "margin_pct": product.margin_pct,
        "roi_pct": product.roi_pct,
    }


@router.get("/products")
async def ecommerce_list_products(category: str | None = None, supplier_id: str | None = None) -> dict[str, Any]:
    from cores.ecommerce.models import publish_blockers

    engine = get_ecommerce_engine()
    products = engine.list_products(category=category, supplier_id=supplier_id)
    return {
        "total": len(products),
        "products": [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "cost_usd": float(p.cost_usd),
                "sale_price_usd": float(p.sale_price_usd),
                "margin_pct": round(p.margin_pct, 1),
                "status": p.status.value,
                "authenticity": getattr(p, "authenticity", "unknown"),
                "publish_blockers": publish_blockers(p),
                "listings": p.marketplace_listings,
            }
            for p in products
        ],
    }


@router.post("/products/{product_id}/optimize")
async def ecommerce_optimize_listing(product_id: str, marketplace: str = "mercadolibre") -> dict[str, Any]:
    from cores.ecommerce.models import publish_blockers

    engine = get_ecommerce_engine()
    product = engine.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    blockers = publish_blockers(product)
    if blockers:
        raise HTTPException(status_code=422, detail={"blocked": "publish_blocked", "blockers": blockers})
    try:
        marketplace_enum = Marketplace(marketplace)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid marketplace: {marketplace}") from None
    listing = get_listing_optimizer().optimize_listing(product, marketplace_enum)
    product.marketplace_listings[marketplace_enum.value] = listing.id
    return {
        "listing_id": listing.id,
        "title": listing.title,
        "description": listing.description[:500],
        "price_usd": float(listing.price_usd),
    }


@router.post("/sourcing/score")
async def ecommerce_sourcing_score(payload: SourcingScoreIn) -> dict[str, Any]:
    return get_sourcing_engine().score_supplier_offer(
        cost_usd=payload.cost_usd,
        sale_price_usd=payload.sale_price_usd,
        processing_days=payload.processing_days,
        shipping_usd=payload.shipping_usd,
        marketplace_fee_pct=payload.marketplace_fee_pct,
        platform_fee_pct=payload.platform_fee_pct,
        tax_pct=payload.tax_pct,
        other_costs_usd=payload.other_costs_usd,
    )


class PricingSuggestIn(BaseModel):
    cost_usd: float = 0.0
    competitor_prices: list[float] = Field(default_factory=list)
    target_margin_pct: float = 35.0
    shipping_usd: float = 0.0
    marketplace_fee_pct: float = 13.0
    platform_fee_pct: float = 0.0
    tax_pct: float = 0.0
    other_costs_usd: float = 0.0


@router.post("/sourcing/suggest-price")
async def ecommerce_suggest_price(payload: PricingSuggestIn) -> dict[str, Any]:
    """Auto-pricing $0: floor por margen objetivo vs 95% del mínimo competidor."""
    return get_sourcing_engine().suggest_price(
        cost_usd=payload.cost_usd,
        competitor_prices=payload.competitor_prices,
        target_margin_pct=payload.target_margin_pct,
        shipping_usd=payload.shipping_usd,
        marketplace_fee_pct=payload.marketplace_fee_pct,
        platform_fee_pct=payload.platform_fee_pct,
        tax_pct=payload.tax_pct,
        other_costs_usd=payload.other_costs_usd,
    )


@router.post("/sourcing/net-real")
async def ecommerce_net_real(payload: SourcingScoreIn) -> dict[str, Any]:
    """NETO REAL: venta − proveedor − Meli − plataforma − impuestos − otros.

    Misma matemática que /sourcing/score con otro nombre: el número que
    importa (ganancia neta por venta). platform_fee_pct=3.0 para Dropsheable.
    """
    return get_sourcing_engine().score_supplier_offer(
        cost_usd=payload.cost_usd,
        sale_price_usd=payload.sale_price_usd,
        processing_days=payload.processing_days,
        shipping_usd=payload.shipping_usd,
        marketplace_fee_pct=payload.marketplace_fee_pct,
        platform_fee_pct=payload.platform_fee_pct,
        tax_pct=payload.tax_pct,
        other_costs_usd=payload.other_costs_usd,
    )


class ProductScoreIn(BaseModel):
    margin_pct: float | None = None
    demand_0_10: float | None = None
    competition_0_10: float | None = None
    rotation_0_10: float | None = None
    supplier_reliability_0_10: float | None = None
    fulfillment_ease_0_10: float | None = None
    ticket_usd: float | None = None
    return_risk_0_10: float | None = None
    capital_required_usd: float = 0.0
    fulfillment_provider: bool = True
    stock_sync: bool = True


@router.post("/sourcing/product-score")
async def ecommerce_product_score(payload: ProductScoreIn) -> dict[str, Any]:
    """Product score con hard gates $0 (25% margen 20% demanda ...)."""
    return get_sourcing_engine().product_score(
        margin_pct=payload.margin_pct,
        demand_0_10=payload.demand_0_10,
        competition_0_10=payload.competition_0_10,
        rotation_0_10=payload.rotation_0_10,
        supplier_reliability_0_10=payload.supplier_reliability_0_10,
        fulfillment_ease_0_10=payload.fulfillment_ease_0_10,
        ticket_usd=payload.ticket_usd,
        return_risk_0_10=payload.return_risk_0_10,
        capital_required_usd=payload.capital_required_usd,
        fulfillment_provider=payload.fulfillment_provider,
        stock_sync=payload.stock_sync,
    )


@router.post("/products/{product_id}/score")
async def ecommerce_product_assembled_score(product_id: str) -> dict[str, Any]:
    """Score 0-10 de un producto armando señales reales (nunca inventa).

    margen ← producto · confiabilidad/calidad/devoluciones ← scorecard del
    proveedor · competencia ← snapshots rivales · demanda/rotación/logística =
    UNKNOWN (neutral 5.0) hasta tener datos · gates $0 ← proveedor.
    """
    from cores.ecommerce.models import zero_capital_gate

    engine = get_ecommerce_engine()
    product = engine.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    supplier = engine.get_supplier(product.supplier_id) if product.supplier_id else None
    signals: dict[str, Any] = {"fuente": {}, "unknown": []}
    margin = float(product.margin_pct or 0.0)
    if margin > 0:
        signals["fuente"]["margen"] = "producto.margin_pct"
    else:
        signals["unknown"].append("margen (sin precio/costo)")
    reliability = quality = riesgo_dev = None
    if supplier is not None:
        # Scorecard en 0-100; product_score espera 0-10 → /10.
        reliability = float(supplier.fulfillment_rate) if supplier.total_pos > 0 else None
        quality = float(supplier.quality_score) if supplier.total_pos > 0 else None
        riesgo_dev = float(supplier.return_rate) if supplier.total_pos > 0 else None
        if reliability is None:
            signals["unknown"].append("confiabilidad/calidad/devoluciones (proveedor sin POs medidas)")
        else:
            signals["fuente"]["scorecard"] = f"proveedor {supplier.id} ({supplier.total_pos} POs)"
    else:
        signals["unknown"].append("confiabilidad/calidad/devoluciones (sin proveedor)")
    snaps = engine.list_competitor_snapshots(product_id=product_id, limit=20)
    competencia = float(min(10.0, len(snaps))) if snaps else None
    if competencia is None:
        signals["unknown"].append("competencia (sin snapshots rivales: POST /products/{id}/competitors)")
    else:
        signals["fuente"]["competencia"] = f"{len(snaps)} snapshots rivales"
    signals["unknown"].extend(["demanda", "rotación", "logística (sin datos: neutral 5.0)"])
    gate = zero_capital_gate(supplier) if supplier is not None else {"status": "future", "reasons": ["sin proveedor"]}
    result = get_sourcing_engine().product_score(
        margin_pct=margin if margin > 0 else None,
        demand_0_10=None,
        competition_0_10=competencia,
        rotation_0_10=None,
        supplier_reliability_0_10=(reliability / 10.0) if reliability is not None else None,
        fulfillment_ease_0_10=(quality / 10.0) if quality is not None else None,
        ticket_usd=float(product.sale_price_usd or 0) or None,
        return_risk_0_10=(riesgo_dev / 10.0) if riesgo_dev is not None else None,
        capital_required_usd=float(supplier.capital_required_usd or 0) if supplier else 0.0,
        fulfillment_provider=(supplier.fulfillment == "provider") if supplier else False,
        stock_sync=bool(supplier.stock_sync) if supplier else False,
    )
    result["signals"] = signals
    result["zero_capital"] = gate
    return result


@router.get("/suppliers/ranked")
async def ecommerce_ranked_suppliers() -> dict[str, Any]:
    """Ranking $0 + ML: Dropsheable → Unidrop → Ventaz → Dropdeal → Caufy → IG."""
    from cores.ecommerce.engine import seed_ranked_suppliers
    from cores.ecommerce.models import zero_capital_gate

    ranked = seed_ranked_suppliers()
    return {
        "total": len(ranked),
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "website": s.website,
                "instagram": getattr(s, "instagram", ""),
                "reseller_program": bool(getattr(s, "reseller_program", False)),
                "capital_required_usd": float(s.capital_required_usd),
                "monthly_cost_usd": float(s.monthly_cost_usd),
                "ml_integrated": s.ml_integrated,
                "fulfillment": s.fulfillment,
                "fee_model": s.fee_model,
                "fee_pct": s.fee_pct,
                "stock_sync": s.stock_sync,
                "verified": s.verified,
                "zero_capital": zero_capital_gate(s),
                "notes": s.notes,
            }
            for s in ranked
        ],
    }


class CompetitorIn(BaseModel):
    competitor_prices: list[float] = Field(default_factory=list)
    source: str = "manual"
    competitor_stock: dict[str, bool] = Field(default_factory=dict)


@router.post("/products/{product_id}/competitors")
async def ecommerce_record_competitors(product_id: str, payload: CompetitorIn) -> dict[str, Any]:
    engine = get_ecommerce_engine()
    if not engine.get_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    snap = engine.record_competitor_snapshot(
        product_id,
        competitor_prices=payload.competitor_prices,
        source=payload.source,
        competitor_stock=payload.competitor_stock or None,
    )
    return {
        "success": True,
        "signal": snap.signal,
        "action": snap.action,
        "min_price": snap.min_price,
        "avg_price": snap.avg_price,
        "note": snap.note,
    }


@router.get("/products/{product_id}/competitors")
async def ecommerce_list_competitors(product_id: str) -> dict[str, Any]:
    engine = get_ecommerce_engine()
    snaps = engine.list_competitor_snapshots(product_id=product_id, limit=20)
    return {
        "total": len(snaps),
        "snapshots": [
            {
                "observed_at": s.observed_at.isoformat(),
                "signal": s.signal,
                "action": s.action,
                "min_price": s.min_price,
                "avg_price": s.avg_price,
                "source": s.source,
            }
            for s in snaps
        ],
    }


@router.get("/intel/competitors")
async def ecommerce_competitor_watch() -> dict[str, Any]:
    return run_ecommerce_competitor_watch()


@router.get("/intel/winners")
async def ecommerce_intel_winners(platform_fee_pct: float = 0.0) -> dict[str, Any]:
    """MATAR o ESCALAR por datos: neto/venta × ventas por producto + funnel."""
    engine = get_ecommerce_engine()
    perf = engine.product_performance(platform_fee_pct=platform_fee_pct)
    funnel = engine.portfolio_funnel(platform_fee_pct=platform_fee_pct)
    return {"total": len(perf), "products": perf[:100], "funnel": funnel}


@router.get("/intel/objectives")
async def ecommerce_intel_objectives(human_hours: float = 0.0, platform_fee_pct: float = 0.0) -> dict[str, Any]:
    """Objetivos O1-O6 del experimento + netos por hora humana."""
    return get_ecommerce_engine().experiment_objectives(human_hours=human_hours, platform_fee_pct=platform_fee_pct)


class RouteIn(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    supplier_offers: dict[str, dict[str, float]] = Field(default_factory=dict)
    supplier_meta: dict[str, dict[str, float]] = Field(default_factory=dict)


@router.post("/orders/route")
async def ecommerce_route_order(payload: RouteIn) -> dict[str, Any]:
    """Multi-supplier smart routing ($0, puro). Items sin oferta quedan en unrouted."""
    from decimal import Decimal

    items = []
    for raw in payload.items:
        try:
            items.append(
                OrderItem(
                    product_id=str(raw.get("product_id", "")),
                    listing_id=str(raw.get("listing_id", "")),
                    quantity=int(raw.get("quantity", 1) or 1),
                    unit_price_usd=Decimal(str(raw.get("unit_price_usd", 0) or 0)),
                    total_price_usd=Decimal(str(raw.get("total_price_usd", 0) or 0)),
                )
            )
        except Exception:
            continue
    return get_order_orchestrator().route_to_best_supplier(
        order_items=items,
        supplier_offers=payload.supplier_offers,
        supplier_meta=payload.supplier_meta,
    )


@router.post("/suppliers/scorecards/refresh")
async def ecommerce_refresh_scorecards() -> dict[str, Any]:
    return run_ecommerce_supplier_scorecards()


@router.get("/suppliers/scorecards")
async def ecommerce_supplier_scorecards() -> dict[str, Any]:
    engine = get_ecommerce_engine()
    rows = engine.list_suppliers(active_only=False)
    return {
        "total": len(rows),
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "fulfillment_rate": s.fulfillment_rate,
                "return_rate": s.return_rate,
                "quality_score": s.quality_score,
                "total_pos": s.total_pos,
            }
            for s in rows
        ],
    }


@router.post("/products/{product_id}/cross-list")
async def ecommerce_cross_list(product_id: str) -> dict[str, Any]:
    """Un producto -> listings adaptados Meli + IG + WA + TikTok ($0)."""
    engine = get_ecommerce_engine()
    product = engine.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    listings = get_listing_optimizer().optimize_for_all_channels(product)
    for channel, listing in listings.items():
        product.marketplace_listings[channel] = listing.id
    return {
        "success": True,
        "channels": sorted(listings.keys()),
        "titles": {ch: lst.title for ch, lst in listings.items()},
    }


@router.post("/products/{product_id}/content-plan")
async def ecommerce_content_plan(product_id: str, platform: str = "instagram") -> dict[str, Any]:
    """Script orgánico por producto para Shorts/Reels ($0, publicar = Human Gate)."""
    engine = get_ecommerce_engine()
    product = engine.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return get_content_planner().plan_product_content(product, platform=platform)


@router.get("/design/brief")
async def ecommerce_design_brief(niche: str = "perfumes") -> dict[str, Any]:
    """Brief de diseño IG $0: formatos, reglas y stack gratis. Sin red, sin costo."""
    from cores.ecommerce.design import design_brief

    return design_brief(niche)


@router.post("/design/flyer")
async def ecommerce_design_flyer(
    title: str = "",
    price_text: str = "",
    cta: str = "Pedilo por WhatsApp",
    size: str = "post",
    tag: str = "",
    image: UploadFile | None = None,
) -> Any:
    """Compone un flyer PNG desde una foto (multipart `image`). 100% local (Pillow)."""
    from fastapi.responses import Response

    from cores.ecommerce.design import IG_SIZES, make_flyer

    if size not in IG_SIZES:
        raise HTTPException(status_code=422, detail="size debe ser post|story|square|highlight")
    if image is None:
        raise HTTPException(status_code=422, detail="falta la foto (multipart image)")
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=422, detail="foto vacía")
    out = make_flyer(raw, title, price_text, cta=cta, size=size, tag=tag)
    if not out.get("success"):
        raise HTTPException(status_code=422, detail=str(out.get("error")))
    return Response(content=out["png"], media_type="image/png")


@router.get("/design/weekly-pack")
async def ecommerce_design_weekly_pack() -> dict[str, Any]:
    """Pack de 7 días desde el catálogo ACTIVE (rotación por nicho). Sin red."""
    from cores.ecommerce.design import weekly_pack
    from cores.ecommerce.models import ProductStatus
    from cores.ecommerce.outreach import niche_for

    engine = get_ecommerce_engine()
    items = [
        {
            "id": p.id,
            "name": p.name,
            "sale_price_usd": float(p.sale_price_usd or 0),
            "niche": niche_for(p.supplier_id, f"{p.name} {p.category}"),
        }
        for p in engine.list_products(status=ProductStatus.ACTIVE)[:24]
    ]
    return weekly_pack(items)


@router.get("/design/products/{product_id}/flyer-brief")
async def ecommerce_design_flyer_brief(product_id: str, size: str = "post") -> dict[str, Any]:
    """Copy del flyer armada desde señales reales (precio/bandas/tag/bloqueos).

    La foto la sube el humano (permiso del proveedor); todo lo demás sale solo.
    """
    from cores.ecommerce.design import IG_SIZES, product_flyer_brief

    if size not in IG_SIZES:
        raise HTTPException(status_code=422, detail="size debe ser post|story|square|highlight")
    engine = get_ecommerce_engine()
    product = engine.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product_flyer_brief(product, size=size)


def _queue_items() -> list[dict[str, Any]]:
    """Productos ACTIVE para la cola (misma fuente que el job semanal)."""
    from cores.ecommerce.pipeline import get_design_queue_items

    return get_design_queue_items()


@router.get("/design/queue")
async def ecommerce_design_queue() -> dict[str, Any]:
    """Cola de publicación: QUÉ toca cada día + estado. Se arma sola si está vacía."""
    from cores.ecommerce.publish_queue import get_publish_queue

    queue = get_publish_queue()
    if not queue.to_dict()["days"]:
        return queue.rebuild(_queue_items())
    return queue.to_dict()


@router.post("/design/queue/rebuild")
async def ecommerce_design_queue_rebuild() -> dict[str, Any]:
    """Regenera la semana preservando lo ya publicado."""
    from cores.ecommerce.publish_queue import get_publish_queue

    return get_publish_queue().rebuild(_queue_items())


@router.post("/design/queue/{dia}/publish")
async def ecommerce_design_queue_publish(dia: str) -> dict[str, Any]:
    """Marca un día como publicado (publicar lo hacés vos en IG)."""
    from cores.ecommerce.publish_queue import get_publish_queue

    row = get_publish_queue().mark_published(dia)
    if not row:
        raise HTTPException(status_code=404, detail=f"día desconocido: {dia}")
    return {"success": True, "day": row}


@router.post("/reviews/prepare")
async def ecommerce_prepare_reviews() -> dict[str, Any]:
    return run_ecommerce_review_request()


@router.get("/reviews")
async def ecommerce_list_reviews() -> dict[str, Any]:
    engine = get_ecommerce_engine()
    rows = engine.list_review_requests()
    return {
        "total": len(rows),
        "reviews": [
            {"id": r.id, "order_id": r.order_id, "status": r.status, "message": r.message[:200]} for r in rows[:100]
        ],
    }


class CartIn(BaseModel):
    visitor_id: str = ""
    product_id: str = ""
    marketplace: str = "mercadolibre"


@router.post("/carts/track")
async def ecommerce_track_cart(payload: CartIn) -> dict[str, Any]:
    if not payload.product_id.strip():
        raise HTTPException(status_code=422, detail="product_id is required")
    cart = get_ecommerce_engine().track_cart_view(
        visitor_id=payload.visitor_id, product_id=payload.product_id, marketplace=payload.marketplace
    )
    return {"success": True, "id": cart.id}


@router.get("/carts/abandoned")
async def ecommerce_abandoned_carts(minutes_idle: int = 30) -> dict[str, Any]:
    rows = get_ecommerce_engine().list_abandoned_carts(minutes_idle=minutes_idle)
    carts_out = [{"id": c.id, "product_id": c.product_id, "visitor_id": c.visitor_id} for c in rows[:100]]
    return {"total": len(rows), "carts": carts_out}


@router.get("/orders")
async def ecommerce_list_orders(status: str | None = None) -> dict[str, Any]:
    engine = get_ecommerce_engine()
    status_enum = None
    if status:
        try:
            status_enum = OrderStatus(status)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid status: {status}") from None
    orders = engine.list_orders(status=status_enum)
    out = []
    for order in orders[:100]:
        out.append(
            {
                "id": order.id,
                "marketplace": order.marketplace.value,
                "status": order.status.value,
                "total_usd": float(order.total_usd),
                "margin_usd": float(order.margin_usd),
                "next_action": get_order_orchestrator().next_action(order),
            }
        )
    return {"total": len(orders), "orders": out}


@router.get("/metrics")
async def ecommerce_metrics(days: int = 30) -> dict[str, Any]:
    engine = get_ecommerce_engine()
    end = datetime.now(UTC)
    start = end - timedelta(days=max(1, min(days, 365)))
    metrics = engine.calculate_metrics(start, end)
    return {
        "period_days": days,
        "total_orders": metrics.total_orders,
        "total_revenue_usd": float(metrics.total_revenue_usd),
        "total_margin_usd": float(metrics.total_margin_usd),
        "avg_margin_pct": metrics.avg_margin_pct,
        "avg_order_value_usd": float(metrics.avg_order_value_usd),
        "by_marketplace": metrics.by_marketplace,
        "top_products": metrics.top_products,
    }


@router.post("/sync/orders")
async def ecommerce_sync_orders() -> dict[str, Any]:
    return run_ecommerce_order_sync()


@router.get("/sync/health")
async def ecommerce_sync_health() -> dict[str, Any]:
    return run_ecommerce_listing_health()


@router.get("/storefront/preview")
async def ecommerce_storefront_preview(brand: str = "Droppinglabel", wa_number: str = "") -> Any:
    """Vidriera HTML desde ACTIVE reales (vacía honesta sin ACTIVE con precio)."""
    from fastapi.responses import HTMLResponse

    from cores.ecommerce.storefront import active_products_for_storefront, render_storefront

    engine = get_ecommerce_engine()
    products = active_products_for_storefront(engine)
    return HTMLResponse(render_storefront(products, brand=brand, wa_number=wa_number))


@router.post("/storefront/build")
async def ecommerce_storefront_build(brand: str = "Droppinglabel", wa_number: str = "") -> dict[str, Any]:
    """Genera index.html desplegable (Pages/Netlify) desde ACTIVE reales."""
    from cores.ecommerce.storefront import build_storefront_file

    return build_storefront_file(get_ecommerce_engine(), brand=brand, wa_number=wa_number)
