"""Tests for ingeniously-free ecommerce upgrades + zero-invest services.

Fase 1 auto-pricing, competitor watch, Fase 2 routing, Fase 3 scorecards,
Fase 4 cross-listing, Fase 5 content plan, Fase 6 reviews/carts,
Fase 7 affiliate, Fase 8 lead enrich/export/arbitrage + factory/curation/packs.
All pure/deterministic, zero network.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.affiliate import router as affiliate_router
from api.routers.client_acquisition import router as ca_router
from api.routers.ecommerce import router as eco_router
from api.routers.zero_invest import router as zi_router
from cores.affiliate import get_affiliate_engine
from cores.client_acquisition import ClientAcquisitionEngine, LeadSource, ProjectType
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
)
from cores.ecommerce.pipeline import (
    CompetitorWatch,
    ProductContentPlanner,
    get_listing_optimizer,
    get_order_orchestrator,
    get_sourcing_engine,
    run_ecommerce_competitor_watch,
    run_ecommerce_review_request,
    run_ecommerce_supplier_scorecards,
)

eco_app = FastAPI()
eco_app.include_router(eco_router)
eco_client = TestClient(eco_app)

aff_app = FastAPI()
aff_app.include_router(affiliate_router)
aff_client = TestClient(aff_app)

zi_app = FastAPI()
zi_app.include_router(zi_router)
zi_client = TestClient(zi_app)

ca_app = FastAPI()
ca_app.include_router(ca_router)
ca_client = TestClient(ca_app)


def _product(pid="p1") -> Product:
    return Product(
        id=pid,
        sku="SKU-1",
        name="Perfume Árabe Noche",
        description="Perfume nicho intenso",
        short_description="Nicho intenso",
        category="perfumes",
        brand="Droppinglabel",
        supplier_id="sup_1",
        cost_usd=Decimal("20"),
        sale_price_usd=Decimal("59.99"),
        images=["https://example.com/img.jpg"],
        tags=["arabe", "noche"],
        status=ProductStatus.ACTIVE,
    )


def test_suggest_price_floor_and_undercut() -> None:
    eng = get_sourcing_engine()
    no_comp = eng.suggest_price(cost_usd=20, competitor_prices=None)
    assert no_comp["success"] is True
    assert no_comp["basis"] == "margin_floor_only"
    assert no_comp["verdict"] == "VIABLE"
    with_comp = eng.suggest_price(cost_usd=20, competitor_prices=[100.0, 90.0])
    assert with_comp["suggested_price_usd"] == round(90.0 * 0.95, 2)
    bad = eng.suggest_price(cost_usd=0)
    assert bad["success"] is False


def test_competitor_watch_signals() -> None:
    watch = CompetitorWatch()
    assert watch.evaluate(0, []).get("signal") == "UNKNOWN"
    over = watch.evaluate(120, [100.0])
    assert over["signal"] == "OVERPRICED"
    assert over["action"] == "revisar_pricing"
    ok = watch.evaluate(99, [100.0, 102.0])
    assert ok["signal"] in ("COMPETITIVE", "OPPORTUNITY")


def test_route_to_best_supplier() -> None:
    orch = get_order_orchestrator()
    items = [OrderItem(product_id="p1", listing_id="l1", quantity=1)]
    res = orch.route_to_best_supplier(
        items,
        supplier_offers={"s1": {"p1": 20.0}, "s2": {"p1": 18.0}},
        supplier_meta={"s1": {"processing_days": 2, "rating": 5}, "s2": {"processing_days": 5, "rating": 4}},
    )
    assert res["routed"] == {"s2": ["p1"]}
    assert res["unrouted"] == []
    missing = orch.route_to_best_supplier(items, supplier_offers={})
    assert missing["unrouted"] == ["p1"]


def test_cross_listing_four_channels() -> None:
    out = get_listing_optimizer().optimize_for_all_channels(_product())
    assert set(out.keys()) == {"mercadolibre", "instagram", "whatsapp", "tiktok_shop"}
    assert all(lst.title for lst in out.values())


def test_content_planner_script() -> None:
    plan = ProductContentPlanner().plan_product_content(_product(), platform="instagram")
    assert "HOOK" in plan["script"]
    assert len(plan["hashtags"]) >= 3


def test_engine_competitor_snapshot_and_watch_job() -> None:
    engine = EcommerceEngine()
    engine.add_product(_product())
    snap = engine.record_competitor_snapshot("p1", [100.0], source="manual")
    assert snap.signal in ("OVERPRICED", "COMPETITIVE", "OPPORTUNITY", "UNKNOWN")
    assert run_ecommerce_competitor_watch()["success"] is True


def test_engine_scorecards_and_job() -> None:
    engine = EcommerceEngine()
    engine.add_supplier(Supplier(id="sup_1", name="S1", type=SupplierType.LOCAL_AR, rating=4.5))
    assert engine.update_supplier_scorecards() == 0
    assert run_ecommerce_supplier_scorecards()["success"] is True


def test_engine_reviews_and_carts() -> None:
    engine = EcommerceEngine()
    order = Order(
        id="o1",
        marketplace=Marketplace.MERCADOLIBRE,
        status=OrderStatus.DELIVERED,
        delivered_at=datetime.now(UTC) - timedelta(days=11),
    )
    engine.add_order(order)
    assert engine.prepare_review_requests(days_after_delivery=10) == 1
    assert run_ecommerce_review_request()["success"] is True
    cart = engine.track_cart_view("v1", "p1")
    assert cart.id
    # carts are fresh (<30m) so none abandoned yet
    assert engine.list_abandoned_carts(minutes_idle=60) == []


def test_ecommerce_api_new_endpoints() -> None:
    assert eco_client.post("/api/ecommerce/sourcing/suggest-price", json={"cost_usd": 20}).status_code == 200
    assert eco_client.get("/api/ecommerce/intel/competitors").status_code == 200
    assert (
        eco_client.post(
            "/api/ecommerce/orders/route",
            json={"items": [], "supplier_offers": {}, "supplier_meta": {}},
        ).status_code
        == 200
    )
    assert eco_client.post("/api/ecommerce/suppliers/scorecards/refresh").status_code == 200
    assert eco_client.get("/api/ecommerce/suppliers/scorecards").status_code == 200
    assert eco_client.post("/api/ecommerce/reviews/prepare").status_code == 200
    assert eco_client.get("/api/ecommerce/reviews").status_code == 200
    assert (
        eco_client.post("/api/ecommerce/carts/track", json={"visitor_id": "v", "product_id": "p1"}).status_code == 200
    )
    assert eco_client.get("/api/ecommerce/carts/abandoned").status_code == 200


def test_affiliate_flow(tmp_path, monkeypatch) -> None:
    import api.routers.affiliate as aff_router_mod
    from cores.affiliate import AffiliateEngine

    monkeypatch.setattr(aff_router_mod, "get_affiliate_engine", lambda: AffiliateEngine(path=tmp_path / "aff.json"))
    link = aff_client.post(
        "/api/affiliate/links", json={"url": "https://amazon.com/dp/X", "product_name": "Test", "network": "amazon"}
    )
    assert link.status_code == 200
    lid = link.json()["id"]
    assert aff_client.post(f"/api/affiliate/links/{lid}/click").status_code == 200
    conv = aff_client.post(f"/api/affiliate/links/{lid}/conversion", json={"earned_usd": 5.0})
    assert conv.json()["earned_usd"] == 5.0
    plan = aff_client.post("/api/affiliate/contents/plan", json={"product_name": "Test", "link_ids": [lid]})
    assert plan.status_code == 200
    cid = plan.json()["id"]
    assert aff_client.post(f"/api/affiliate/contents/{cid}/ready").status_code == 200
    assert aff_client.get("/api/affiliate/status").status_code == 200
    eng = get_affiliate_engine()
    assert eng.funnel()["clicks"] >= 0


def test_lead_enrich_export_arbitrage() -> None:
    eng = ClientAcquisitionEngine()
    lead = eng.capture_lead("Panadería Sur", source=LeadSource.DIRECTORY_SCRAPE, business_type="panadería")
    enriched = eng.enrich_lead(lead.id, email="hola@panaderia.test", city="Quilmes")
    assert enriched is not None and enriched.enriched is True
    assert eng.score_lead(lead) >= 60
    assert len(eng.export_qualified(min_score=60)) >= 1
    prop = eng.generate_proposal(lead.id, project_type=ProjectType.CORPORATE_WEB, pages=5)
    assert prop is not None
    proj = eng.start_project(lead.id, prop.id)
    assert proj is not None
    arb = eng.plan_arbitrage(proj.id, freelancer_cost_usd=100, client_price_usd=300)
    assert arb["success"] is True and arb["verdict"] == "VIABLE"
    # API
    assert ca_client.get("/api/client-acquisition/leads/export/qualified").status_code == 200


def test_zero_invest_services() -> None:
    assert zi_client.get("/api/zero-invest/report-factory/catalog").status_code == 200
    build = zi_client.post(
        "/api/zero-invest/report-factory/build",
        json={"platform": "hackerone", "data": {"title": "IDOR en perfil", "description": "d", "severity": "high"}},
    )
    assert build.status_code == 200
    assert "checklist" in build.json()
    bad = zi_client.post("/api/zero-invest/report-factory/build", json={"platform": "nope", "data": {"title": "x"}})
    assert bad.status_code == 422
    cur = zi_client.post(
        "/api/zero-invest/data-curation/curate",
        json={"items": [{"text": "Pasos para reproducir IDOR en endpoint /api/users/123 con curl y validación " * 5}]},
    )
    assert cur.json()["added"] >= 1
    assert zi_client.get("/api/zero-invest/data-curation/package").status_code == 200
    assert zi_client.get("/api/zero-invest/security-packs").status_code == 200
    assert zi_client.get("/api/zero-invest/security-packs/api_security_audit").status_code == 200
    assert zi_client.get("/api/zero-invest/automation/offers").status_code == 200
    assert zi_client.post("/api/zero-invest/automation/offers/scrape_to_sheets/quote").status_code == 200


def _order_with_sale(
    engine: EcommerceEngine,
    order_id: str,
    product_id: str,
    qty: int,
    price: float,
    cost: float,
    days_ago: int = 5,
    status: OrderStatus = OrderStatus.DELIVERED,
    paid: bool = True,
) -> None:
    from cores.ecommerce.models import PaymentStatus

    created = datetime.now(UTC) - timedelta(days=days_ago)
    order = Order(
        id=order_id,
        marketplace=Marketplace.MERCADOLIBRE,
        status=status,
        payment_status=PaymentStatus.PAID if paid else PaymentStatus.PENDING,
        items=[
            OrderItem(
                product_id=product_id,
                listing_id="meli:x",
                quantity=qty,
                unit_price_usd=Decimal(str(price)),
                unit_cost_usd=Decimal(str(cost)),
                total_price_usd=Decimal(str(price * qty)),
                total_cost_usd=Decimal(str(cost * qty)),
                margin_usd=Decimal(str((price - cost) * qty)),
            )
        ],
        created_at=created,
        delivered_at=created if status == OrderStatus.DELIVERED else None,
    )
    order.calculate_totals()
    engine.add_order(order)


def test_net_real_breakdown_dropsheable_3pct() -> None:
    eng = get_sourcing_engine()
    # 39.990 venta, 25.000 costo, Meli 13%, Dropsheable 3%: neto = venta − todo
    res = eng.score_supplier_offer(cost_usd=25000, sale_price_usd=39990, marketplace_fee_pct=13.0, platform_fee_pct=3.0)
    assert res["platform_fee_usd"] == round(39990 * 0.03, 2)
    assert res["net_usd"] == round(39990 - 25000 - 39990 * 0.13 - 39990 * 0.03, 2)
    assert res["net_usd"] == res["margin_usd"]
    # compat: sin fees nuevos el cálculo histórico no cambia
    old = eng.score_supplier_offer(cost_usd=20, sale_price_usd=60, shipping_usd=5)
    assert old["platform_fee_usd"] == 0.0
    assert old["tax_usd"] == 0.0
    assert old["verdict"] == "VIABLE"


def test_suggest_price_floor_rises_with_platform_fee() -> None:
    eng = get_sourcing_engine()
    plain = eng.suggest_price(cost_usd=25000, target_margin_pct=35.0)
    with_fee = eng.suggest_price(cost_usd=25000, target_margin_pct=35.0, platform_fee_pct=3.0)
    assert with_fee["success"] is True
    assert with_fee["suggested_price_usd"] > plain["suggested_price_usd"]
    assert with_fee["platform_fee_usd"] > 0


def test_performance_classify_verdicts() -> None:
    from cores.ecommerce.pipeline import get_product_performance

    clf = get_product_performance()
    assert clf.classify(sales_30d=10, sales_60d=15, net_per_sale=6000, days_live=90)["verdict"] == "ESCALAR"
    assert clf.classify(sales_30d=0, sales_60d=0, net_per_sale=0, days_live=70)["verdict"] == "MATAR"
    assert clf.classify(sales_30d=0, sales_60d=0, net_per_sale=0, days_live=10)["verdict"] == "TESTING"
    assert clf.classify(sales_30d=3, sales_60d=5, net_per_sale=0, days_live=90)["verdict"] == "REVISAR_PRECIO"
    assert clf.classify(sales_30d=3, sales_60d=5, net_per_sale=4000, days_live=90)["verdict"] == "OBSERVAR"


def test_engine_performance_and_funnel() -> None:
    engine = EcommerceEngine()
    engine.add_supplier(Supplier(id="sup_1", name="Dropsheable", type=SupplierType.DROPSHEABLE))
    winner = _product("win1")
    engine.add_product(winner)
    _order_with_sale(engine, "o-win", "win1", qty=10, price=39990, cost=25000, days_ago=5)
    dead = _product("dead1")
    dead.created_at = datetime.now(UTC) - timedelta(days=70)
    engine.add_product(dead)
    perf = engine.product_performance(platform_fee_pct=3.0)
    by_id = {r["product_id"]: r for r in perf}
    assert by_id["win1"]["verdict"] == "ESCALAR"
    assert by_id["win1"]["net_per_sale"] > 0
    assert by_id["dead1"]["verdict"] == "MATAR"
    funnel = engine.portfolio_funnel(platform_fee_pct=3.0)
    assert funnel["publications"] == 2
    assert funnel["winners"] == 1
    assert funnel["to_kill"] == 1


def test_engine_objectives_o1_o6_and_hourly() -> None:
    engine = EcommerceEngine()
    engine.add_supplier(Supplier(id="sup_1", name="Dropsheable", type=SupplierType.DROPSHEABLE))
    engine.add_product(_product("p1"))
    fresh = engine.experiment_objectives()
    assert fresh["o1_first_sale"] is False
    assert fresh["net_per_human_hour"] is None
    _order_with_sale(engine, "o1", "p1", qty=1, price=39990, cost=25000, days_ago=2)
    done = engine.experiment_objectives(human_hours=4.0, platform_fee_pct=3.0)
    assert done["o1_first_sale"] is True
    assert done["o2_first_fulfilled_collected"] is True
    assert done["o5_net_per_human_hour_known"] is True
    assert done["net_per_human_hour"] == round(done["net_total"] / 4.0, 2)
    cancelled = Order(id="o-x", marketplace=Marketplace.MERCADOLIBRE, status=OrderStatus.CANCELLED)
    engine.add_order(cancelled)
    again = engine.experiment_objectives()
    assert again["sales_total"] == 1


def test_net_real_and_intel_endpoints() -> None:
    res = eco_client.post(
        "/api/ecommerce/sourcing/net-real",
        json={"cost_usd": 25000, "sale_price_usd": 39990, "marketplace_fee_pct": 13.0, "platform_fee_pct": 3.0},
    )
    assert res.status_code == 200
    assert res.json()["net_usd"] == round(39990 - 25000 - 39990 * 0.13 - 39990 * 0.03, 2)
    scored = eco_client.post("/api/ecommerce/sourcing/score", json={"cost_usd": 20, "sale_price_usd": 60})
    assert scored.json()["verdict"] == "VIABLE"
    assert eco_client.get("/api/ecommerce/intel/winners").status_code == 200
    assert eco_client.get("/api/ecommerce/intel/objectives?human_hours=2").status_code == 200


def test_affiliate_persists_across_restart(tmp_path) -> None:
    from cores.affiliate import AffiliateEngine, AffiliateNetwork

    eng = AffiliateEngine(path=tmp_path / "aff.json")
    link = eng.add_link(url="https://amazon.com/dp/Y", product_name="Persist", network=AffiliateNetwork.AMAZON)
    assert link is not None
    eng.record_click(link.id)
    eng.record_conversion(link.id, earned_usd=7.5)
    content = eng.plan_content(product_name="Persist", link_ids=[link.id])
    eng.mark_ready(content.id)
    eng2 = AffiliateEngine(path=tmp_path / "aff.json")
    got = eng2.get_link(link.id)
    assert got is not None and got.clicks == 1 and got.conversions == 1 and got.earned_usd == 7.5
    assert eng2.funnel()["earned_confirmed_usd"] == 7.5


def test_affiliate_corrupt_file_never_raises(tmp_path) -> None:
    from cores.affiliate import AffiliateEngine

    bad = tmp_path / "aff.json"
    bad.write_text("{no-json", encoding="utf-8")
    eng = AffiliateEngine(path=bad)
    assert eng.funnel()["links"] == 0
