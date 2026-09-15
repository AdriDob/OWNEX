"""E-commerce API — Droppinglabel + MercadoLibre + IG/WA from OWNEX.

Zero-stock model: supplier -> customer. No fake data: adapters report
honest unavailable when credentials are missing; publishing needs human approval.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException
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
    api_endpoint: str = ""


class ProductIn(BaseModel):
    id: str
    sku: str
    name: str
    description: str = ""
    category: str = ""
    brand: str = ""
    supplier_id: str = ""
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
        api_endpoint=payload.api_endpoint,
    )
    engine.add_supplier(supplier)
    return {"success": True, "id": supplier.id}


@router.get("/suppliers")
async def ecommerce_list_suppliers() -> dict[str, Any]:
    engine = get_ecommerce_engine()
    suppliers = engine.list_suppliers(active_only=False)
    return {
        "total": len(suppliers),
        "suppliers": [{"id": s.id, "name": s.name, "type": s.type.value, "active": s.is_active} for s in suppliers],
    }


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
    engine = get_ecommerce_engine()
    product = Product(
        id=payload.id,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        brand=payload.brand,
        supplier_id=payload.supplier_id,
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
                "listings": p.marketplace_listings,
            }
            for p in products
        ],
    }


@router.post("/products/{product_id}/optimize")
async def ecommerce_optimize_listing(product_id: str, marketplace: str = "mercadolibre") -> dict[str, Any]:
    engine = get_ecommerce_engine()
    product = engine.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
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
    )


class PricingSuggestIn(BaseModel):
    cost_usd: float = 0.0
    competitor_prices: list[float] = Field(default_factory=list)
    target_margin_pct: float = 35.0
    shipping_usd: float = 0.0
    marketplace_fee_pct: float = 13.0


@router.post("/sourcing/suggest-price")
async def ecommerce_suggest_price(payload: PricingSuggestIn) -> dict[str, Any]:
    """Auto-pricing $0: floor por margen objetivo vs 95% del mínimo competidor."""
    return get_sourcing_engine().suggest_price(
        cost_usd=payload.cost_usd,
        competitor_prices=payload.competitor_prices,
        target_margin_pct=payload.target_margin_pct,
        shipping_usd=payload.shipping_usd,
        marketplace_fee_pct=payload.marketplace_fee_pct,
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


@router.get("/suppliers/ranked")
async def ecommerce_ranked_suppliers() -> dict[str, Any]:
    """Ranking $0 + ML: Dropsheable → Unidrop → Ventaz → Dropdeal → Caufy."""
    from cores.ecommerce.engine import seed_ranked_suppliers

    ranked = seed_ranked_suppliers()
    return {
        "total": len(ranked),
        "suppliers": [
            {
                "id": s.id,
                "name": s.name,
                "website": s.website,
                "capital_required_usd": float(s.capital_required_usd),
                "monthly_cost_usd": float(s.monthly_cost_usd),
                "ml_integrated": s.ml_integrated,
                "fulfillment": s.fulfillment,
                "fee_model": s.fee_model,
                "fee_pct": s.fee_pct,
                "stock_sync": s.stock_sync,
                "verified": s.verified,
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
