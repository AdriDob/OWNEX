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

# ── Fee constants (platform-declared, verify before publishing) ──
DROPSHEABLE_FEE_PCT = 3.0  # Dropsheable declara 3% por venta, sin stock ni mensualidad
VIABLE_MARGIN_PCT = 25.0  # piso VIABLE tras todos los costos
WINNER_MIN_SALES_30D = 8  # ganador: vende ~8+/mes con neto > 0 → escalar
KILL_MIN_DAYS_LIVE = 60  # 0 ventas en 60 días vivo → matar/pausar

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
        platform_fee_pct: float = 0.0,
        tax_pct: float = 0.0,
        other_costs_usd: float = 0.0,
    ) -> dict[str, Any]:
        """NETO REAL: venta − proveedor − Meli − plataforma − impuestos − otros.

        platform_fee_pct: fee del proveedor-plataforma (Dropsheable declara 3%).
        tax_pct: impuestos aplicables (IIBB etc., los confirma el humano vía
        simulador Meli). other_costs_usd: montos fijos extra. Defaults 0 = el
        comportamiento histórico queda intacto (compat hacia atrás).
        """
        cost = Decimal(str(cost_usd))
        shipping = Decimal(str(shipping_usd))
        price = Decimal(str(sale_price_usd))
        fee = price * Decimal(str(marketplace_fee_pct)) / Decimal("100")
        platform_fee = price * Decimal(str(platform_fee_pct)) / Decimal("100")
        tax = price * Decimal(str(tax_pct)) / Decimal("100")
        other = Decimal(str(other_costs_usd))
        total_cost = cost + shipping + fee + platform_fee + tax + other
        margin = price - total_cost
        margin_pct = float(margin / price * 100) if price > 0 else 0.0
        verdict = "VIABLE" if margin_pct >= VIABLE_MARGIN_PCT and margin > 0 else "THIN" if margin > 0 else "REJECT"
        return {
            "cost_usd": float(cost),
            "shipping_usd": float(shipping),
            "fee_usd": float(fee),
            "platform_fee_usd": float(platform_fee),
            "tax_usd": float(tax),
            "other_costs_usd": float(other),
            "total_cost_usd": float(total_cost),
            "margin_usd": float(margin),
            "net_usd": float(margin),
            "margin_pct": round(margin_pct, 1),
            "processing_days": processing_days,
            "verdict": verdict,
            "note": "VIABLE exige margen ≥25% tras Meli + plataforma + impuestos + envío.",
        }

    def suggest_price(
        self,
        cost_usd: float,
        competitor_prices: list[float] | None = None,
        target_margin_pct: float = 35.0,
        shipping_usd: float = 0.0,
        marketplace_fee_pct: float = 13.0,
        platform_fee_pct: float = 0.0,
        tax_pct: float = 0.0,
        other_costs_usd: float = 0.0,
    ) -> dict[str, Any]:
        """Suggest a sale price: max(floor by target margin, 95% of min competitor).

        Pure math, no network. Never below VIABLE (25% margin floor).
        competitor_prices: public prices observed (Meli search, honest input).
        El floor descuenta Meli + plataforma + impuestos + fijos extra.
        """
        try:
            cost = float(cost_usd)
        except (TypeError, ValueError):
            cost = 0.0
        if cost <= 0:
            return {
                "success": False,
                "error": "invalid_cost",
                "suggested_price_usd": 0.0,
                "verdict": "REJECT",
            }
        target = max(VIABLE_MARGIN_PCT, float(target_margin_pct or 35.0))
        # Floor: price s.t. margin after all % fees + fixed costs >= target%.
        # price * (1 - meli% - plat% - tax% - target%) >= cost + ship + other
        fee_rate = float(marketplace_fee_pct or 13.0) / 100.0
        plat_rate = float(platform_fee_pct or 0.0) / 100.0
        tax_rate = float(tax_pct or 0.0) / 100.0
        try:
            other = max(0.0, float(other_costs_usd or 0.0))
        except (TypeError, ValueError):
            other = 0.0
        denom = 1.0 - fee_rate - plat_rate - tax_rate - (target / 100.0)
        if denom <= 0:
            denom = 1.0 - fee_rate - plat_rate - tax_rate - (VIABLE_MARGIN_PCT / 100.0)
        fixed = cost + float(shipping_usd or 0.0) + other
        floor = fixed / denom if denom > 0 else fixed * 1.35
        comps = [float(p) for p in (competitor_prices or []) if isinstance(p, (int, float)) and p > 0]
        if comps:
            suggested = max(floor, min(comps) * 0.95)
            basis = "competitor_undercut_5pct"
        else:
            suggested = floor
            basis = "margin_floor_only"
        suggested = round(max(suggested, 0.01), 2)
        scored = self.score_supplier_offer(
            cost_usd=cost,
            sale_price_usd=suggested,
            shipping_usd=float(shipping_usd or 0.0),
            marketplace_fee_pct=float(marketplace_fee_pct or 13.0),
            platform_fee_pct=float(platform_fee_pct or 0.0),
            tax_pct=float(tax_pct or 0.0),
            other_costs_usd=other,
        )
        return {
            "success": True,
            "suggested_price_usd": suggested,
            "floor_price_usd": round(floor, 2),
            "basis": basis,
            "target_margin_pct": target,
            "competitors_observed": len(comps),
            "min_competitor_usd": min(comps) if comps else 0.0,
            "verdict": scored["verdict"],
            "margin_pct": scored["margin_pct"],
            "margin_usd": scored["margin_usd"],
            "net_usd": scored["net_usd"],
            "platform_fee_usd": scored["platform_fee_usd"],
            "tax_usd": scored["tax_usd"],
        }

    def product_score(
        self,
        *,
        margin_pct: float | None = None,
        demand_0_10: float | None = None,
        competition_0_10: float | None = None,
        rotation_0_10: float | None = None,
        supplier_reliability_0_10: float | None = None,
        fulfillment_ease_0_10: float | None = None,
        ticket_usd: float | None = None,
        return_risk_0_10: float | None = None,
        capital_required_usd: float = 0.0,
        fulfillment_provider: bool = True,
        stock_sync: bool = True,
    ) -> dict[str, Any]:
        """PRODUCT_SCORE = 25% margen + 20% demanda + 15% competencia(inversa)
        + 15% rotación + 10% confiabilidad + 10% facilidad + 5% ticket
        − penalización devoluciones − penalización riesgo.

        Hard gates (modelo $0): CAPITAL_REQUIRED==0, FULFILLMENT_PROVIDER,
        STOCK_SYNC. Si alguno falla → REJECT con razón, sin score.
        UNKNOWN (None) → 5.0 neutral, jamás inventado. Todo 0-10 salvo ticket.
        """
        if float(capital_required_usd or 0.0) > 0:
            return {
                "success": True,
                "score": 0.0,
                "verdict": "REJECT",
                "reason": "capital_required>0 (mayorista, no $0)",
            }
        if not fulfillment_provider:
            return {"success": True, "score": 0.0, "verdict": "REJECT", "reason": "fulfillment no-proveedor"}
        if not stock_sync:
            return {
                "success": True,
                "score": 0.0,
                "verdict": "REJECT",
                "reason": "sin stock sincronizado (riesgo reputación)",
            }

        def _n(v: float | None) -> float:
            try:
                f = float(v)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return 5.0
            return min(10.0, max(0.0, f))

        m = _n(margin_pct if margin_pct is None else min(10.0, float(margin_pct) / 5.0))
        ticket_n = 5.0
        try:
            t = float(ticket_usd) if ticket_usd is not None else None
            ticket_n = 5.0 if t is None else min(10.0, max(0.0, t / 10.0))
        except (TypeError, ValueError):
            ticket_n = 5.0
        score = (
            m * 0.25
            + _n(demand_0_10) * 0.20
            + (10.0 - _n(competition_0_10)) * 0.15
            + _n(rotation_0_10) * 0.15
            + _n(supplier_reliability_0_10) * 0.10
            + _n(fulfillment_ease_0_10) * 0.10
            + ticket_n * 0.05
            - _n(return_risk_0_10) * 0.10
        )
        score = round(min(10.0, max(0.0, score)), 2)
        verdict = "PRIORITY" if score >= 7.0 else ("CANDIDATE" if score >= 5.0 else "DISCARD")
        return {"success": True, "score": score, "verdict": verdict, "reason": ""}


