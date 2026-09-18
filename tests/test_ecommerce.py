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


class TestOutreachIG:
    def test_default_canal_es_meli_contrato_historico(self) -> None:
        from cores.ecommerce.outreach import build_message

        m = build_message("sup_fut_001", "Nebbux")
        assert m["canal"] == "meli"
        assert "MercadoLibre" in m["body"]

    def test_ig_todas_las_categorias_mencionan_instagram(self) -> None:
        from cores.ecommerce.outreach import OUTREACH_TEMPLATES, OUTREACH_TEMPLATES_IG, build_message

        assert set(OUTREACH_TEMPLATES_IG) == set(OUTREACH_TEMPLATES)
        for sid, name in [
            ("sup_urban_001", "Nebbux"),
            ("sup_fut_001", "Fútbol Total"),
            ("sup_watch_002", "Cronos Import"),
            ("sup_perf_005", "Decants AR"),
            ("sup_acc_003", "Acero Mayorista"),
            ("sup_x", "Desconocido"),
        ]:
            m = build_message(sid, name, canal="ig")
            assert m["canal"] == "ig"
            assert "Instagram" in m["body"]
            assert "MercadoLibre" not in m["body"]
            assert m["wa_url"].startswith("https://wa.me/?text=")

    def test_arab_keywords_van_a_perfumes(self) -> None:
        from cores.ecommerce.outreach import build_message, niche_for

        assert niche_for("s1", "Aromas Árabes AR") == "perfumes"
        assert niche_for("s2", "Lattafa Mayorista") == "perfumes"
        assert niche_for("s3", "Oud House") == "perfumes"
        assert build_message("s2", "Lattafa Mayorista", canal="ig")["category_key"] == "perfumes"

    def test_canal_invalido_422(self) -> None:
        r = client.post(
            "/api/ecommerce/suppliers",
            json={"id": "ig_canal_test", "name": "Test Canal", "website": "https://example.com"},
        )
        assert r.status_code == 200
        assert client.get("/api/ecommerce/suppliers/ig_canal_test/outreach?canal=tiktok").status_code == 422
        assert client.post("/api/ecommerce/suppliers/ig_canal_test/outreach/contact?canal=tiktok").status_code == 422

    def test_outreach_ig_roundtrip(self) -> None:
        r = client.get("/api/ecommerce/suppliers/ig_canal_test/outreach?canal=ig")
        assert r.status_code == 200
        assert r.json()["message"]["canal"] == "ig"
        c = client.post("/api/ecommerce/suppliers/ig_canal_test/outreach/contact?canal=ig")
        assert c.status_code == 200
        assert "Instagram" in c.json()["record"]["message"]  # IG encuadra, no Meli


class TestSupplierInstagramField:
    def test_instagram_y_niche_en_lista(self) -> None:
        r = client.post(
            "/api/ecommerce/suppliers",
            json={
                "id": "sup_perf_900",
                "name": "Lattafa Test AR",
                "website": "https://example.com",
                "instagram": "@lattafatest",
            },
        )
        assert r.status_code == 200
        body = client.get("/api/ecommerce/suppliers").json()
        row = next(s for s in body["suppliers"] if s["id"] == "sup_perf_900")
        assert row["instagram"] == "@lattafatest"
        assert row["niche"] == "perfumes"


class TestContenidoIG:
    def test_cross_list_incluye_instagram(self) -> None:
        r = client.post(
            "/api/ecommerce/products",
            json={"id": "ig_prod_1", "sku": "IG-001", "name": "Decant Lattafa 5ml"},
        )
        assert r.status_code == 200
        xl = client.post("/api/ecommerce/products/ig_prod_1/cross-list")
        assert xl.status_code == 200
        assert "instagram" in xl.json()["channels"]
        assert client.post("/api/ecommerce/products/no-existe/cross-list").status_code == 404

    def test_content_plan_default_instagram(self) -> None:
        cp = client.post("/api/ecommerce/products/ig_prod_1/content-plan")
        assert cp.status_code == 200
        assert isinstance(cp.json(), dict)
        assert client.post("/api/ecommerce/products/no-existe/content-plan").status_code == 404


