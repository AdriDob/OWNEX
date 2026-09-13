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
    OrderStatus,
    Product,
    ProductStatus,
    Supplier,
    SupplierType,
)
from cores.ecommerce.pipeline import (
    get_listing_optimizer,
    get_order_orchestrator,
    get_sourcing_engine,
    run_ecommerce_listing_health,
    run_ecommerce_order_sync,
)

router = APIRouter(prefix="/api/ecommerce", tags=["ecommerce"])


class SupplierIn(BaseModel):
    id: str
    name: str
    type: SupplierType = SupplierType.OTHER
    processing_time_days: int = 3
    is_active: bool = True


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