class CompetitorWatch:
    """Pure competitor-signal evaluation (no network here; fetch lives in adapters/jobs).

    Input: our price + observed competitor prices (public Meli search).
    Output: honest action signal — nunca inventa precios, UNKNOWN si sin datos.
    """

    def evaluate(
        self,
        our_price_usd: float,
        competitor_prices: list[float] | None = None,
        competitor_stock: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        try:
            ours = float(our_price_usd)
        except (TypeError, ValueError):
            ours = 0.0
        comps = [float(p) for p in (competitor_prices or []) if isinstance(p, (int, float)) and p > 0]
        if ours <= 0 or not comps:
            return {
                "signal": "UNKNOWN",
                "action": "sin_datos_suficientes",
                "our_price_usd": ours,
                "competitors_observed": len(comps),
                "note": "Sin precio propio o sin competidores observados: no se recomienda acción.",
            }
        min_comp = min(comps)
        avg_comp = sum(comps) / len(comps)
        if ours > min_comp * 1.10:
            return {
                "signal": "OVERPRICED",
                "action": "revisar_pricing",
                "our_price_usd": ours,
                "min_competitor_usd": round(min_comp, 2),
                "avg_competitor_usd": round(avg_comp, 2),
                "gap_pct": round((ours - min_comp) / min_comp * 100, 1),
                "competitors_observed": len(comps),
                "note": f"Estamos {round((ours - min_comp) / min_comp * 100, 1)}% sobre el mínimo. Revisar pricing.",
            }
        stock = competitor_stock or {}
        oos_competitors = sum(1 for v in stock.values() if v is False)
        if oos_competitors > 0 and ours <= min_comp * 1.05:
            return {
                "signal": "OPPORTUNITY",
                "action": "empujar_visibilidad",
                "our_price_usd": ours,
                "min_competitor_usd": round(min_comp, 2),
                "avg_competitor_usd": round(avg_comp, 2),
                "competitors_out_of_stock": oos_competitors,
                "competitors_observed": len(comps),
                "note": "Competidor sin stock y precio competitivo: empujar visibilidad.",
            }
        return {
            "signal": "COMPETITIVE",
            "action": "mantener",
            "our_price_usd": ours,
            "min_competitor_usd": round(min_comp, 2),
            "avg_competitor_usd": round(avg_comp, 2),
            "competitors_observed": len(comps),
            "note": "Precio dentro de rango competitivo.",
        }


class ProductPerformance:
    """MATAR o ESCALAR por datos reales, nunca por especulación (puro, $0).

    Loop: BUSCAR → CALCULAR → PUBLICAR → ESPERAR → MEDIR → MATAR o ESCALAR.
    - ESCALAR: vende ≥8/mes con neto > 0 → empujar visibilidad/stock.
    - REVISAR_PRECIO: vende pero sin neto → no escalar, recalcular NETO REAL.
    - OBSERVAR: vende ocasional → seguir midiendo.
    - TESTING: <30 días vivo → muy pronto para matar, esperar→medir.
    - MATAR: 0 ventas en ≥60 días vivo → pausar/matar, libera tiempo humano.
    El riesgo no es stock ($0) sino tiempo en productos que no venden.
    """

    def classify(
        self,
        sales_30d: int = 0,
        sales_60d: int = 0,
        net_per_sale: float = 0.0,
        days_live: int = 0,
    ) -> dict[str, Any]:
        try:
            s30 = max(0, int(sales_30d or 0))
            s60 = max(0, int(sales_60d or 0))
            live = max(0, int(days_live or 0))
            net = float(net_per_sale or 0.0)
        except (TypeError, ValueError):
            return {
                "verdict": "UNKNOWN",
                "action": "sin_datos_suficientes",
                "note": "Entradas inválidas: no se clasifica.",
            }
        if s60 == 0 and live >= KILL_MIN_DAYS_LIVE:
            return {
                "verdict": "MATAR",
                "action": "pausar_publicacion",
                "note": f"0 ventas en {live} días vivo: pausar, libera tiempo humano.",
            }
        if s60 == 0 and live < 30:
            return {
                "verdict": "TESTING",
                "action": "esperar_medir",
                "note": f"Solo {live} días vivo sin ventas: esperar→medir, muy pronto para matar.",
            }
        if s30 == 0 and s60 == 0:
            return {
                "verdict": "TESTING",
                "action": "esperar_medir",
                "note": "Sin ventas aún en ventana corta: esperar→medir.",
            }
        if net <= 0 and (s30 + s60) > 0:
            return {
                "verdict": "REVISAR_PRECIO",
                "action": "recalcular_neto_real",
                "note": "Vende pero sin neto: recalcular NETO REAL antes de escalar.",
            }
        if s30 >= WINNER_MIN_SALES_30D and net > 0:
            return {
                "verdict": "ESCALAR",
                "action": "empujar_visibilidad",
                "note": f"Ganador: {s30} ventas/30d con neto {round(net, 2)} → escalar.",
            }
        return {
            "verdict": "OBSERVAR",
            "action": "seguir_midiendo",
            "note": "Vende ocasional: seguir midiendo antes de decidir.",
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

    def optimize_for_all_channels(self, product: Product) -> dict[str, MarketplaceListing]:
        """One product -> adapted listing per free channel (deterministic, $0).

        Meli: title 60 + specs. IG: storytelling caption + hashtags in description.
        WA: short catalog copy with price first. TikTok Shop: hook + CTA.
        """
        base_keywords = self.build_keywords(product)
        out: dict[str, MarketplaceListing] = {}
        # Meli: technical, already optimized
        out[Marketplace.MERCADOLIBRE.value] = self.optimize_listing(product, Marketplace.MERCADOLIBRE)
        # Instagram: visual-first caption
        ig = self.optimize_listing(product, Marketplace.INSTAGRAM)
        hashtags = " ".join(f"#{k.replace(' ', '')[:24]}" for k in base_keywords[:12] if k)
        ig_caption = (
            f"{product.name} ✨\n{product.short_description or product.description or ''}\n\n"
            f"{hashtags}\nConsultanos por WhatsApp 👇"
        ).strip()[:2200]
        ig.description = ig_caption
        ig.title = self.optimize_title(product.name, product.brand, product.attributes)[:60]
        out[Marketplace.INSTAGRAM.value] = ig
        # WhatsApp: catalog short copy, price first
        wa = self.optimize_listing(product, Marketplace.WHATSAPP)
        price_txt = f"USD {product.sale_price_usd}" if product.sale_price_usd else "Consultar precio"
        wa_line = f"*{product.name}* — {price_txt}\n{product.short_description or ''}\nStock: a pedido ✅ Envío a todo el país".strip()[
            :1000
        ]
        wa.description = wa_line
        wa.title = product.name[:60]
        out[Marketplace.WHATSAPP.value] = wa
        # TikTok Shop: hook + demo + CTA
        tk = self.optimize_listing(product, Marketplace.TIKTOK_SHOP)
        tk_hook = (
            f"STOP ⛔ ¿Todavía pagás de más por {product.category or 'esto'}?\n"
            f"Probé {product.name} por {price_txt} y esto pasó 👇\n"
            f"✅ {', '.join(base_keywords[:3]) if base_keywords else 'calidad verificada'}\n"
            f"Link en bio / comentario fijo 🔗"
        ).strip()[:1000]
        tk.description = tk_hook
        tk.title = self.optimize_title(product.name, product.brand, product.attributes)[:60]
        out[Marketplace.TIKTOK_SHOP.value] = tk
        return out


class ProductContentPlanner:
    """Deterministic organic-content planner per product ($0, no LLM, no network).

    Generates Short/Reel/Post scripts + hashtags + CTA linking back to listings.
    Publishing itself stays behind Human Gate (MPT / Meta adapters only prepare).
    """

    def plan_product_content(self, product: Product, platform: str = "instagram") -> dict[str, Any]:
        name = (product.name or "producto").strip()
        category = (product.category or "oferta").strip()
        price_txt = f"USD {product.sale_price_usd}" if product.sale_price_usd else "precio por WhatsApp"
        keywords = ListingOptimizer().build_keywords(product)
        kw_line = ", ".join(keywords[:5]) if keywords else category
        hook = f"Probé {name} por {price_txt} — ¿vale la pena? 🤔"
        script_lines = [
            f"HOOK (0-3s): {hook}",
            f"PROBLEMA (3-10s): Conseguir {category} bueno sin pagar de más es difícil.",
            f"DEMO (10-30s): {name} en uso real. Detalle: {kw_line}.",
            f"PRUEBA (30-40s): Precio {price_txt}, pedido a contra-entrega / MercadoLibre con protección.",
            "CTA (40-45s): Link en bio / comentario fijo / escribinos por WhatsApp. Seguinos para más reviews honestas.",
        ]
        hashtags = [f"#{k.replace(' ', '')[:24]}" for k in keywords[:12] if k]
        for extra in ("reviewhonesta", "ofertasargentina", "dropshippingar"):
            if f"#{extra}" not in hashtags:
                hashtags.append(f"#{extra}")
        return {
            "product_id": product.id,
            "platform": platform,
            "hook": hook,
            "script": "\n".join(script_lines),
            "hashtags": hashtags[:15],
            "cta": "Link en bio / comentario fijo / WhatsApp directo",
            "affiliate_slot": "pegar_link_afiliado_aqui",
            "note": "Contenido orgánico $0. Publicar requiere aprobación humana.",
        }


class OrderOrchestrator:
    """Zero-stock fulfillment: customer order -> supplier purchase -> tracking."""

    def route_to_best_supplier(
        self,
        order_items: list[OrderItem],
        supplier_offers: dict[str, dict[str, float]] | None = None,
        supplier_meta: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, Any]:
        """Route each item to the best supplier (pure, deterministic, $0).

        supplier_offers: {supplier_id: {product_id: unit_cost_usd}}.
        supplier_meta: {supplier_id: {processing_days, rating, shipping_usd}}.
        Priority: 1) lowest landed cost 2) fastest processing 3) highest rating.
        Items without any offer stay in "unrouted" (honest, never invented).
        """
        offers = supplier_offers or {}
        meta = supplier_meta or {}
        routed: dict[str, list[str]] = {}
        unrouted: list[str] = []
        details: list[dict[str, Any]] = []
        for item in order_items or []:
            best_sid: str | None = None
            best_key: tuple | None = None
            for sid, catalog in offers.items():
                if item.product_id not in catalog:
                    continue
                try:
                    unit = float(catalog[item.product_id])
                except (TypeError, ValueError):
                    continue
                if unit <= 0:
                    continue
                m = meta.get(sid, {}) if isinstance(meta.get(sid), dict) else {}
                try:
                    ship = float(m.get("shipping_usd", 0.0) or 0.0)
                except (TypeError, ValueError):
                    ship = 0.0
                try:
                    proc = float(m.get("processing_days", 3) or 3)
                except (TypeError, ValueError):
                    proc = 3.0
                try:
                    rating = float(m.get("rating", 0.0) or 0.0)
                except (TypeError, ValueError):
                    rating = 0.0
                key = (round(unit + ship, 2), round(proc, 2), round(-rating, 2), sid)
                if best_key is None or key < best_key:
                    best_key = key
                    best_sid = sid
            if best_sid is None:
                unrouted.append(item.product_id)
                details.append({"product_id": item.product_id, "supplier_id": None, "reason": "no_offer"})
            else:
                routed.setdefault(best_sid, []).append(item.product_id)
                details.append({"product_id": item.product_id, "supplier_id": best_sid, "reason": "best_landed_cost"})
        return {"routed": routed, "unrouted": unrouted, "details": details}

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
_competitor: CompetitorWatch | None = None
_planner: ProductContentPlanner | None = None


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


def get_competitor_watch() -> CompetitorWatch:
    global _competitor
    if _competitor is None:
        _competitor = CompetitorWatch()
    return _competitor


_performance: ProductPerformance | None = None


def get_product_performance() -> ProductPerformance:
    global _performance
    if _performance is None:
        _performance = ProductPerformance()
    return _performance


def get_content_planner() -> ProductContentPlanner:
    global _planner
    if _planner is None:
        _planner = ProductContentPlanner()
    return _planner


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


def run_ecommerce_competitor_watch() -> dict[str, Any]:
    """Evaluate competitor signals from stored snapshots (no network, never raises)."""
    try:
        from cores.ecommerce.engine import get_ecommerce_engine

        engine = get_ecommerce_engine()
        snaps = engine.list_competitor_snapshots(limit=200)
        overpriced = sum(1 for s in snaps if s.signal == "OVERPRICED")
        opportunities = sum(1 for s in snaps if s.signal == "OPPORTUNITY")
        return {
            "success": True,
            "snapshots": len(snaps),
            "overpriced": overpriced,
            "opportunities": opportunities,
        }
    except Exception as exc:
        logger.warning("ecommerce competitor watch failed: %s", exc)
        return {"success": False, "error": "watch_failed"}


def run_ecommerce_supplier_scorecards() -> dict[str, Any]:
    """Recalculate supplier scorecards from local history (never raises)."""
    try:
        from cores.ecommerce.engine import get_ecommerce_engine

        engine = get_ecommerce_engine()
        updated = engine.update_supplier_scorecards()
        return {"success": True, "suppliers_updated": updated}
    except Exception as exc:
        logger.warning("ecommerce scorecards failed: %s", exc)
        return {"success": False, "error": "scorecards_failed"}


def run_ecommerce_review_request() -> dict[str, Any]:
    """Prepare review asks for DELIVERED orders >10d without ask (never sends alone)."""
    try:
        from cores.ecommerce.engine import get_ecommerce_engine

        engine = get_ecommerce_engine()
        prepared = engine.prepare_review_requests(days_after_delivery=10)
        return {"success": True, "prepared": prepared}
    except Exception as exc:
        logger.warning("ecommerce review request failed: %s", exc)
        return {"success": False, "error": "review_failed"}


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
        _cron_job(
            job_id="ecommerce_competitor_watch",
            app_id="ecommerce",
            handler="cores.ecommerce.pipeline:run_ecommerce_competitor_watch",
            cron="0 6 * * *",
            args=[],
            metadata={"cycle": "ecommerce", "type": "intel", "desc": "señales competidores diaria 06:00"},
        ),
        _cron_job(
            job_id="ecommerce_supplier_scorecards",
            app_id="ecommerce",
            handler="cores.ecommerce.pipeline:run_ecommerce_supplier_scorecards",
            cron="30 6 * * *",
            args=[],
            metadata={"cycle": "ecommerce", "type": "health", "desc": "scorecards proveedores diaria 06:30"},
        ),
        _cron_job(
            job_id="ecommerce_review_request",
            app_id="ecommerce",
            handler="cores.ecommerce.pipeline:run_ecommerce_review_request",
            cron="0 10 * * *",
            args=[],
            metadata={"cycle": "ecommerce", "type": "engagement", "desc": "pide reviews 10d post-entrega 10:00"},
        ),
    ]