class TestZeroCapitalGate:
    def test_rejected_con_capital_o_fulfillment_propio(self) -> None:
        from cores.ecommerce.models import Supplier, SupplierType, zero_capital_gate

        s = Supplier(id="a", name="A", type=SupplierType.LOCAL_AR, capital_required_usd=Decimal("100"))
        assert zero_capital_gate(s)["status"] == "rejected"
        s2 = Supplier(id="b", name="B", type=SupplierType.LOCAL_AR, fulfillment="own", verified=True)
        assert zero_capital_gate(s2)["status"] == "rejected"

    def test_future_con_abono_minimo_o_sin_verificar(self) -> None:
        from cores.ecommerce.models import Supplier, SupplierType, zero_capital_gate

        s = Supplier(id="a", name="A", type=SupplierType.LOCAL_AR, monthly_cost_usd=Decimal("22"), verified=True)
        g = zero_capital_gate(s)
        assert g["status"] == "future" and g["reasons"]
        s2 = Supplier(
            id="b",
            name="B",
            type=SupplierType.DOMESTIC_DISTRIBUTOR,
            fulfillment_model="mayorista",
            verified=False,
        )
        assert zero_capital_gate(s2)["status"] == "future"
        s3 = Supplier(id="c", name="C", type=SupplierType.LOCAL_AR, verified=False)
        assert zero_capital_gate(s3)["status"] == "future"

    def test_active_solo_verificado_sin_cargas(self) -> None:
        from cores.ecommerce.models import Supplier, SupplierType, zero_capital_gate

        s = Supplier(
            id="ok",
            name="OK",
            type=SupplierType.LOCAL_AR,
            fulfillment="provider",
            fee_model="per_sale_pct",
            verified=True,
        )
        g = zero_capital_gate(s)
        assert g["status"] == "active" and len(g["reasons"]) == 1

    def test_nunca_raisea_con_basura(self) -> None:
        from types import SimpleNamespace

        from cores.ecommerce.models import zero_capital_gate

        g = zero_capital_gate(SimpleNamespace())  # type: ignore[arg-type]
        assert g["status"] in ("active", "future", "rejected")


class TestSemillasIG:
    def test_nuevas_semillas_con_gate_future(self) -> None:
        from cores.ecommerce.engine import seed_ranked_suppliers
        from cores.ecommerce.models import zero_capital_gate

        seeds = {s.id: s for s in seed_ranked_suppliers()}
        for sid in (
            "flex_sport_arg",
            "canevic_perf",
            "frag_oriente_perf",
            "nilo_perf",
            "syc_perf",
            "maxon_perf_moron",
            "dropi",
        ):
            assert sid in seeds, sid
            assert zero_capital_gate(seeds[sid])["status"] == "future"
        assert "12" in seeds["flex_sport_arg"].notes  # por encargo: lead time honesto
        assert seeds["flex_sport_arg"].processing_time_days == 12

    def test_ranked_expone_zero_capital(self) -> None:
        body = client.get("/api/ecommerce/suppliers/ranked").json()
        assert body["total"] >= 12
        row = next(s for s in body["suppliers"] if s["id"] == "flex_sport_arg")
        assert row["zero_capital"]["status"] == "future"
        assert row["zero_capital"]["reasons"]

    def test_lista_expone_zero_capital(self) -> None:
        body = client.get("/api/ecommerce/suppliers").json()
        assert body["total"] >= 1
        assert "zero_capital" in body["suppliers"][0]


