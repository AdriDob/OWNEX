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
from cores.ecommerce.adapters import IGWAAdapter, MeliAdapter, SupplierCatalogAdapter
from cores.ecommerce.engine import EcommerceEngine
from cores.ecommerce.models import (
    Marketplace,
    Order,
    OrderItem,
    OrderStatus,
    Product,
    ProductStatus,
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


def _fake_client_class(response=None, exc=None, record=None):
    """Build a fake httpx.AsyncClient class (no network, records URLs)."""

    class _Resp:
        status_code = response["status"] if response else 500

        def json(self):
            if response is not None and "payload" in response:
                return response["payload"]
            raise ValueError("no json")

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def get(self, url, **kwargs):
            if record is not None:
                record.append(url)
            if exc is not None:
                raise exc
            return _Resp()

    return _Client


def _supplier_with_endpoint(supplier_id="sup_web_1") -> Supplier:
    return Supplier(
        id=supplier_id,
        name="Proveedor Web Test",
        type=SupplierType.LOCAL_AR,
        website="https://proveedor.test",
        api_endpoint="https://proveedor.test/api/catalogo",
    )


_CATALOG_PAYLOAD = [
    {"sku": "PERF-001", "name": "Perfume Árabe Noche", "price": 20.0, "currency": "USD"},
    {"title": "Remera Oversize", "cost": 15.5, "image": "https://img.test/r.jpg"},
    {"name": "", "price": 10.0},
    {"name": "Sin precio"},
    "basura-no-dict",
]


def test_supplier_catalog_success_mapping(monkeypatch) -> None:
    import asyncio

    import httpx

    urls: list[str] = []
    monkeypatch.setattr(
        httpx, "AsyncClient", _fake_client_class(response={"status": 200, "payload": _CATALOG_PAYLOAD}, record=urls)
    )
    result = asyncio.run(SupplierCatalogAdapter(_supplier_with_endpoint()).fetch_catalog(limit=10))
    assert result["success"] is True
    assert len(result["items"]) == 2
    assert result["items"][0]["sku"] == "PERF-001"
    assert result["items"][1]["name"] == "Remera Oversize"
    assert urls and urls[0].startswith("https://proveedor.test/api/catalogo")


def test_supplier_catalog_no_endpoint_makes_no_request(monkeypatch) -> None:
    import asyncio

    import httpx

    urls: list[str] = []
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_class(response={"status": 200, "payload": []}, record=urls))
    supplier = Supplier(id="sup_noep", name="Sin Endpoint", type=SupplierType.OTHER)
    result = asyncio.run(SupplierCatalogAdapter(supplier).fetch_catalog())
    assert result["success"] is False
    assert result["error"] == "no_endpoint"
    assert urls == []


def test_supplier_catalog_connection_failure(monkeypatch) -> None:
    import asyncio

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_class(exc=TimeoutError("t")))
    result = asyncio.run(SupplierCatalogAdapter(_supplier_with_endpoint()).fetch_catalog())
    assert result["success"] is False
    assert result["error"] == "connection_failed"
    assert result["items"] == []


def test_supplier_catalog_bad_shape(monkeypatch) -> None:
    import asyncio

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_class(response={"status": 200, "payload": {"ok": True}}))
    result = asyncio.run(SupplierCatalogAdapter(_supplier_with_endpoint()).fetch_catalog())
    assert result["success"] is False
    assert result["error"] == "unsupported_catalog_shape"


def test_engine_sync_upserts_draft_products(monkeypatch) -> None:
    import asyncio

    import httpx

    engine = EcommerceEngine()
    engine.add_supplier(_supplier_with_endpoint("sup_sync_1"))
    monkeypatch.setattr(httpx, "AsyncClient", _fake_client_class(response={"status": 200, "payload": _CATALOG_PAYLOAD}))
    first = asyncio.run(engine.sync_supplier_catalog("sup_sync_1"))
    assert first["success"] is True
    assert first["synced"] == 2
    product = engine.get_product("sup_sync_1:PERF-001")
    assert product is not None
    assert product.status == ProductStatus.DRAFT
    assert float(product.cost_usd) == 20.0
    second = asyncio.run(engine.sync_supplier_catalog("sup_sync_1"))
    assert second["synced"] == 0
    assert second["updated"] == 2


def test_engine_sync_unknown_supplier() -> None:
    import asyncio

    engine = EcommerceEngine()
    result = asyncio.run(engine.sync_supplier_catalog("no-existe"))
    assert result["success"] is False
    assert result["error"] == "unknown_supplier"


def test_zero_price_product_margin_guard() -> None:
    p = Product(id="p0", sku="P0", name="Costo conocido, precio pendiente", cost_usd=Decimal("20"))
    assert p.calculate_margin() == 0.0
    assert p.calculate_roi() == 0.0


class TestSupplierSyncApi:
    def test_sync_unknown_supplier_404(self) -> None:
        resp = client.post("/api/ecommerce/suppliers/definitivamente-no-existe/sync-catalog")
        assert resp.status_code == 404

    def test_register_and_sync_catalog(self, monkeypatch) -> None:
        import httpx

        resp = client.post(
            "/api/ecommerce/suppliers",
            json={
                "id": "api_sup_web",
                "name": "Proveedor API Test",
                "api_endpoint": "https://proveedor.test/api/catalogo",
                "website": "https://proveedor.test",
            },
        )
        assert resp.status_code == 200
        monkeypatch.setattr(
            httpx, "AsyncClient", _fake_client_class(response={"status": 200, "payload": _CATALOG_PAYLOAD})
        )
        sync = client.post("/api/ecommerce/suppliers/api_sup_web/sync-catalog")
        assert sync.status_code == 200
        body = sync.json()
        assert body["success"] is True
        assert body["synced"] == 2
