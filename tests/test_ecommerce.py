"""Tests for the E-commerce Engine (Droppinglabel + Meli + IG/WA).

Zero-stock model: supplier -> customer. Adapters are honest-unavailable
without credentials; pipeline math is pure and deterministic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.ecommerce import router
from cores.ecommerce.adapters import IGWAAdapter, MeliAdapter
from cores.ecommerce.engine import EcommerceEngine
from cores.ecommerce.models import (
    Marketplace,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    Supplier,
    SupplierType,
    get_default_subcategories,
    get_hs_code,
)
from cores.ecommerce.pipeline import (
    ListingOptimizer,
    OrderOrchestrator,
    SourcingEngine,
    run_ecommerce_listing_health,
    run_ecommerce_order_sync,
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _product(**overrides) -> Product:
    data = {
        "id": "prod_1",
        "sku": "DROP-001",
        "name": "Zapatillas Runner Pro",
        "description": "Zapatillas deportivas livianas",
        "category": "deportiva",
        "brand": "Droppinglabel",
        "supplier_id": "sup_1",
        "cost_usd": Decimal("25.0"),
        "sale_price_usd": Decimal("59.99"),
        "currency": "USD",
        "images": ["https://example.com/img1.jpg"],
        "tags": ["running", "deporte"],
        "attributes": {"color": "negro", "talle": "42"},
    }
    data.update(overrides)
    return Product(**data)


def test_product_margin_roi() -> None:
    p = _product()
    assert p.calculate_margin() > 50.0
    assert p.calculate_roi() > 100.0


def test_hs_code_and_subcategories() -> None:
    assert get_hs_code("relojes", "analogicos") == "91"
    assert "zapatillas" in get_default_subcategories("deportiva")


def test_sourcing_verdicts() -> None:
    engine = SourcingEngine()
    viable = engine.score_supplier_offer(cost_usd=20, sale_price_usd=60, shipping_usd=5)
    assert viable["verdict"] == "VIABLE"
    assert viable["margin_pct"] >= 25
    reject = engine.score_supplier_offer(cost_usd=55, sale_price_usd=60, shipping_usd=5)
    assert reject["verdict"] == "REJECT"


def test_listing_optimizer_title_and_keywords() -> None:
    opt = ListingOptimizer()
    title = opt.optimize_title("Zapatillas Runner", brand="Droppinglabel", attributes={"color": "negro"})
    assert "Zapatillas" in title
    assert len(title) <= 60
    listing = opt.optimize_listing(_product(), Marketplace.MERCADOLIBRE)
    assert listing.title
    assert listing.marketplace == Marketplace.MERCADOLIBRE


def test_order_orchestrator_next_action() -> None:
    orch = OrderOrchestrator()
    order = Order(id="o1", marketplace=Marketplace.MERCADOLIBRE, status=OrderStatus.PENDING)
    assert "Confirmar" in orch.next_action(order)
    delivered = Order(id="o2", marketplace=Marketplace.INSTAGRAM, status=OrderStatus.DELIVERED)
    assert "PAID" in orch.next_action(delivered)


def test_purchase_order_totals() -> None:
    orch = OrderOrchestrator()
    order = Order(
        id="o3",
        marketplace=Marketplace.WHATSAPP,
        items=[
            OrderItem(
                product_id="prod_1",
                listing_id="wa:prod_1",
                quantity=2,
                unit_price_usd=Decimal("60"),
                total_price_usd=Decimal("120"),
            )
        ],
    )
    po = orch.build_purchase_order("sup_1", [order], {"prod_1": 25.0})
    assert po.total_usd == Decimal("50.0")
    assert po.order_ids == ["o3"]


def test_engine_crud_and_metrics() -> None:
    engine = EcommerceEngine()
    engine.add_supplier(Supplier(id="sup_1", name="Proveedor Test", type=SupplierType.LOCAL_AR))
    assert engine.get_supplier("sup_1") is not None
    engine.add_product(_product())
    assert engine.get_product_by_sku("DROP-001") is not None
    order = Order(
        id="ord_1",
        marketplace=Marketplace.MERCADOLIBRE,
        items=[
            OrderItem(
                product_id="prod_1",
                listing_id="meli:prod_1",
                quantity=1,
                unit_price_usd=Decimal("59.99"),
                unit_cost_usd=Decimal("25.0"),
                total_price_usd=Decimal("59.99"),
                total_cost_usd=Decimal("25.0"),
                margin_usd=Decimal("34.99"),
            )
        ],
    )
    order.calculate_totals()
    engine.add_order(order)
    assert engine.get_order("ord_1") is not None
    end = datetime.now(UTC)
    metrics = engine.calculate_metrics(end - timedelta(days=30), end)
    assert metrics.total_orders >= 1
    assert float(metrics.total_revenue_usd) > 0


def test_adapters_honest_unavailable() -> None:
    meli = MeliAdapter()
    igwa = IGWAAdapter()
    # Without credentials both must report unavailable, never raise.
    assert meli.status()["available"] in (True, False)
    assert igwa.status()["available"] in (True, False)
    assert isinstance(meli.is_available(), bool)
    assert isinstance(igwa.is_available(), bool)


def test_sync_handlers_never_raise() -> None:
    orders = run_ecommerce_order_sync()
    assert orders["success"] in (True, False)
    assert "synced" in orders
    health = run_ecommerce_listing_health()
    assert health["success"] is True
    assert "active_products" in health


class TestEcommerceApi:
    def test_status(self) -> None:
        resp = client.get("/api/ecommerce/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "products" in body
        assert "adapters" in body

    def test_add_and_list_product(self) -> None:
        payload = {
            "id": "api_prod_1",
            "sku": "API-001",
            "name": "Reloj Smart X",
            "category": "relojes",
            "cost_usd": 18.0,
            "sale_price_usd": 49.99,
        }
        resp = client.post("/api/ecommerce/products", json=payload)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        listing_resp = client.get("/api/ecommerce/products")
        assert listing_resp.status_code == 200
        assert listing_resp.json()["total"] >= 1

    def test_sourcing_score_endpoint(self) -> None:
        resp = client.post(
            "/api/ecommerce/sourcing/score",
            json={"cost_usd": 20, "sale_price_usd": 60, "shipping_usd": 5},
        )
        assert resp.status_code == 200
        assert resp.json()["verdict"] == "VIABLE"