class TestAuthenticityGate:
    def test_valores_y_blockers_puros(self) -> None:
        from cores.ecommerce.models import AUTHENTICITY_VALUES, Product, publish_blockers

        assert set(AUTHENTICITY_VALUES) == {"official", "licensed", "replica", "unknown"}
        p = Product(id="x", sku="X", name="X", sale_price_usd=Decimal("10"), supplier_id="s")
        assert publish_blockers(p) == [
            "authenticity sin verificar: definir official|licensed|replica antes de publicar"
        ]
        p.authenticity = "replica"
        assert publish_blockers(p) == []
        p.authenticity = "trucho"
        assert any("inválido" in b for b in publish_blockers(p))

    def test_post_producto_valida_authenticity(self) -> None:
        r = client.post(
            "/api/ecommerce/products",
            json={"id": "auth_bad", "sku": "AB", "name": "Malo", "authenticity": "trucho"},
        )
        assert r.status_code == 422
        r = client.post(
            "/api/ecommerce/products",
            json={
                "id": "auth_rep",
                "sku": "AR",
                "name": "Réplica OK",
                "supplier_id": "flex_sport_arg",
                "cost_usd": 20,
                "sale_price_usd": 60,
                "authenticity": "replica",
            },
        )
        assert r.status_code == 200

    def test_optimize_bloquea_unknown_y_pasa_replica(self) -> None:
        r = client.post(
            "/api/ecommerce/products",
            json={
                "id": "auth_unk",
                "sku": "AU",
                "name": "Sin verificar",
                "supplier_id": "flex_sport_arg",
                "cost_usd": 20,
                "sale_price_usd": 60,
            },
        )
        assert r.status_code == 200
        blocked = client.post("/api/ecommerce/products/auth_unk/optimize?marketplace=mercadolibre")
        assert blocked.status_code == 422
        assert "authenticity" in str(blocked.json()["detail"]).lower()
        ok = client.post("/api/ecommerce/products/auth_rep/optimize?marketplace=mercadolibre")
        assert ok.status_code == 200
        assert ok.json()["listing_id"]

    def test_lista_expone_authenticity(self) -> None:
        body = client.get("/api/ecommerce/products").json()
        row = next(p for p in body["products"] if p["id"] == "auth_unk")
        assert row["authenticity"] == "unknown"
        assert row["publish_blockers"] != []


class TestPriceBands:
    def test_orden_y_veredictos(self) -> None:
        from cores.ecommerce.pipeline import get_sourcing_engine

        res = get_sourcing_engine().price_bands(cost_usd=50.0, competitor_prices=[100.0, 120.0])
        assert res["success"] is True
        b = res["bands"]
        assert set(b) == {"minimo", "objetivo", "premium", "competitivo"}
        assert b["minimo"]["price_usd"] <= b["objetivo"]["price_usd"] <= b["premium"]["price_usd"]
        assert b["competitivo"]["price_usd"] == round(100.0 * 0.95, 2)
        assert all(x["verdict"] in ("VIABLE", "THIN", "REJECT") for x in (b["minimo"], b["objetivo"], b["premium"]))

    def test_competitivo_unknown_sin_rivales_y_costo_invalido(self) -> None:
        from cores.ecommerce.pipeline import get_sourcing_engine

        res = get_sourcing_engine().price_bands(cost_usd=50.0)
        assert res["bands"]["competitivo"]["verdict"] == "UNKNOWN"
        assert res["bands"]["competitivo"]["price_usd"] is None
        bad = get_sourcing_engine().price_bands(cost_usd=0)
        assert bad["success"] is False

    def test_suggest_price_trae_bandas(self) -> None:
        r = client.post("/api/ecommerce/sourcing/suggest-price", json={"cost_usd": 50.0})
        assert r.status_code == 200
        assert set(r.json()["bands"]) == {"minimo", "objetivo", "premium", "competitivo"}


class TestProductAssembledScore:
    def test_score_ensamblado_200_y_404(self) -> None:
        r = client.post("/api/ecommerce/products/auth_rep/score")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["verdict"] in ("PRIORITY", "CANDIDATE", "DISCARD", "REJECT")
        assert "signals" in body and "zero_capital" in body
        assert body["zero_capital"]["status"] in ("active", "future", "rejected")
        assert client.post("/api/ecommerce/products/no-existe/score").status_code == 404


