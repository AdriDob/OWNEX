"""Data models for the E-commerce Engine.

Covers dropshipping (Droppinglabel), marketplace (MercadoLibre), and
order orchestration across channels. Zero-stock model: supplier → customer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class Marketplace(StrEnum):
    MERCADOLIBRE = "mercadolibre"
    INSTAGRAM = "instagram"
    WHATSAPP = "whatsapp"
    TIKTOK_SHOP = "tiktok_shop"
    FACEBOOK_MARKETPLACE = "facebook_marketplace"
    OWN_WEBSITE = "own_website"
    OTHER = "other"


class SupplierType(StrEnum):
    ALIEXPRESS = "aliexpress"
    LOCAL_AR = "local_argentina"
    CHINA_WHOLESALE = "china_wholesale"
    DOMESTIC_DISTRIBUTOR = "domestic_distributor"
    PRINT_ON_DEMAND = "print_on_demand"
    OTHER = "other"


class ProductStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    OUT_OF_STOCK = "out_of_stock"
    DISCONTINUED = "discontinued"


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    PURCHASED_FROM_SUPPLIER = "purchased_from_supplier"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class ListingStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    ENDED = "ended"
    BLOCKED = "blocked"
    NEEDS_REVIEW = "needs_review"


class ShippingStatus(StrEnum):
    PENDING = "pending"
    LABEL_CREATED = "label_created"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"
    FAILED = "failed"
    CHARGEBACK = "chargeback"


@dataclass(slots=True)
class Supplier:
    id: str
    name: str
    type: SupplierType
    contact_email: str = ""
    contact_phone: str = ""
    website: str = ""
    api_endpoint: str = ""
    api_credentials: dict[str, str] = field(default_factory=dict)
    shipping_countries: list[str] = field(default_factory=list)
    processing_time_days: int = 3
    minimum_order_usd: Decimal = Decimal("0")
    commission_rate: Decimal = Decimal("0")  # if supplier takes commission
    is_active: bool = True
    rating: float = 0.0
    notes: str = ""
    # ── Scorecard auto (Fase 3, $0: recalculado desde historial local) ──
    fulfillment_rate: float = 0.0  # % POs shipped/delivered sobre total
    avg_shipping_days: float = 0.0  # promedio real observado (0 = sin datos)
    return_rate: float = 0.0  # % orders returned/refunded atribuidas
    quality_score: float = 0.0  # 0-100 composite honesto
    total_pos: int = 0
    last_score_at: datetime | None = None
    # ── Modelo $0 (ranking proveedores: "$0 stock" ≠ "$0 total") ──
    capital_required_usd: Decimal = Decimal("0")  # stock inicial exigido (0 = puro)
    monthly_cost_usd: Decimal = Decimal("0")  # abono/suscripción (>0 ≠ $0 total)
    ml_integrated: bool = False  # integración Mercado Libre publicada
    fulfillment: str = "provider"  # provider | own | mixed
    fee_model: str = "none"  # none | per_sale_pct | monthly | hybrid
    fee_pct: float = 0.0  # % por venta (ej. Dropsheable 3%)
    stock_sync: bool = False  # stock sincronizado automático
    verified: bool = False  # acuerdo comercial verificado (checklist 5 preguntas)
    verified_at: datetime | None = None
    fulfillment_model: str = ""  # comision | dropshipping | mayorista (C = reject $0)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Product:
    id: str
    sku: str
    name: str
    description: str = ""
    short_description: str = ""
    category: str = ""
    subcategory: str = ""
    brand: str = ""
    supplier_id: str = ""
    supplier_sku: str = ""
    cost_usd: Decimal = Decimal("0")
    sale_price_usd: Decimal = Decimal("0")
    sale_price_ars: Decimal = Decimal("0")
    currency: str = "USD"
    weight_kg: float = 0.0
    dimensions_cm: dict[str, float] = field(default_factory=dict)  # l, w, h
    images: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)  # color, size, material, etc.
    status: ProductStatus = ProductStatus.DRAFT
    marketplace_listings: dict[str, str] = field(default_factory=dict)  # marketplace -> listing_id
    seo_title: str = ""
    seo_description: str = ""
    seo_keywords: list[str] = field(default_factory=list)
    margin_pct: float = 0.0
    roi_pct: float = 0.0
    suggested_price_usd: Decimal = Decimal("0")  # auto-pricing Fase 1 (humano aprueba)
    is_dropship: bool = True
    requires_customs: bool = False
    hs_code: str = ""  # Harmonized System code for customs
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def calculate_margin(self) -> float:
        if self.cost_usd > 0 and self.sale_price_usd > 0:
            self.margin_pct = float((self.sale_price_usd - self.cost_usd) / self.sale_price_usd * 100)
        else:
            self.margin_pct = 0.0
        return self.margin_pct

    def calculate_roi(self) -> float:
        if self.cost_usd > 0 and self.sale_price_usd > 0:
            self.roi_pct = float((self.sale_price_usd - self.cost_usd) / self.cost_usd * 100)
        else:
            self.roi_pct = 0.0
        return self.roi_pct


@dataclass(slots=True)
class MarketplaceListing:
    id: str
    product_id: str
    marketplace: Marketplace
    external_id: str = ""  # Meli item_id, IG media_id, etc.
    title: str = ""
    description: str = ""
    price_usd: Decimal = Decimal("0")
    price_local: Decimal = Decimal("0")
    currency: str = "USD"
    quantity: int = 0
    status: ListingStatus = ListingStatus.DRAFT
    url: str = ""
    images: list[str] = field(default_factory=list)
    attributes: dict[str, str] = field(default_factory=dict)
    shipping_template_id: str = ""
    category_id: str = ""
    views: int = 0
    sales: int = 0
    questions: int = 0
    rating: float = 0.0
    last_synced: datetime | None = None
    error_message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Customer:
    id: str
    marketplace: Marketplace
    external_id: str = ""  # Meli user_id, IG pk, WA phone
    name: str = ""
    email: str = ""
    phone: str = ""
    shipping_address: dict[str, str] = field(default_factory=dict)
    billing_address: dict[str, str] = field(default_factory=dict)
    total_orders: int = 0
    total_spent_usd: Decimal = Decimal("0")
    last_order_at: datetime | None = None
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class OrderItem:
    product_id: str
    listing_id: str
    quantity: int = 1
    unit_price_usd: Decimal = Decimal("0")
    unit_cost_usd: Decimal = Decimal("0")
    total_price_usd: Decimal = Decimal("0")
    total_cost_usd: Decimal = Decimal("0")
    margin_usd: Decimal = Decimal("0")


@dataclass(slots=True)
class Order:
    id: str
    marketplace: Marketplace
    external_id: str = ""  # Meli order_id, IG order ref
    customer_id: str = ""
    items: list[OrderItem] = field(default_factory=list)
    subtotal_usd: Decimal = Decimal("0")
    shipping_usd: Decimal = Decimal("0")
    tax_usd: Decimal = Decimal("0")
    discount_usd: Decimal = Decimal("0")
    total_usd: Decimal = Decimal("0")
    total_cost_usd: Decimal = Decimal("0")
    margin_usd: Decimal = Decimal("0")
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.PENDING
    shipping_status: ShippingStatus = ShippingStatus.PENDING
    shipping_carrier: str = ""
    tracking_number: str = ""
    shipping_label_url: str = ""
    estimated_delivery: datetime | None = None
    delivered_at: datetime | None = None
    marketplace_fees_usd: Decimal = Decimal("0")
    payment_fees_usd: Decimal = Decimal("0")
    notes: str = ""
    internal_notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    confirmed_at: datetime | None = None
    shipped_at: datetime | None = None

    def calculate_totals(self) -> None:
        self.subtotal_usd = sum((item.total_price_usd for item in self.items), Decimal("0"))
        self.total_cost_usd = sum((item.total_cost_usd for item in self.items), Decimal("0"))
        self.margin_usd = sum((item.margin_usd for item in self.items), Decimal("0"))
        self.total_usd = self.subtotal_usd + self.shipping_usd + self.tax_usd - self.discount_usd


@dataclass(slots=True)
class PurchaseOrder:
    id: str
    supplier_id: str
    order_ids: list[str] = field(default_factory=list)  # Customer orders being fulfilled
    items: list[OrderItem] = field(default_factory=list)
    subtotal_usd: Decimal = Decimal("0")
    shipping_usd: Decimal = Decimal("0")
    tax_usd: Decimal = Decimal("0")
    total_usd: Decimal = Decimal("0")
    status: OrderStatus = OrderStatus.PENDING
    supplier_order_ref: str = ""
    tracking_number: str = ""
    expected_arrival: datetime | None = None
    received_at: datetime | None = None
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def calculate_totals(self) -> None:
        self.subtotal_usd = sum((item.total_cost_usd for item in self.items), Decimal("0"))
        self.total_usd = self.subtotal_usd + self.shipping_usd + self.tax_usd


@dataclass(slots=True)
class SyncLog:
    id: str
    entity_type: str  # product, listing, order, inventory
    entity_id: str
    marketplace: Marketplace
    action: str  # create, update, delete, sync
    status: str  # success, failed, partial
    details: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class CompetitorSnapshot:
    """Observed competitor prices for one product (public data, honest timestamp)."""

    id: str
    product_id: str
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    competitor_prices: list[float] = field(default_factory=list)
    min_price: float = 0.0
    avg_price: float = 0.0
    signal: str = "UNKNOWN"  # UNKNOWN/COMPETITIVE/OVERPRICED/OPPORTUNITY
    action: str = "sin_datos_suficientes"
    source: str = "manual"  # manual | meli_search | job
    note: str = ""


@dataclass(slots=True)
class ReviewRequest:
    """Post-sale review ask (WhatsApp/Email template, $0 Cloud API free tier)."""

    id: str
    order_id: str
    channel: str = "whatsapp"  # whatsapp | email
    template: str = "review_default"
    message: str = ""
    sent_at: datetime | None = None
    status: str = "pending"  # pending | prepared | sent | failed
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class AbandonedCart:
    """Lightweight cart-intent tracking for organic recovery ($0, frontend pixel)."""

    id: str
    visitor_id: str = ""
    product_id: str = ""
    marketplace: str = "mercadolibre"
    viewed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    recovered: bool = False
    recovery_sent_at: datetime | None = None
    note: str = ""


@dataclass(slots=True)
class EcommerceMetrics:
    period_start: datetime
    period_end: datetime
    total_orders: int = 0
    total_revenue_usd: Decimal = Decimal("0")
    total_cost_usd: Decimal = Decimal("0")
    total_margin_usd: Decimal = Decimal("0")
    avg_margin_pct: float = 0.0
    avg_order_value_usd: Decimal = Decimal("0")
    conversion_rate: float = 0.0
    returning_customer_rate: float = 0.0
    top_products: list[dict[str, Any]] = field(default_factory=list)
    top_marketplaces: list[dict[str, Any]] = field(default_factory=list)
    by_marketplace: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_category: dict[str, dict[str, Any]] = field(default_factory=dict)


# Default categories for Droppinglabel
DEFAULT_CATEGORIES = {
    "ropa": {
        "subcategories": [
            "remeras",
            "camisas",
            "pantalones",
            "vestidos",
            "abrigos",
            "deportiva",
            "interior",
            "accesorios",
        ],
        "hs_code_prefix": "61",  # Articles of apparel, knitted/crocheted
    },
    "deportiva": {
        "subcategories": ["zapatillas", "remeras", "pantalones", "camperas", "accesorios", "equipamiento"],
        "hs_code_prefix": "64",  # Footwear
    },
    "relojes": {
        "subcategories": ["analogicos", "digitales", "smartwatches", "correas", "accesorios"],
        "hs_code_prefix": "91",  # Clocks and watches
    },
    "perfumes": {
        "subcategories": ["hombre", "mujer", "unisex", "muestras", "sets"],
        "hs_code_prefix": "33",  # Essential oils, perfumery
    },
}


def get_hs_code(category: str, subcategory: str) -> str:
    """Get HS code prefix for a category."""
    cat = DEFAULT_CATEGORIES.get(category.lower(), {})
    return cat.get("hs_code_prefix", "")


def get_default_subcategories(category: str) -> list[str]:
    """Get default subcategories for a category."""
    cat = DEFAULT_CATEGORIES.get(category.lower(), {})
    return cat.get("subcategories", [])


# MercadoLibre specific constants
MELI_CATEGORIES = {
    "ropa": "MLA1430",  # Ropa y accesorios
    "deportiva": "MLA1276",  # Deportes y fitness
    "relojes": "MLA1432",  # Relojes
    "perfumes": "MLA1196",  # Belleza y cuidado personal
}

MELI_SHIPPING_MODES = {
    "me1": "Mercado Envíos Colecta",
    "me2": "Mercado Envíos Flex",
    "custom": "Envío personalizado",
    "not_specified": "No especificado",
}

MELI_LISTING_TYPES = {
    "free": "Gratuita",
    "gold": "Clásica",
    "gold_premium": "Premium",
    "gold_pro": "Profesional",
}

MELI_CONDITIONS = {
    "new": "Nuevo",
    "used": "Usado",
    "not_specified": "No especificado",
}
