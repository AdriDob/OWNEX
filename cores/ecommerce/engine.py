"""E-commerce Engine — core orchestration for multi-channel operations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from cores.ecommerce.models import (
    EcommerceMetrics,
    Marketplace,
    Order,
    OrderStatus,
    Product,
    ProductStatus,
    PurchaseOrder,
    Supplier,
    SyncLog,
)

logger = logging.getLogger("ownex.ecommerce.engine")


class EcommerceEngine:
    """Central engine coordinating all e-commerce operations."""

    def __init__(self) -> None:
        self._suppliers: dict[str, Supplier] = {}
        self._products: dict[str, Product] = {}
        self._orders: dict[str, Order] = {}
        self._purchase_orders: dict[str, PurchaseOrder] = {}
        self._sync_logs: list[SyncLog] = []
        self._initialized = False

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
        return supplier

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
        }


_engine: EcommerceEngine | None = None


def get_ecommerce_engine() -> EcommerceEngine:
    global _engine
    if _engine is None:
        _engine = EcommerceEngine()
        _engine.initialize()
    return _engine