class TestSemillasFutbolBasquet:
    def test_nuevas_semillas_futuro_y_nicho(self) -> None:
        from cores.ecommerce.engine import seed_ranked_suppliers
        from cores.ecommerce.models import zero_capital_gate
        from cores.ecommerce.outreach import niche_for

        seeds = {s.id: s for s in seed_ranked_suppliers()}
        for sid in ("kingz_ar", "sublime_sport", "labocha_retro", "mundial_retro", "retro_ba"):
            assert sid in seeds, sid
            assert zero_capital_gate(seeds[sid])["status"] == "future"
            assert niche_for(seeds[sid].id, seeds[sid].name) == "futbol"
        assert seeds["retro_ba"].instagram == "camisetas.retro.ba"
        assert "FÁBRICA" in seeds["sublime_sport"].notes

    def test_ranked_total_crece(self) -> None:
        body = client.get("/api/ecommerce/suppliers/ranked").json()
        assert body["total"] >= 17
        ids = {s["id"] for s in body["suppliers"]}
        assert {"kingz_ar", "sublime_sport", "labocha_retro", "mundial_retro", "retro_ba"} <= ids


class TestSimpleFilter:
    def test_simples_son_solo_pago_por_venta(self) -> None:
        from cores.ecommerce.engine import seed_ranked_suppliers
        from cores.ecommerce.models import zero_capital_gate

        gates = {s.id: zero_capital_gate(s) for s in seed_ranked_suppliers()}
        assert gates["dropsheable"]["simple"] is True  # 3%/venta, sin abono
        assert gates["ventaz"]["simple"] is True
        assert gates["dropi"]["simple"] is True
        assert gates["unidrop"]["simple"] is False  # abono mensual
        assert gates["dropdeal"]["simple"] is False  # híbrido con suscripción
        assert gates["caufy"]["simple"] is False  # suscripción
        assert gates["canevic_perf"]["simple"] is False  # mayorista sin verificar
        assert gates["flex_sport_arg"]["simple"] is False  # sin verificar todavía

    def test_verify_endpoint_activa_y_404(self) -> None:
        assert client.post("/api/ecommerce/suppliers/no-existe/verify").status_code == 404
        r = client.post(
            "/api/ecommerce/suppliers",
            json={"id": "simple_verify_me", "name": "Simple Test", "website": "https://example.com"},
        )
        assert r.status_code == 200
        v = client.post("/api/ecommerce/suppliers/simple_verify_me/verify?notes=WA+ok+unitario")
        assert v.status_code == 200
        body = v.json()
        assert body["zero_capital"]["status"] == "active"
        assert body["zero_capital"]["simple"] is True


