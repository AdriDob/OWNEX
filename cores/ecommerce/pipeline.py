"""E-commerce pipeline — sourcing, listing optimization, orders, sync jobs.

Single module (budget): 4 small engines + 3 scheduler handlers.
All external calls are best-effort and never raise into the scheduler.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from cores.ecommerce.models import (
    Marketplace,
    MarketplaceListing,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductStatus,
    PurchaseOrder,
    get_default_subcategories,
)

logger = logging.getLogger("ownex.ecommerce.pipeline")

_STOPWORDS = {
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "de",
    "del",
    "en",
    "y",
    "con",
    "para",
    "the",
    "a",
    "an",
    "and",
    "with",
    "for",
    "of",
}


class SourcingEngine:
    """Supplier margin analysis (pure math, no network)."""

    def score_supplier_offer(
        self,
        cost_usd: float,
        sale_price_usd: float,
        processing_days: int = 3,
        shipping_usd: float = 0.0,
        marketplace_fee_pct: float = 13.0,
    ) -> dict[str, Any]:
        cost = Decimal(str(cost_usd))
        shipping = Decimal(str(shipping_usd))
        price = Decimal(str(sale_price_usd))
        fee = price * Decimal(str(marketplace_fee_pct)) / Decimal("100")
        total_cost = cost + shipping + fee
        margin = price - total_cost
        margin_pct = float(margin / price * 100) if price > 0 else 0.0
        verdict = "VIABLE" if margin_pct >= 25 and margin > 0 else "THIN" if margin > 0 else "REJECT"
        return {
            "cost_usd": float(cost),
            "shipping_usd": float(shipping),
            "fee_usd": float(fee),
            "total_cost_usd": float(total_cost),
            "margin_usd": float(margin),
            "margin_pct": round(margin_pct, 1),
            "processing_days": processing_days,
            "verdict": verdict,
            "note": "VIABLE exige margen ≥25% tras fees Meli (~13%) + envío.",
        }


class ListingOptimizer:
    """Deterministic SEO/copy optimizer (no LLM, no network)."""

    def optimize_title(self, name: str, brand: str = "", attributes: dict[str, str] | None = None) -> str:
        attrs = attributes or {}
        parts = [name.strip()]
        if brand:
            parts.append(brand.strip())
        for key in ("color", "talle", "size", "material", "capacidad"):
            val = str(attrs.get(key, "") or "").strip()
            if val:
                parts.append(val)
        title = " ".join(p for p in parts if p)
        title = re.sub(r"\s+", " ", title).strip()
        return title[:60]

    def build_keywords(self, product: Product) -> list[str]:
        words: list[str] = []
        blob = f"{product.name} {product.brand} {product.category} {' '.join(product.tags)}"
        for raw in re.split(r"[^a-zA-Záéíóúñü0-9]+", blob.lower()):
            token = raw.strip()
            if len(token) >= 4 and token not in _STOPWORDS and token not in words:
                words.append(token)
            if len(words) >= 12:
                break
        subs = get_default_subcategories(product.category)
        for sub in subs[:3]:
            if sub not in words:
                words.append(sub)
        return words[:12]

    def optimize_listing(self, product: Product, marketplace: Marketplace) -> MarketplaceListing:
        title = self.optimize_title(product.name, product.brand, product.attributes)
        keywords = self.build_keywords(product)
        desc = (product.description or product.short_description or "").strip()
        if keywords and len(desc) < 4000:
            desc = f"{desc}\n\nCaracterísticas: {', '.join(keywords[:8])}".strip()[:4000]
        return MarketplaceListing(
            id=f"{marketplace.value}:{product.id}",
            product_id=product.id,
            marketplace=marketplace,
            title=title,
            description=desc,
            price_usd=product.sale_price_usd,
            price_local=product.sale_price_ars or product.sale_price_usd,
            currency="ARS" if product.sale_price_ars > 0 else product.currency,
            quantity=1,
            images=list(product.images or [])[:6],
            attributes=dict(product.attributes or {}),
        )


class OrderOrchestrator:
    """Zero-stock fulfillment: customer order -> supplier purchase -> tracking."""

    def build_purchase_order(
        self, supplier_id: str, orders: list[Order], product_cost: dict[str, float]
    ) -> PurchaseOrder:
        items: list[OrderItem] = []
        order_ids: list[str] = []
        for order in orders:
            order_ids.append(order.id)
            for item in order.items:
                unit_cost = Decimal(str(product_cost.get(item.product_id, 0.0)))
                total_cost = unit_cost * item.quantity
                items.append(
                    OrderItem(
                        product_id=item.product_id,
                        listing_id=item.listing_id,
                        quantity=item.quantity,
                        unit_price_usd=item.unit_price_usd,
                        unit_cost_usd=unit_cost,
                        total_price_usd=item.total_price_usd,
                        total_cost_usd=total_cost,
                        margin_usd=item.total_price_usd - total_cost,
                    )
                )
        po = PurchaseOrder(
            id=f"po_{supplier_id}_{int(datetime.now(UTC).timestamp())}",
            supplier_id=supplier_id,
            order_ids=order_ids,
            items=items,
        )
        po.calculate_totals()
        return po

    def next_action(self, order: Order) -> str:
        mapping = {
            OrderStatus.PENDING: "Confirmar pago y stock del proveedor",
            OrderStatus.CONFIRMED: "Emitir purchase order al proveedor",
            OrderStatus.PROCESSING: "Esperar tracking del proveedor",
            OrderStatus.PURCHASED_FROM_SUPPLIER: "Cargar tracking y avisar al cliente",
            OrderStatus.SHIPPED: "Monitorear entrega",
            OrderStatus.DELIVERED: "Pedir review + registrar PAID real",
            OrderStatus.CANCELLED: "Sin acción",
            OrderStatus.RETURNED: "Gestionar reembolso",
            OrderStatus.REFUNDED: "Sin acción",
            OrderStatus.DISPUTED: "Responder disputa con evidencia",
        }
        return mapping.get(order.status, "Revisar manualmente")


_sourcing: SourcingEngine | None = None
_optimizer: ListingOptimizer | None = None
_orchestrator: OrderOrchestrator | None = None


def get_sourcing_engine() -> SourcingEngine:
    global _sourcing
    if _sourcing is None:
        _sourcing = SourcingEngine()
    return _sourcing


def get_listing_optimizer() -> ListingOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = ListingOptimizer()
    return _optimizer


def get_order_orchestrator() -> OrderOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrderOrchestrator()
    return _orchestrator


# ── Scheduler handlers (dotted-path, never raise) ──


def run_ecommerce_order_sync() -> dict[str, Any]:
    """Poll Meli recent orders and mirror new ones (best-effort)."""
    try:
        import asyncio

        from cores.ecommerce.adapters import get_meli_adapter
        from cores.ecommerce.engine import get_ecommerce_engine

        async def _run() -> dict[str, Any]:
            adapter = get_meli_adapter()
            if not adapter.is_available():
                return {"success": True, "synced": 0, "reason": "meli_not_configured"}
            result = await adapter.list_orders_recent(limit=20)
            if not result.get("success"):
                return {"success": True, "synced": 0, "reason": str(result.get("error", "unknown"))}
            engine = get_ecommerce_engine()
            synced = 0
            for raw in result.get("orders", []):
                ext_id = str(raw.get("id", ""))
                if not ext_id or engine.get_order_by_external_id(Marketplace.MERCADOLIBRE, ext_id):
                    continue
                total = float(raw.get("total_amount", 0.0) or 0.0)
                order = Order(
                    id=f"meli_{ext_id}",
                    marketplace=Marketplace.MERCADOLIBRE,
                    external_id=ext_id,
                    customer_id=str((raw.get("buyer") or {}).get("id", "")),
                    subtotal_usd=Decimal(str(total)),
                    total_usd=Decimal(str(total)),
                    status=OrderStatus.PENDING,
                )
                engine.add_order(order)
                engine.log_sync("order", order.id, Marketplace.MERCADOLIBRE, "sync", "success", {})
                synced += 1
            return {"success": True, "synced": synced}

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return {"success": True, "synced": 0, "reason": "event_loop_busy_retry_next_tick"}
        return asyncio.run(_run())
    except Exception as exc:
        logger.warning("ecommerce order sync failed: %s", exc)
        return {"success": False, "error": "sync_failed", "synced": 0}


def run_ecommerce_listing_health() -> dict[str, Any]:
    """Report listing health from local state (no network)."""
    try:
        from cores.ecommerce.engine import get_ecommerce_engine

        engine = get_ecommerce_engine()
        products = engine.list_products(status=ProductStatus.ACTIVE)
        without_listing = [p.id for p in products if not p.marketplace_listings]
        return {
            "success": True,
            "active_products": len(products),
            "without_listing": len(without_listing),
            "sample_ids": without_listing[:10],
        }
    except Exception as exc:
        logger.warning("ecommerce listing health failed: %s", exc)
        return {"success": False, "error": "health_failed"}


def get_ecommerce_jobs() -> list:
    """Job definitions for the ecommerce cycle (imported lazily by scheduler)."""
    from cores.scheduler.jobs import _cron_job

    return [
        _cron_job(
            job_id="ecommerce_order_sync",
            app_id="ecommerce",
            handler="cores.ecommerce.pipeline:run_ecommerce_order_sync",
            cron="*/15 * * * *",
            args=[],
            metadata={"cycle": "ecommerce", "type": "sync", "desc": "sincroniza ordenes Meli cada 15m"},
        ),
        _cron_job(
            job_id="ecommerce_listing_health",
            app_id="ecommerce",
            handler="cores.ecommerce.pipeline:run_ecommerce_listing_health",
            cron="30 7 * * *",
            args=[],
            metadata={"cycle": "ecommerce", "type": "health", "desc": "salud de listings diaria 07:30"},
        ),
    ]
