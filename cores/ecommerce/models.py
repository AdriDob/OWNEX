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
    DROPSHEABLE = "dropsheable"
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
    instagram: str = ""  # handle @tienda (sin @ también vale) para outreach y contenido IG $0
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
    reseller_program: bool = False  # True si el modelo admite revender su catálogo (plataforma/fábrica/encargo)
    verified_at: datetime | None = None
    fulfillment_model: str = ""  # comision | dropshipping | mayorista (C = reject $0)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


ZERO_CAPITAL_ACTIVE = "active"  # términos $0 confirmados: se puede publicar y vender
ZERO_CAPITAL_FUTURE = "future"  # buen candidato pero exige algo (abono, mínimo, stock) o falta verificar
ZERO_CAPITAL_REJECTED = "rejected"  # exige capital inicial o despachamos nosotros

# Autenticidad del producto (anti-baja por marca). UNKNOWN bloquea la publicación.
AUTHENTICITY_OFFICIAL = "official"  # original del fabricante/marca
AUTHENTICITY_LICENSED = "licensed"  # licencia oficial de reventa
AUTHENTICITY_REPLICA = "replica"  # réplica/inspirado: se vende descrita tal cual, jamás como original
AUTHENTICITY_UNKNOWN = "unknown"  # sin verificar: NO se publica hasta definirlo
AUTHENTICITY_VALUES = (
    AUTHENTICITY_OFFICIAL,
    AUTHENTICITY_LICENSED,
    AUTHENTICITY_REPLICA,
    AUTHENTICITY_UNKNOWN,
)


def zero_capital_gate(supplier: Supplier) -> dict[str, Any]:
    """Clasifica un proveedor para operar con $0 reales (puro, nunca raisea).

    Regla no negociable del owner: primero venta, después dinero, después escala.
    - REJECTED: exige capital inicial (stock/suscripción prepaga que haya que
      financiar) o el fulfillment es nuestro (sin stock no hay despacho).
    - FUTURE: no exige capital pero falta algo — abono mensual, compra mínima,
      fulfillment mixto, acuerdo mayorista sin confirmar o 5 preguntas sin verificar.
    - ACTIVE: verificado + sin capital + sin abono + sin mínimo + despacha el proveedor.
    """
    reasons: list[str] = []
    blocked = False
    try:
        capital = float(getattr(supplier, "capital_required_usd", 0) or 0)
    except (TypeError, ValueError, ArithmeticError):
        capital = 0.0
    try:
        monthly = float(getattr(supplier, "monthly_cost_usd", 0) or 0)
    except (TypeError, ValueError, ArithmeticError):
        monthly = 0.0
    try:
        minimum = float(getattr(supplier, "minimum_order_usd", 0) or 0)
    except (TypeError, ValueError, ArithmeticError):
        minimum = 0.0
    fulfillment = str(getattr(supplier, "fulfillment", "provider") or "provider").lower()
    fee_model = str(getattr(supplier, "fee_model", "none") or "none").lower()
    fulfillment_model = str(getattr(supplier, "fulfillment_model", "") or "").lower()
    verified = bool(getattr(supplier, "verified", False))
    # Simple = no te pide pagar nada más que por ventas (fee none o % por venta,
    # sin capital/abono/mínimo, despacha el proveedor). Mayorista sin verificar
    # NO es simple: sus términos reales (mínimos, unitario) aún se desconocen.
    simple = (
        capital <= 0
        and monthly <= 0
        and fee_model in ("none", "per_sale_pct")
        and minimum <= 0
        and fulfillment == "provider"
        and (verified or fulfillment_model in ("", "dropshipping", "comision"))
    )

    if capital > 0:
        blocked = True
        reasons.append(f"exige capital inicial USD {capital:g} (stock/compra previa)")
    if fulfillment == "own":
        blocked = True
        reasons.append("fulfillment propio: despacharíamos nosotros (exige stock)")
    if blocked:
        return {"status": ZERO_CAPITAL_REJECTED, "reasons": reasons, "simple": False}
    if monthly > 0 or fee_model in ("monthly", "hybrid"):
        reasons.append("cobra abono/suscripción (no es $0 total hasta pagarlo con ventas)")
    if minimum > 0:
        reasons.append(f"compra mínima USD {minimum:g} (hay que financiarla)")
    if fulfillment == "mixed":
        reasons.append("fulfillment mixto: confirmar qué parte despacha el proveedor")
    if fulfillment_model == "mayorista" and not verified:
        reasons.append("mayorista sin acuerdo: confirmar unitario + despacho a nombre tercero + comisión por escrito")
    if not verified:
        reasons.append("acuerdo sin verificar: faltan las 5 preguntas (comisión, stock, despacho, devoluciones, fotos)")
    if reasons:
        return {"status": ZERO_CAPITAL_FUTURE, "reasons": reasons, "simple": simple}
    return {
        "status": ZERO_CAPITAL_ACTIVE,
        "reasons": ["términos $0 verificados: sin capital, sin abono, despacha el proveedor"],
        "simple": True,
    }


def publish_blockers(product: Any) -> list[str]:
    """Bloqueadores de publicación de un producto (puro, nunca raisea).

    Regla: `unknown` no se publica hasta verificarlo (ni como original ni como
    réplica). La lista vacía = publicable (el humano igual aprueba).
    """
    blockers: list[str] = []
    try:
        authenticity = str(getattr(product, "authenticity", AUTHENTICITY_UNKNOWN) or AUTHENTICITY_UNKNOWN).lower()
    except Exception:
        authenticity = AUTHENTICITY_UNKNOWN
    if authenticity not in AUTHENTICITY_VALUES:
        blockers.append(f"authenticity inválido ({authenticity}): usar official|licensed|replica|unknown")
    elif authenticity == AUTHENTICITY_UNKNOWN:
        blockers.append("authenticity sin verificar: definir official|licensed|replica antes de publicar")
    try:
        price = float(getattr(product, "sale_price_usd", 0) or 0) or float(getattr(product, "sale_price_ars", 0) or 0)
    except (TypeError, ValueError, ArithmeticError):
        price = 0.0
    if price <= 0:
        blockers.append("sin precio de venta (fijarlo con /sourcing/net-real)")
    if not str(getattr(product, "supplier_id", "") or "").strip():
        blockers.append("sin proveedor asignado")
    return blockers


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
    authenticity: str = AUTHENTICITY_UNKNOWN  # official | licensed | replica | unknown
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