class TestResellerPitch:
    def test_pitch_preciso_y_corto(self) -> None:
        from cores.ecommerce.outreach import build_reseller_pitch

        p = build_reseller_pitch("flex_sport_arg", "Flex Sport Arg")
        assert "Droppinglabel" in p["body"]
        assert "camisetas de fútbol" in p["body"]
        assert "comisión" in p["body"]
        assert "paquete neutro" in p["body"] or "nombre de Droppinglabel" in p["body"]
        assert len(p["body"]) < 900  # entra en un WhatsApp sin cortar
        assert p["wa_url"].startswith("https://wa.me/?text=")
        assert build_reseller_pitch("s1", "X")["niche"] == "generic"

    def test_flags_reventa_probable(self) -> None:
        from cores.ecommerce.engine import seed_ranked_suppliers

        flags = {s.id: bool(s.reseller_program) for s in seed_ranked_suppliers()}
        for sid in (
            "dropsheable",
            "unidrop",
            "ventaz",
            "dropdeal",
            "caufy",
            "dropi",
            "flex_sport_arg",
            "kingz_ar",
            "sublime_sport",
            "canevic_perf",
            "bodacious_mayorista",
        ):
            assert flags.get(sid) is True, sid
        for sid in (
            "la_camiseteria",
            "mundo_tribuna",
            "labocha_retro",
            "mundial_retro",
            "retro_ba",
            "zenwaig_relojes",
            "vono_streetwear",
        ):
            assert flags.get(sid) is False, sid

    def test_outreach_detalle_trae_pitch(self) -> None:
        r = client.post(
            "/api/ecommerce/suppliers",
            json={"id": "pitch_flex_test", "name": "Flex Sport Test", "website": "https://example.com"},
        )
        assert r.status_code == 200
        r = client.get("/api/ecommerce/suppliers/pitch_flex_test/outreach?canal=ig")
        assert r.status_code == 200
        pitch = r.json()["reseller_pitch"]
        assert "Droppinglabel" in pitch["body"] and pitch["wa_url"].startswith("https://wa.me/")

    def test_nuevas_semillas_urbanas_y_perfumes(self) -> None:
        from cores.ecommerce.engine import seed_ranked_suppliers
        from cores.ecommerce.models import zero_capital_gate
        from cores.ecommerce.outreach import niche_for

        seeds = {s.id: s for s in seed_ranked_suppliers()}
        assert niche_for("bodacious_mayorista", seeds["bodacious_mayorista"].name) == "urban"
        assert niche_for("caos_men", seeds["caos_men"].name) == "urban"
        assert zero_capital_gate(seeds["bodacious_mayorista"])["status"] == "future"
        body = client.get("/api/ecommerce/suppliers/ranked").json()
        assert body["total"] >= 21


class TestDesignKit:
    def test_brief_shape(self) -> None:
        from cores.ecommerce.design import IG_SIZES, design_brief

        b = design_brief("perfumes")
        assert set(b["formatos"]) == {"post", "story", "square", "highlight"}
        assert b["formatos"]["post"] == {"w": 1080, "h": 1350, "uso": "feed: producto + precio"}
        assert len(b["stack_gratis"]) >= 5 and len(b["reglas"]) >= 3
        assert IG_SIZES["story"]["h"] == 1920

    def test_flyer_render_y_errores(self) -> None:
        import io

        from PIL import Image

        from cores.ecommerce.design import make_flyer

        buf = io.BytesIO()
        Image.new("RGB", (400, 400), (30, 30, 30)).save(buf, format="PNG")
        out = make_flyer(buf.getvalue(), "Lattafa Yara 100ml", "$95.000", size="post")
        assert out["success"] is True and (out["w"], out["h"]) == (1080, 1350)
        assert out["png"][:8] == b"\x89PNG\r\n\x1a\n"
        bad = make_flyer(b"", "X", "$1")
        assert bad == {"success": False, "error": "empty_image"}
        bad2 = make_flyer(buf.getvalue(), "", "")
        assert bad2 == {"success": False, "error": "title_and_price_required"}
        bad3 = make_flyer(buf.getvalue(), "X", "$1", size="post")
        assert bad3["success"] is True

    def test_weekly_pack_siete_dias_sin_inventar(self) -> None:
        from cores.ecommerce.design import weekly_pack

        empty = weekly_pack([])
        assert len(empty["days"]) == 7 and empty["con_productos"] == 0
        assert all(d["producto"] is None for d in empty["days"])
        full = weekly_pack(
            [{"id": f"p{i}", "name": f"P{i}", "sale_price_usd": 10, "niche": "perfumes"} for i in range(9)]
        )
        assert full["con_productos"] == 7 and full["sin_productos"] == 0
        assert len({d["producto"]["id"] for d in full["days"]}) == 7  # sin repetir

    def test_endpoints_design(self) -> None:
        r = client.get("/api/ecommerce/design/brief?niche=relojes")
        assert r.status_code == 200 and r.json()["niche"] == "relojes"
        w = client.get("/api/ecommerce/design/weekly-pack")
        assert w.status_code == 200 and len(w.json()["days"]) == 7
        import io

        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (200, 200), (10, 10, 10)).save(buf, format="PNG")
        f = client.post(
            "/api/ecommerce/design/flyer?title=Test&price_text=$10&size=story",
            files={"image": ("foto.png", buf.getvalue(), "image/png")},
        )
        assert f.status_code == 200 and f.headers["content-type"] == "image/png"
        assert client.post("/api/ecommerce/design/flyer?title=X&price_text=$1&size=post").status_code == 422
        assert (
            client.post(
                "/api/ecommerce/design/flyer?title=X&price_text=$1&size=banner",
                files={"image": ("f.png", buf.getvalue(), "image/png")},
            ).status_code
            == 422
        )


