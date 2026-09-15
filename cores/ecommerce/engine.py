"""E-commerce Engine — core orchestration for multi-channel operations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from cores.ecommerce.models import (
    AbandonedCart,
    CompetitorSnapshot,
    EcommerceMetrics,
    Marketplace,
    Order,
    OrderStatus,
    PaymentStatus,
    Product,
    ProductStatus,
    PurchaseOrder,
    ReviewRequest,
    Supplier,
    SupplierType,
    SyncLog,
)

logger = logging.getLogger("ownex.ecommerce.engine")


def _suppliers_store_path():
    import os as _os
    from pathlib import Path as _Path

    base = _Path(_os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "ecommerce_suppliers.json"


def seed_ranked_suppliers() -> list[Supplier]:
    """Proveedores rankeados para modelo $0 + Mercado Libre (verificado 2026-09-15).

    Orden: Dropsheable (principal, $0 total) → Unidrop (excelente, abono ML) →
    Ventaz (simple, verificar margen) → Dropdeal (backup, suscripción) →
    Caufy (complementario, sin ML publicado). Datos declarados por cada
    plataforma; verificar acuerdo comercial antes de publicar (verified=False).
    """
    return [
        Supplier(
            id="dropsheable",
            name="Dropsheable",
            type=SupplierType.LOCAL_AR,
            website="https://www.dropsheable.com.ar",
            capital_required_usd=Decimal("0"),
            monthly_cost_usd=Decimal("0"),
            ml_integrated=True,
            fulfillment="provider",
            fee_model="per_sale_pct",
            fee_pct=3.0,
            stock_sync=True,
            verified=False,
            notes="+500 proveedores, importación/publicación ML, pedido automático. Principal.",
        ),
        Supplier(
            id="unidrop",
            name="Unidrop",
            type=SupplierType.LOCAL_AR,
            website="https://www.unidrop.com.ar",
            capital_required_usd=Decimal("0"),
            monthly_cost_usd=Decimal("22"),
            ml_integrated=True,
            fulfillment="provider",
            fee_model="monthly",
            fee_pct=0.0,
            stock_sync=True,
            verified=False,
            notes="Depósito propio Unistore, 1200+ productos, Flex/Colecta. $0 stock pero abono ML ~USD22 → alternativa, no $0 total.",
        ),
        Supplier(
            id="ventaz",
            name="Ventaz",
            type=SupplierType.LOCAL_AR,
            website="https://ventaz.com.ar",
            capital_required_usd=Decimal("0"),
            monthly_cost_usd=Decimal("0"),
            ml_integrated=True,
            fulfillment="provider",
            fee_model="none",
            fee_pct=0.0,
            stock_sync=True,
            verified=False,
            notes="Ellos compran/almacenan/preparan/envían. Verificar margen efectivo y flujo de pago antes de primaria.",
        ),
        Supplier(
            id="dropdeal",
            name="Dropdeal",
            type=SupplierType.LOCAL_AR,
            website="https://dropdeal.ar",
            capital_required_usd=Decimal("0"),
            monthly_cost_usd=Decimal("0"),
            ml_integrated=True,
            fulfillment="provider",
            fee_model="hybrid",
            fee_pct=0.0,
            stock_sync=True,
            verified=False,
            notes="Miles de productos + automatización. Suscripción tras período gratis → backup.",
        ),
        Supplier(
            id="caufy",
            name="Caufy",
            type=SupplierType.LOCAL_AR,
            website="https://caufy.com.ar",
            capital_required_usd=Decimal("0"),
            monthly_cost_usd=Decimal("0"),
            ml_integrated=False,
            fulfillment="provider",
            fee_model="none",
            fee_pct=0.0,
            stock_sync=True,
            verified=False,
            notes="Paga al vender+cobrar. Sin ML publicado (Tiendanube/Shopify/Woo) → complementario + CaufyPrint POD.",
        ),
    ]


class EcommerceEngine:
    """Central engine coordinating all e-commerce operations."""

    def __init__(self) -> None:
        self._suppliers: dict[str, Supplier] = {}
        self._products: dict[str, Product] = {}
        self._orders: dict[str, Order] = {}
        self._purchase_orders: dict[str, PurchaseOrder] = {}
        self._sync_logs: list[SyncLog] = []
        self._competitor_snaps: list[CompetitorSnapshot] = []
        self._reviews: dict[str, ReviewRequest] = {}
        self._carts: dict[str, AbandonedCart] = {}
        self._initialized = False
        # Load persisted suppliers if any (100 AR Meli-only)
        try:
            self._load_suppliers()
        except Exception:
            pass

    def _load_suppliers(self):
        import json as _json

        p = _suppliers_store_path()
        if not p.exists():
            return
        try:
            data = _json.loads(p.read_text(encoding="utf-8"))
            for raw in data.get("suppliers", []):
                try:
                    raw["type"] = SupplierType(raw.get("type", "other"))
                except Exception:
                    raw["type"] = SupplierType.OTHER
                try:
                    raw["minimum_order_usd"] = __import__("decimal").Decimal(str(raw.get("minimum_order_usd", "0")))
                except Exception:
                    raw["minimum_order_usd"] = __import__("decimal").Decimal("0")
                try:
                    raw["commission_rate"] = __import__("decimal").Decimal(str(raw.get("commission_rate", "0")))
                except Exception:
                    raw["commission_rate"] = __import__("decimal").Decimal("0")
                try:
                    raw["capital_required_usd"] = __import__("decimal").Decimal(
                        str(raw.get("capital_required_usd", "0"))
                    )
                except Exception:
                    pass
                try:
                    raw["monthly_cost_usd"] = __import__("decimal").Decimal(str(raw.get("monthly_cost_usd", "0")))
                except Exception:
                    pass
                s = Supplier(**{k: v for k, v in raw.items() if k in Supplier.__dataclass_fields__})
                self._suppliers[s.id] = s
        except Exception as exc:
            logger.warning("Could not load suppliers: %s", exc)

    def _save_suppliers(self):
        import json as _json

        p = _suppliers_store_path()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {"suppliers": [self._supplier_to_dict(s) for s in self._suppliers.values()]}
            p.write_text(_json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not save suppliers: %s", exc)

    def _supplier_to_dict(self, s: Supplier):
        return {
            "id": s.id,
            "name": s.name,
            "type": s.type.value if hasattr(s.type, "value") else str(s.type),
            "website": s.website,
            "api_endpoint": s.api_endpoint,
            "commission_rate": str(s.commission_rate),
            "processing_time_days": s.processing_time_days,
            "is_active": s.is_active,
            "notes": s.notes,
        }

    def initialize(self) -> None:
        """Initialize adapters and load persisted data."""
        if self._initialized:
            return
        try:
            from cores.ecommerce.adapters import get_ig_wa_adapter, get_meli_adapter
            from cores.ecommerce.pipeline import (
                get_listing_optimizer,
                get_order_orchestrator,
                get_sourcing_engine,
            )

            get_meli_adapter()
            get_ig_wa_adapter()
            get_sourcing_engine()
            get_listing_optimizer()
            get_order_orchestrator()
            self._initialized = True
            logger.info("E-commerce engine initialized")
        except Exception as exc:
            logger.exception("Failed to initialize e-commerce engine: %s", exc)

    # --- Supplier Management ---

    def add_supplier(self, supplier: Supplier) -> Supplier:
        self._suppliers[supplier.id] = supplier
        logger.info("Added supplier: %s (%s)", supplier.name, supplier.id)
        try:
            self._save_suppliers()
        except Exception:
            pass
        return supplier

    def get_supplier(self, supplier_id: str) -> Supplier | None:
        return self._suppliers.get(supplier_id)

    def list_suppliers(self, active_only: bool = True) -> list[Supplier]:
        suppliers = list(self._suppliers.values())
        if active_only:
            suppliers = [s for s in suppliers if s.is_active]
        return suppliers

    def update_supplier(self, supplier_id: str, **kwargs) -> Supplier | None:
        supplier = self._suppliers.get(supplier_id)
        if not supplier:
            return None
        for key, value in kwargs.items():
            if hasattr(supplier, key):
                setattr(supplier, key, value)
        supplier.updated_at = datetime.now(UTC)
        try:
            self._save_suppliers()
        except Exception:
            pass
        return supplier

    async def sync_supplier_catalog(self, supplier_id: str, limit: int = 50) -> dict[str, Any]:
        """Mirror a supplier website catalog into DRAFT products (review before sell).

        New/updated items enter as DRAFT: nothing auto-publishes to Meli.
        Human promotes to ACTIVE + sets price (via /sourcing/score) + approves
        the Meli payload. Never raises; failures are reported, not hidden.
        """
        supplier = self.get_supplier(supplier_id)
        if supplier is None:
            return {"success": False, "error": "unknown_supplier", "synced": 0, "updated": 0}
        if not supplier.is_active:
            return {"success": False, "error": "supplier_inactive", "synced": 0, "updated": 0}
        from cores.ecommerce.adapters import SupplierCatalogAdapter

        result = await SupplierCatalogAdapter(supplier).fetch_catalog(limit=limit)
        if not result.get("success"):
            self.log_sync("product", supplier_id, Marketplace.OTHER, "catalog_sync", "failed", result)
            return {**result, "synced": 0, "updated": 0}
        synced, updated = 0, 0
        for item in result.get("items", []):
            pid = f"{supplier_id}:{item['sku'] or item['name'][:40]}"
            existing = self._products.get(pid)
            cost = Decimal(str(item["price"]))
            if existing is not None:
                existing.cost_usd = cost
                existing.calculate_margin()
                existing.calculate_roi()
                existing.updated_at = datetime.now(UTC)
                updated += 1
                continue
            self.add_product(
                Product(
                    id=pid,
                    sku=item["sku"],
                    name=item["name"],
                    description=item["description"],
                    supplier_id=supplier_id,
                    cost_usd=cost,
                    currency=item["currency"],
                    images=item["images"],
                    status=ProductStatus.DRAFT,
                )
            )
            synced += 1
        summary = {"success": True, "synced": synced, "updated": updated, "skipped": result.get("skipped", 0)}
        self.log_sync("product", supplier_id, Marketplace.OTHER, "catalog_sync", "success", summary)
        return summary

    # --- Product Management ---

    def add_product(self, product: Product) -> Product:
        product.calculate_margin()
        product.calculate_roi()
        self._products[product.id] = product
        logger.info("Added product: %s (%s)", product.name, product.id)
        return product

    def get_product(self, product_id: str) -> Product | None:
        return self._products.get(product_id)

    def get_product_by_sku(self, sku: str) -> Product | None:
        for p in self._products.values():
            if p.sku == sku:
                return p
        return None

    def list_products(
        self,
        status: ProductStatus | None = None,
        category: str | None = None,
        supplier_id: str | None = None,
        marketplace: Marketplace | None = None,
    ) -> list[Product]:
        products = list(self._products.values())
        if status:
            products = [p for p in products if p.status == status]
        if category:
            products = [p for p in products if p.category == category]
        if supplier_id:
            products = [p for p in products if p.supplier_id == supplier_id]
        if marketplace:
            products = [p for p in products if marketplace.value in p.marketplace_listings]
        return products

    def update_product(self, product_id: str, **kwargs) -> Product | None:
        product = self._products.get(product_id)
        if not product:
            return None
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        product.calculate_margin()
        product.calculate_roi()
        product.updated_at = datetime.now(UTC)
        return product

    def delete_product(self, product_id: str) -> bool:
        if product_id in self._products:
            del self._products[product_id]
            return True
        return False

    # --- Order Management ---

    def add_order(self, order: Order) -> Order:
        order.calculate_totals()
        self._orders[order.id] = order
        logger.info("Added order: %s (%s)", order.id, order.marketplace.value)
        return order

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_order_by_external_id(self, marketplace: Marketplace, external_id: str) -> Order | None:
        for order in self._orders.values():
            if order.marketplace == marketplace and order.external_id == external_id:
                return order
        return None

    def list_orders(
        self,
        status: OrderStatus | None = None,
        marketplace: Marketplace | None = None,
        customer_id: str | None = None,
        since: datetime | None = None,
    ) -> list[Order]:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        if marketplace:
            orders = [o for o in orders if o.marketplace == marketplace]
        if customer_id:
            orders = [o for o in orders if o.customer_id == customer_id]
        if since:
            orders = [o for o in orders if o.created_at >= since]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    def update_order_status(self, order_id: str, status: OrderStatus) -> Order | None:
        order = self._orders.get(order_id)
        if not order:
            return None
        order.status = status
        order.updated_at = datetime.now(UTC)
        if status == OrderStatus.CONFIRMED and not order.confirmed_at:
            order.confirmed_at = datetime.now(UTC)
        elif status == OrderStatus.SHIPPED and not order.shipped_at:
            order.shipped_at = datetime.now(UTC)
        elif status == OrderStatus.DELIVERED and not order.delivered_at:
            order.delivered_at = datetime.now(UTC)
        return order

    # --- Purchase Order Management ---

    def add_purchase_order(self, po: PurchaseOrder) -> PurchaseOrder:
        po.calculate_totals()
        self._purchase_orders[po.id] = po
        logger.info("Added purchase order: %s for supplier %s", po.id, po.supplier_id)
        return po

    def get_purchase_order(self, po_id: str) -> PurchaseOrder | None:
        return self._purchase_orders.get(po_id)

    def list_purchase_orders(
        self,
        supplier_id: str | None = None,
        status: OrderStatus | None = None,
    ) -> list[PurchaseOrder]:
        pos = list(self._purchase_orders.values())
        if supplier_id:
            pos = [po for po in pos if po.supplier_id == supplier_id]
        if status:
            pos = [po for po in pos if po.status == status]
        return pos

    # --- Sync Logging ---

    def log_sync(
        self,
        entity_type: str,
        entity_id: str,
        marketplace: Marketplace,
        action: str,
        status: str,
        details: dict[str, Any] | None = None,
        error_message: str = "",
    ) -> SyncLog:
        sync_log = SyncLog(
            id=f"sync_{entity_type}_{entity_id}_{datetime.now(UTC).timestamp()}",
            entity_type=entity_type,
            entity_id=entity_id,
            marketplace=marketplace,
            action=action,
            status=status,
            details=details or {},
            error_message=error_message,
        )
        self._sync_logs.append(sync_log)
        return sync_log

    def get_sync_logs(
        self,
        entity_type: str | None = None,
        marketplace: Marketplace | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SyncLog]:
        logs = self._sync_logs
        if entity_type:
            logs = [entry for entry in logs if entry.entity_type == entity_type]
        if marketplace:
            logs = [entry for entry in logs if entry.marketplace == marketplace]
        if since:
            logs = [entry for entry in logs if entry.created_at >= since]
        return sorted(logs, key=lambda entry: entry.created_at, reverse=True)[:limit]

    # --- Metrics ---

    def calculate_metrics(self, period_start: datetime, period_end: datetime) -> EcommerceMetrics:
        orders = [o for o in self._orders.values() if period_start <= o.created_at <= period_end]

        if not orders:
            return EcommerceMetrics(period_start=period_start, period_end=period_end)

        total_revenue = sum((o.total_usd for o in orders), Decimal("0"))
        total_cost = sum((o.total_cost_usd for o in orders), Decimal("0"))
        total_margin = sum((o.margin_usd for o in orders), Decimal("0"))

        metrics = EcommerceMetrics(
            period_start=period_start,
            period_end=period_end,
            total_orders=len(orders),
            total_revenue_usd=total_revenue,
            total_cost_usd=total_cost,
            total_margin_usd=total_margin,
            avg_margin_pct=float(total_margin / total_revenue * 100) if total_revenue > 0 else 0.0,
            avg_order_value_usd=total_revenue / len(orders) if orders else Decimal("0"),
        )

        # By marketplace
        for mp in Marketplace:
            mp_orders = [o for o in orders if o.marketplace == mp]
            if mp_orders:
                mp_revenue = sum((o.total_usd for o in mp_orders), Decimal("0"))
                mp_margin = sum((o.margin_usd for o in mp_orders), Decimal("0"))
                metrics.by_marketplace[mp.value] = {
                    "orders": len(mp_orders),
                    "revenue_usd": float(mp_revenue),
                    "margin_usd": float(mp_margin),
                    "margin_pct": float(mp_margin / mp_revenue * 100) if mp_revenue > 0 else 0.0,
                }

        # Top products
        product_revenue: dict[str, Decimal] = {}
        for order in orders:
            for item in order.items:
                product_revenue[item.product_id] = (
                    product_revenue.get(item.product_id, Decimal("0")) + item.total_price_usd
                )

        top_products = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)[:10]
        metrics.top_products = [{"product_id": pid, "revenue_usd": float(rev)} for pid, rev in top_products]

        return metrics

    # ── Competitor snapshots (Fase 1, public data, human/job fed) ──

    def record_competitor_snapshot(
        self,
        product_id: str,
        competitor_prices: list[float],
        source: str = "manual",
        competitor_stock: dict[str, bool] | None = None,
    ) -> CompetitorSnapshot:
        from cores.ecommerce.pipeline import get_competitor_watch

        product = self._products.get(product_id)
        ours = float(product.sale_price_usd) if product else 0.0
        verdict = get_competitor_watch().evaluate(
            our_price_usd=ours,
            competitor_prices=competitor_prices,
            competitor_stock=competitor_stock,
        )
        comps = [float(p) for p in (competitor_prices or []) if isinstance(p, (int, float)) and p > 0]
        snap = CompetitorSnapshot(
            id=f"comp_{product_id}_{int(datetime.now(UTC).timestamp())}",
            product_id=product_id,
            competitor_prices=comps,
            min_price=min(comps) if comps else 0.0,
            avg_price=(sum(comps) / len(comps)) if comps else 0.0,
            signal=str(verdict.get("signal", "UNKNOWN")),
            action=str(verdict.get("action", "sin_datos_suficientes")),
            source=source,
            note=str(verdict.get("note", "")),
        )
        self._competitor_snaps.append(snap)
        self._competitor_snaps = self._competitor_snaps[-500:]
        return snap

    def list_competitor_snapshots(self, product_id: str | None = None, limit: int = 100) -> list[CompetitorSnapshot]:
        snaps = list(self._competitor_snaps)
        if product_id:
            snaps = [s for s in snaps if s.product_id == product_id]
        return sorted(snaps, key=lambda s: s.observed_at, reverse=True)[: max(1, min(limit, 500))]

    # ── Supplier scorecards (Fase 3, $0 desde historial local) ──

    def update_supplier_scorecards(self) -> int:
        updated = 0
        for supplier in self._suppliers.values():
            pos = [po for po in self._purchase_orders.values() if po.supplier_id == supplier.id]
            if not pos:
                continue
            shipped = sum(1 for po in pos if po.status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED))
            supplier.total_pos = len(pos)
            supplier.fulfillment_rate = round(shipped / len(pos) * 100, 1) if pos else 0.0
            # return_rate desde orders ligadas a este supplier vía product.supplier_id
            supplier_orders = [
                o
                for o in self._orders.values()
                if any(
                    (self._products.get(it.product_id) or Product(id="", sku="", name="")).supplier_id == supplier.id
                    for it in o.items
                )
            ]
            if supplier_orders:
                bad = sum(1 for o in supplier_orders if o.status in (OrderStatus.RETURNED, OrderStatus.REFUNDED))
                supplier.return_rate = round(bad / len(supplier_orders) * 100, 1)
            # quality composite honesto: fulfillment - returns + rating normalizado
            try:
                rating_part = max(0.0, min(100.0, float(supplier.rating or 0.0) * 20.0))
            except (TypeError, ValueError):
                rating_part = 0.0
            supplier.quality_score = round(
                max(0.0, min(100.0, supplier.fulfillment_rate * 0.6 + rating_part * 0.3 - supplier.return_rate * 0.5)),
                1,
            )
            supplier.avg_shipping_days = float(supplier.processing_time_days or 0)
            supplier.last_score_at = datetime.now(UTC)
            supplier.updated_at = datetime.now(UTC)
            updated += 1
        return updated

    # ── Reviews + carts (Fase 6, prepara, nunca envía solo) ──

    def prepare_review_requests(self, days_after_delivery: int = 10) -> int:
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(days=max(1, days_after_delivery))
        prepared = 0
        for order in self._orders.values():
            if order.status != OrderStatus.DELIVERED or not order.delivered_at:
                continue
            if order.delivered_at > cutoff:
                continue
            if any(r.order_id == order.id for r in self._reviews.values()):
                continue
            msg = (
                f"¡Hola! Gracias por tu compra ({order.id}) 🙏 "
                "¿Qué tal tu producto? Tu opinión + foto ayuda a otros compradores. "
                "Respondé este mensaje con tu review y te damos 10% OFF en la próxima 🎁"
            )
            rr = ReviewRequest(
                id=f"rev_{order.id}",
                order_id=order.id,
                channel="whatsapp",
                template="review_default",
                message=msg,
                status="prepared",
            )
            self._reviews[rr.id] = rr
            prepared += 1
        return prepared

    def list_review_requests(self, status: str | None = None) -> list[ReviewRequest]:
        rows = list(self._reviews.values())
        if status:
            rows = [r for r in rows if r.status == status]
        return sorted(rows, key=lambda r: r.created_at, reverse=True)[:200]

    def track_cart_view(self, visitor_id: str, product_id: str, marketplace: str = "mercadolibre") -> AbandonedCart:
        cart = AbandonedCart(
            id=f"cart_{(visitor_id or 'anon')[:24]}_{product_id}_{int(datetime.now(UTC).timestamp())}",
            visitor_id=(visitor_id or "")[:64],
            product_id=product_id,
            marketplace=marketplace,
        )
        self._carts[cart.id] = cart
        return cart

    def list_abandoned_carts(self, minutes_idle: int = 30) -> list[AbandonedCart]:
        from datetime import timedelta

        cutoff = datetime.now(UTC) - timedelta(minutes=max(1, minutes_idle))
        return sorted(
            [c for c in self._carts.values() if not c.recovered and c.viewed_at <= cutoff],
            key=lambda c: c.viewed_at,
        )[:200]

    def mark_cart_recovered(self, cart_id: str) -> AbandonedCart | None:
        cart = self._carts.get(cart_id)
        if not cart:
            return None
        cart.recovered = True
        cart.recovery_sent_at = datetime.now(UTC)
        return cart

    # ── Performance MATAR/ESCALAR + objetivos O1-O6 (datos reales, $0) ──

    def _sold_orders(self) -> list[Order]:
        """Orders that count as sales (CANCELLED never sold anything)."""
        return [o for o in self._orders.values() if o.status != OrderStatus.CANCELLED]

    def product_performance(self, platform_fee_pct: float = 0.0) -> list[dict[str, Any]]:
        """Net per sale × sales per product → verdict MATAR/ESCALAR.

        Ventanas fijas 30/60 días (contrato del clasificador).
        platform_fee_pct: fee plataforma no registrado en la orden
        (Dropsheable declara 3%). 0.0 = neto observado sin asumir nada.
        """
        from datetime import timedelta

        from cores.ecommerce.pipeline import get_product_performance

        now = datetime.now(UTC)
        cutoff_30 = now - timedelta(days=30)
        cutoff_60 = now - timedelta(days=60)
        try:
            fee_rate = max(0.0, float(platform_fee_pct or 0.0)) / 100.0
        except (TypeError, ValueError):
            fee_rate = 0.0
        classifier = get_product_performance()
        rows: list[dict[str, Any]] = []
        for product in self._products.values():
            if product.status == ProductStatus.DISCONTINUED:
                continue
            items = [it for o in self._sold_orders() for it in o.items if it.product_id == product.id]
            s30 = sum(
                it.quantity
                for o in self._sold_orders()
                for it in o.items
                if it.product_id == product.id and o.created_at >= cutoff_30
            )
            s60 = sum(
                it.quantity
                for o in self._sold_orders()
                for it in o.items
                if it.product_id == product.id and o.created_at >= cutoff_60
            )
            revenue = sum((float(it.total_price_usd) for it in items), 0.0)
            gross = sum((float(it.margin_usd) for it in items), 0.0)
            net = round(gross - revenue * fee_rate, 2)
            sales_total = sum(it.quantity for it in items)
            net_per_sale = round(net / sales_total, 2) if sales_total else 0.0
            days_live = max(0, (now - product.created_at).days) if product.created_at else 0
            verdict = classifier.classify(sales_30d=s30, sales_60d=s60, net_per_sale=net_per_sale, days_live=days_live)
            rows.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "status": product.status.value,
                    "sales_30d": s30,
                    "sales_60d": s60,
                    "sales_total": sales_total,
                    "net_total": net,
                    "net_per_sale": net_per_sale,
                    "days_live": days_live,
                    "verdict": verdict["verdict"],
                    "action": verdict["action"],
                    "note": verdict["note"],
                }
            )
        rows.sort(key=lambda r: (r["net_total"], r["sales_30d"]), reverse=True)
        return rows[:500]

    def portfolio_funnel(self, platform_fee_pct: float = 0.0) -> dict[str, Any]:
        """100 pubs → cuántas venden / son ganadoras / hay que matar."""
        perf = self.product_performance(platform_fee_pct=platform_fee_pct)
        by_verdict: dict[str, int] = {}
        for row in perf:
            by_verdict[row["verdict"]] = by_verdict.get(row["verdict"], 0) + 1
        winners = [r for r in perf if r["verdict"] == "ESCALAR"]
        return {
            "publications": len(perf),
            "by_verdict": by_verdict,
            "winners": len(winners),
            "winners_monthly_net": round(sum(r["net_total"] for r in winners), 2),
            "to_kill": by_verdict.get("MATAR", 0),
            "in_testing": by_verdict.get("TESTING", 0),
            "note": "Estructura que escala: pocos ganadores con rotación, no miles de pubs.",
        }

    def experiment_objectives(self, human_hours: float = 0.0, platform_fee_pct: float = 0.0) -> dict[str, Any]:
        """Objetivos O1-O6 del experimento + ganancia neta por hora humana.

        human_hours = horas humanas invertidas (las informa el humano, nunca
        se inventan). 0 → net_per_human_hour None (UNKNOWN honesto).
        """
        sold = self._sold_orders()
        sales_total = sum(it.quantity for o in sold for it in o.items)
        collected = [o for o in sold if o.status == OrderStatus.DELIVERED and o.payment_status == PaymentStatus.PAID]
        collected_units = sum(it.quantity for o in collected for it in o.items)
        try:
            fee_rate = max(0.0, float(platform_fee_pct or 0.0)) / 100.0
        except (TypeError, ValueError):
            fee_rate = 0.0
        revenue = sum((float(o.total_usd) for o in sold), 0.0)
        gross = sum((float(o.margin_usd) for o in sold), 0.0)
        net_total = round(gross - revenue * fee_rate, 2)
        try:
            hours = max(0.0, float(human_hours or 0.0))
        except (TypeError, ValueError):
            hours = 0.0
        winners = [
            r["product_id"]
            for r in self.product_performance(platform_fee_pct=platform_fee_pct)
            if r["verdict"] == "ESCALAR"
        ]
        return {
            "o1_first_sale": sales_total >= 1,
            "o2_first_fulfilled_collected": collected_units >= 1,
            "o3_five_sales": sales_total >= 5,
            "o4_ten_sales": sales_total >= 10,
            "o5_net_per_human_hour_known": hours > 0 and sales_total > 0,
            "o6_scale_winners": winners,
            "sales_total": sales_total,
            "collected_units": collected_units,
            "net_total": net_total,
            "net_per_human_hour": round(net_total / hours, 2) if hours > 0 else None,
            "human_hours": hours,
            "note": "Con tus ventas, tus proveedores y tus precios: este canal produce X netos por hora humana.",
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "initialized": self._initialized,
            "suppliers": len(self._suppliers),
            "products": len(self._products),
            "orders": len(self._orders),
            "purchase_orders": len(self._purchase_orders),
            "active_products": len([p for p in self._products.values() if p.status == ProductStatus.ACTIVE]),
            "pending_orders": len([o for o in self._orders.values() if o.status == OrderStatus.PENDING]),
            "sync_logs": len(self._sync_logs),
            "competitor_snapshots": len(self._competitor_snaps),
            "review_requests": len(self._reviews),
            "abandoned_carts": len(self._carts),
        }


_engine: EcommerceEngine | None = None


def get_ecommerce_engine() -> EcommerceEngine:
    global _engine
    if _engine is None:
        _engine = EcommerceEngine()
        _engine.initialize()
    return _engine