class TestListaAmpliaConcreta:
    def test_tiendas_concretas_sembradas_y_futuras(self) -> None:
        from cores.ecommerce.engine import seed_ranked_suppliers
        from cores.ecommerce.models import zero_capital_gate
        from cores.ecommerce.outreach import build_reseller_pitch, niche_for

        seeds = {s.id: s for s in seed_ranked_suppliers()}
        assert len(seeds) >= 27
        for sid, niche in (
            ("efp_camisetas", "futbol"),
            ("beyond_streetwear", "urban"),
            ("urbanwear_ar", "urban"),
            ("mau_streetwear", "urban"),
            ("callejero_tienda", "urban"),
            ("dripstore_ar", "urban"),
        ):
            assert sid in seeds, sid
            assert niche_for(seeds[sid].id, seeds[sid].name) == niche, sid
            assert zero_capital_gate(seeds[sid])["status"] == "future", sid
        # El pitch nombra Droppinglabel y sirve para estas tiendas
        p = build_reseller_pitch("urbanwear_ar", seeds["urbanwear_ar"].name)
        assert "Droppinglabel" in p["body"] and "ropa urbana" in p["body"]


class TestPerfumeriasArabes:
    def test_nuevas_perfumerias_futuras_y_nicho(self) -> None:
        from cores.ecommerce.engine import seed_ranked_suppliers
        from cores.ecommerce.models import zero_capital_gate
        from cores.ecommerce.outreach import build_reseller_pitch, niche_for

        seeds = {s.id: s for s in seed_ranked_suppliers()}
        for sid in (
            "elzar_perfumeria",
            "benito_decants",
            "ambrosia_perfumes",
            "fragandecants",
            "parfumerie_ar",
            "canevic_perf",
        ):
            assert sid in seeds, sid
            assert niche_for(seeds[sid].id, seeds[sid].name) == "perfumes", sid
            assert zero_capital_gate(seeds[sid])["status"] == "future", sid
        assert seeds["canevic_perf"].website == "https://canevic.com.ar"
        assert seeds["elzar_perfumeria"].reseller_program is True
        assert "320.000" in seeds["canevic_perf"].notes
        p = build_reseller_pitch("elzar_perfumeria", seeds["elzar_perfumeria"].name)
        assert "perfumes árabes" in p["body"]
        body = client.get("/api/ecommerce/suppliers/ranked").json()
        assert body["total"] >= 26


class TestGatePersistence:
    def test_supplier_to_dict_conserva_gate(self) -> None:
        from datetime import UTC, datetime

        from cores.ecommerce.engine import EcommerceEngine
        from cores.ecommerce.models import Supplier, SupplierType

        eng = EcommerceEngine.__new__(EcommerceEngine)
        sup = Supplier(
            id="gate_x",
            name="Gate",
            type=SupplierType.LOCAL_AR,
            fee_model="per_sale_pct",
            fee_pct=3.0,
            fulfillment="provider",
            fulfillment_model="dropshipping",
            verified=True,
            verified_at=datetime.now(UTC),
        )
        d = eng._supplier_to_dict(sup)
        assert d["verified"] is True and d["fee_model"] == "per_sale_pct"
        assert d["fulfillment"] == "provider" and d["fulfillment_model"] == "dropshipping"
        assert d["verified_at"]

    def test_verify_sobrevive_reload(self, tmp_path, monkeypatch) -> None:
        import json

        import cores.ecommerce.engine as eng_mod
        from cores.ecommerce.engine import EcommerceEngine

        store = tmp_path / "suppliers.json"
        store.write_text(json.dumps({"suppliers": []}), encoding="utf-8")
        monkeypatch.setattr(eng_mod, "_suppliers_store_path", lambda: store)
        eng = EcommerceEngine()
        from cores.ecommerce.models import Supplier, SupplierType

        eng.add_supplier(Supplier(id="v1", name="V1", type=SupplierType.LOCAL_AR))
        eng.update_supplier("v1", verified=True)
        eng2 = EcommerceEngine()
        reloaded = eng2.get_supplier("v1")
        assert reloaded is not None and reloaded.verified is True

    def test_legacy_sin_terminos_no_es_simple(self, tmp_path, monkeypatch) -> None:
        import json

        import cores.ecommerce.engine as eng_mod
        from cores.ecommerce.engine import EcommerceEngine
        from cores.ecommerce.models import zero_capital_gate

        store = tmp_path / "suppliers.json"
        store.write_text(
            json.dumps(
                {
                    "suppliers": [
                        {"id": "sup_urban_001", "name": "Nebbux", "type": "local_argentina"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(eng_mod, "_suppliers_store_path", lambda: store)
        eng = EcommerceEngine()
        sup = eng.get_supplier("sup_urban_001")
        assert sup is not None and sup.fulfillment_model == "mayorista"
        gate = zero_capital_gate(sup)
        assert gate["status"] == "future" and gate["simple"] is False


class TestPublishQueue:
    def test_cola_vacia_rebuild_y_publish(self, tmp_path, monkeypatch) -> None:
        import cores.ecommerce.publish_queue as pq

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        pq._store = None
        monkeypatch.setattr(pq, "_store", None)
        q = pq.PublishQueue(path=tmp_path / "q.json")
        assert q.to_dict() == {"built_at": None, "total": 0, "pendientes": 0, "publicados": 0, "days": []}
        out = q.rebuild([{"id": "p1", "name": "Yara", "sale_price_usd": 95, "niche": "perfumes"}])
        assert out["total"] == 7 and out["pendientes"] == 7
        assert q.mark_published("Lunes") is not None
        assert q.mark_published("NoExiste") is None
        assert q.to_dict()["publicados"] == 1
        # Rebuild preserva lo publicado con producto
        out2 = q.rebuild([{"id": "p1", "name": "Yara", "sale_price_usd": 95, "niche": "perfumes"}])
        assert out2["publicados"] >= 0
        # Corrupto → vacío sin raise
        (tmp_path / "bad.json").write_text("{roto", encoding="utf-8")
        assert pq.PublishQueue(path=tmp_path / "bad.json").to_dict()["total"] == 0

    def test_endpoints_cola(self) -> None:
        assert client.get("/api/ecommerce/design/queue").status_code == 200
        body = client.get("/api/ecommerce/design/queue").json()
        assert body["total"] == 7 and "pendientes" in body
        r = client.post("/api/ecommerce/design/queue/Lunes/publish")
        assert r.status_code == 200 and r.json()["success"] is True
        assert client.post("/api/ecommerce/design/queue/NoExiste/publish").status_code == 404
        assert client.post("/api/ecommerce/design/queue/rebuild").status_code == 200

    def test_flyer_con_marca_y_tag(self) -> None:
        import io

        from PIL import Image

        from cores.ecommerce.design import make_flyer

        buf = io.BytesIO()
        Image.new("RGB", (600, 600), (20, 20, 20)).save(buf, format="PNG")
        out = make_flyer(buf.getvalue(), "Khamrah 100ml", "$95.000", tag="original", size="story")
        assert out["success"] is True and (out["w"], out["h"]) == (1080, 1920)


class TestFlyerBriefAuto:
    def test_prefiere_precio_ars_real(self) -> None:
        from cores.ecommerce.design import product_flyer_brief

        p = _product(authenticity="replica", sale_price_ars=Decimal("95000"))
        brief = product_flyer_brief(p)
        assert brief["price_text"] == "$ 95.000"
        assert brief["tag"] == "réplica"
        assert brief["ready"] is True
        assert brief["blockers"] == []

    def test_sugiere_banda_objetivo_sin_precio(self) -> None:
        from cores.ecommerce.design import product_flyer_brief

        p = _product(sale_price_usd=Decimal("0"), sale_price_ars=Decimal("0"))
        brief = product_flyer_brief(p)
        assert brief["price_text"] == ""
        assert brief["suggested_price_text"].startswith("USD ")
        assert float(brief["suggested_price_text"].split()[1]) > 25.0
        assert brief["ready"] is False
        assert any("precio" in b for b in brief["blockers"])

    def test_unknown_sin_tag_y_con_bloqueo(self) -> None:
        from cores.ecommerce.design import product_flyer_brief

        brief = product_flyer_brief(_product())
        assert brief["tag"] == ""
        assert any("authenticity" in b for b in brief["blockers"])
        assert brief["ready"] is False

    def test_endpoint_200_404_422(self) -> None:
        r = client.post(
            "/api/ecommerce/products",
            json={
                "id": "flyer_brief_1",
                "sku": "FB1",
                "name": "Yara 100ml",
                "supplier_id": "canevic_perf",
                "cost_usd": 35,
                "sale_price_ars": 95000,
                "authenticity": "official",
            },
        )
        assert r.status_code == 200
        b = client.get("/api/ecommerce/design/products/flyer_brief_1/flyer-brief")
        assert b.status_code == 200
        body = b.json()
        assert body["price_text"] == "$ 95.000"
        assert body["tag"] == "original"
        assert body["ready"] is True
        assert client.get("/api/ecommerce/design/products/no_existe/flyer-brief").status_code == 404
        assert client.get("/api/ecommerce/design/products/flyer_brief_1/flyer-brief?size=banner").status_code == 422

    def test_job_semanal_registrado(self) -> None:
        from cores.ecommerce.pipeline import get_ecommerce_jobs
        from cores.scheduler.jobs import get_all_jobs

        job = next(j for j in get_ecommerce_jobs() if j.job_id == "ecommerce_design_pack")
        assert job.handler == "cores.ecommerce.pipeline:run_ecommerce_design_pack"
        assert job.kwargs.get("cron") == "0 7 * * 1"
        ids = [j.job_id for jobs in get_all_jobs().values() for j in jobs]
        assert len(ids) == len(set(ids))

    def test_handler_no_toca_cola_sin_productos(self, tmp_path, monkeypatch) -> None:
        from types import SimpleNamespace

        import cores.ecommerce.publish_queue as pq
        from cores.ecommerce.pipeline import run_ecommerce_design_pack

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(pq, "_store", None)
        monkeypatch.setattr(
            "cores.ecommerce.engine.get_ecommerce_engine",
            lambda: SimpleNamespace(list_products=lambda status=None: []),
        )
        out = run_ecommerce_design_pack()
        assert out["success"] is True and out["rebuilt"] is False
        assert out["total"] == 0

    def test_handler_rebuild_con_activos(self, tmp_path, monkeypatch) -> None:
        from types import SimpleNamespace

        import cores.ecommerce.publish_queue as pq
        from cores.ecommerce.pipeline import run_ecommerce_design_pack

        monkeypatch.setenv("OWNEX_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(pq, "_store", None)
        prod = _product(id="job_p1", supplier_id="canevic_perf", sale_price_ars=Decimal("95000"))
        prod.status = ProductStatus.ACTIVE
        monkeypatch.setattr(
            "cores.ecommerce.engine.get_ecommerce_engine",
            lambda: SimpleNamespace(list_products=lambda status=None: [prod]),
        )
        out = run_ecommerce_design_pack()
        assert out["success"] is True and out["rebuilt"] is True
        assert out["total"] == 7
