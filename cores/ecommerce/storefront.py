"""Vidriera estática Droppinglabel — catálogo público $0 sin checkout online.

Genera un `index.html` autocontenido desde productos ACTIVE reales: foto,
precio VIABLE, tag de autenticidad y botón de pedido por WhatsApp (o link a
Meli si existe listing). Sin servidor, sin pasarela, sin costo fijo: se sube
tal cual a GitHub Pages/Netlify y el cierre es por WhatsApp (humano).

Reglas honestas: solo productos ACTIVE con precio real > 0; sin precio no hay
tarjeta (jamás precio inventado); tag de autenticidad siempre visible;
sin ACTIVE el HTML lo dice en vez de mostrar vidriera vacía.
"""

from __future__ import annotations

import html
import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

logger = logging.getLogger("ownex.ecommerce.storefront")

STOREFRONT_FILENAME = "droppinglabel_index.html"


def _price_text(sale_price_ars: Any, sale_price_usd: Any) -> str:
    """Precio ARS preferido; USD solo si no hay ARS. Vacío si no hay precio real."""
    from cores.ecommerce.design import _money_text

    ars = _money_text(sale_price_ars, "ARS")
    if ars:
        return ars
    return _money_text(sale_price_usd, "USD")


def _wa_order_url(body_product: str, wa_number: str = "") -> str:
    """Link de pedido por WhatsApp con texto pre-cargado (número del dueño o genérico)."""
    msg = f"Hola Droppinglabel! Me interesa {body_product}. ¿Sigue disponible? ¿Precio + envío?"
    base = f"https://wa.me/{wa_number}" if wa_number.strip() else "https://wa.me/"
    return f"{base}?text={quote(msg)}"


NICHE_TITLES = {
    "perfumes": "Perfumes árabes y nicho",
    "relojes": "Relojes y accesorios",
    "futbol": "Fútbol",
    "urbana": "Ropa urbana",
    "accesorios": "Accesorios",
    "generic": "Destacados",
}

NICHE_ORDER = ("perfumes", "relojes", "futbol", "urbana", "accesorios", "generic")

TRUST_BADGES = (
    ("Envío a todo el país", "Despacho con tracking 24-72h"),
    ("Pago a contra entrega de información", "Transferencia y MercadoPago, se reserva con el pago"),
    ("Originalidad declarada", "Réplica se vende como réplica, original con lote"),
    ("Atención por WhatsApp", "Respondemos precio, stock y envío"),
)

FAQ_ITEMS = (
    (
        "¿Cómo compro?",
        "Elegí el producto, tocá Pedir por WhatsApp y coordinamos pago y envío. Se reserva con el pago.",
    ),
    (
        "¿Cuánto tarda el envío?",
        "Despacho en 24-72h con tracking a todo el país. Las camisetas retro por encargo llevan 12 días hábiles y se avisa antes de comprar.",
    ),
    (
        "¿Qué medios de pago aceptan?",
        "Transferencia y MercadoPago. La reserva se confirma con el pago.",
    ),
    (
        "¿Tienen cambios y devoluciones?",
        "Sí, por falla o error de talle/producto dentro de los 10 días de recibido. Escribinos por WhatsApp con foto.",
    ),
    (
        "¿Los productos son originales?",
        "Cada ficha lo declara: original, licencia oficial o réplica. Lo que es réplica se vende descrita tal cual, jamás como original.",
    ),
)


def _card(p: dict[str, Any], wa_number: str) -> str | None:
    """Una ficha de producto. None si no hay nombre o precio real."""
    from cores.ecommerce.design import AUTH_TAG

    try:
        name = str(p.get("name", "") or "").strip()
        if not name:
            return None
        price = _price_text(p.get("sale_price_ars"), p.get("sale_price_usd"))
        if not price:
            return None  # sin precio real no hay tarjeta
        tag = AUTH_TAG.get(str(p.get("authenticity", "unknown") or "unknown").lower(), "")
        tag_html = f'<span class="tag">{html.escape(tag)}</span>' if tag else ""
        img = str(p.get("image", "") or "")
        img_html = (
            f'<img src="{html.escape(img)}" alt="{html.escape(name)}" loading="lazy"/>'
            if img.startswith("http")
            else ""
        )
        meli = str(p.get("meli_url", "") or "")
        buy_html = (
            f'<a class="btn meli" href="{html.escape(meli)}" target="_blank" rel="noopener">Comprar en Meli</a>'
            if meli.startswith("http")
            else ""
        )
        niche = html.escape(str(p.get("niche", "") or ""))
        return (
            "<article class='card'>"
            f"{img_html}<h3>{html.escape(name)}</h3>"
            f"<p class='price'>{html.escape(price)}</p>"
            f"<p class='meta'>{niche} {tag_html}</p>"
            f"<a class='btn wa' href='{html.escape(_wa_order_url(f'{name} ({price})', wa_number))}'"
            " target='_blank' rel='noopener'>Pedir por WhatsApp</a>"
            f"{buy_html}</article>"
        )
    except Exception:
        return None


_CSS = (
    "body{font-family:system-ui,-apple-system,sans-serif;background:#0b0b0e;color:#f5f5f5;margin:0;line-height:1.5}"
    ".bar{background:#FFE600;color:#000;text-align:center;font-size:.85em;font-weight:600;padding:8px 12px}"
    "nav{position:sticky;top:0;background:#0b0b0ee6;border-bottom:1px solid #222;padding:10px 16px;"
    "display:flex;gap:12px;align-items:center;flex-wrap:wrap;backdrop-filter:blur(6px)}"
    "nav b{margin-right:auto}nav a{color:#f5f5f5;text-decoration:none;font-size:.9em}"
    "nav a.cta{background:#fff;color:#000;font-weight:700;border-radius:8px;padding:6px 12px}"
    ".hero{padding:56px 24px;text-align:center;max-width:760px;margin:0 auto}"
    ".hero h1{font-size:2.2em;margin:.2em 0}.hero p{color:#bdbdc7}"
    ".hero .btn{display:inline-block;margin:8px 6px 0;padding:12px 24px}"
    ".trust{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;padding:0 24px 8px}"
    ".trust div{border:1px solid #26262e;border-radius:10px;padding:12px;font-size:.9em}"
    ".trust b{display:block}.trust span{color:#bdbdc7}"
    "section.cat{padding:8px 24px}section.cat h2{border-bottom:1px solid #222;padding-bottom:8px}"
    ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;padding:16px 0}"
    ".card{background:#15151a;border:1px solid #26262e;border-radius:12px;padding:16px}"
    ".card img{width:100%;border-radius:8px}.price{font-size:1.3em;font-weight:700}"
    ".tag{border:1px solid #444;border-radius:20px;padding:2px 10px;font-size:.8em}"
    ".btn{display:block;text-align:center;margin-top:10px;padding:10px;border-radius:8px;"
    "text-decoration:none;font-weight:600}.wa{background:#fff;color:#000}"
    ".meli{background:#FFE600;color:#000}"
    ".steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;padding:0 24px}"
    ".steps div{border:1px solid #26262e;border-radius:10px;padding:12px}"
    "details{border:1px solid #26262e;border-radius:10px;margin:8px 24px;padding:12px}"
    "summary{cursor:pointer;font-weight:600}footer{padding:32px 24px;text-align:center;color:#8a8a94;font-size:.85em}"
    ".float{position:fixed;right:16px;bottom:16px;background:#25D366;color:#000;font-weight:700;"
    "border-radius:40px;padding:14px 20px;text-decoration:none}"
    ".empty{padding:48px;text-align:center}"
    "@media(max-width:600px){.hero{padding:36px 16px}.hero h1{font-size:1.7em}}"
)


def _faq_html() -> str:
    parts = ["<section><h2 style='padding:0 24px'>Preguntas frecuentes</h2>"]
    for q, a in FAQ_ITEMS:
        parts.append(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>")
    parts.append("</section>")
    return "".join(parts)


def _json_ld(brand: str, cards_count: int) -> str:
    data = (
        '{"@context":"https://schema.org","@type":"Store",'
        f'"name":{json_dumps(brand)},"description":"Dropshipping local AR sin stock propio.",'
        f'"numberOfItems":{cards_count}}}'
    )
    return f"<script type='application/ld+json'>{data}</script>"


def json_dumps(value: str) -> str:
    """JSON string seguro sin importar json en el render (nombres con comillas)."""
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_storefront(
    products: list[dict[str, Any]],
    brand: str = "Droppinglabel",
    wa_number: str = "",
) -> str:
    """Render puro: lista de dicts de producto → HTML autocontenido. Nunca raisea."""
    try:
        by_niche: dict[str, list[str]] = {}
        total = 0
        for p in products or []:
            card = _card(p, wa_number)
            if not card:
                continue
            total += 1
            key = str(p.get("niche", "") or "generic")
            by_niche.setdefault(key, []).append(card)
        brand_esc = html.escape(brand or "Droppinglabel")
        wa_all = html.escape(_wa_order_url("catálogo", wa_number))
        if not total:
            body = (
                "<main class='empty'><h1>Catálogo en preparación</h1>"
                "<p>Todavía no hay productos ACTIVE con precio. "
                "Estamos verificando proveedores — volvé pronto.</p></main>"
            )
            nav_links = ""
            sections = ""
        else:
            present = [n for n in NICHE_ORDER if by_niche.get(n)] + [n for n in by_niche if n not in NICHE_ORDER]
            nav_links = "".join(
                f"<a href='#{html.escape(n)}'>{html.escape(NICHE_TITLES.get(n, n))}</a>" for n in present
            )
            sections = "".join(
                f"<section class='cat' id='{html.escape(n)}'>"
                f"<h2>{html.escape(NICHE_TITLES.get(n, n))}</h2>"
                f"<div class='grid'>{''.join(by_niche[n])}</div></section>"
                for n in present
            )
            trust = "".join(f"<div><b>{html.escape(t)}</b><span>{html.escape(d)}</span></div>" for t, d in TRUST_BADGES)
            body = (
                f"<div class='hero'><h1>{brand_esc}</h1>"
                "<p>Curaduría local sin stock propio: pedís por WhatsApp, el proveedor despacha con tracking.</p>"
                f"<a class='btn wa' href='#perfumes'>Ver catálogo</a> "
                f"<a class='btn meli' href='{wa_all}' target='_blank' rel='noopener'>Consultar por WhatsApp</a></div>"
                f"<div class='trust'>{trust}</div>"
                f"{sections}"
                "<div class='steps'><div><b>1 · Elegí</b><br/>Navegá por categoría con precio a la vista.</div>"
                "<div><b>2 · Escribinos</b><br/>El botón arma tu mensaje con el producto.</div>"
                "<div><b>3 · Coordinamos</b><br/>Pago y envío a todo el país con tracking.</div></div>"
                f"{_faq_html()}"
            )
        return (
            "<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'/>"
            f"<meta name='description' content='{brand_esc}: catálogo sin stock propio, pedido por WhatsApp, envío a todo el país'/>"
            f"<title>{brand_esc} — catálogo</title>"
            f"{_json_ld(brand or 'Droppinglabel', total)}"
            f"<style>{_CSS}</style></head><body>"
            "<div class='bar'>Envío a todo el país · Transferencia y MercadoPago · Seña por WhatsApp</div>"
            f"<nav><b>{brand_esc}</b>{nav_links}"
            f"<a class='cta' href='{wa_all}' target='_blank' rel='noopener'>WhatsApp</a></nav>"
            f"<header style='padding:8px 24px'><p>{total} productos · precios ARS</p></header>"
            f"{body}"
            f"<a class='float' href='{wa_all}' target='_blank' rel='noopener'>WhatsApp</a>"
            "<footer><p>Dropshipping local AR · sin stock propio · precios ARS</p></footer>"
            "</body></html>"
        )
    except Exception as exc:
        logger.warning("storefront: render falló: %s", exc)
        return "<!DOCTYPE html><html><body><p>Catálogo no disponible.</p></body></html>"


def active_products_for_storefront(engine: Any) -> list[dict[str, Any]]:
    """Lee ACTIVE del engine y los deja listos para render (nunca raisea)."""
    from cores.ecommerce.models import ProductStatus
    from cores.ecommerce.outreach import niche_for

    try:
        items = engine.list_products(status=ProductStatus.ACTIVE) or []
    except Exception as exc:
        logger.warning("storefront: no se pudo leer ACTIVE: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for p in items:
        try:
            listings = getattr(p, "marketplace_listings", None) or {}
            meli_id = listings.get("mercadolibre", "") if isinstance(listings, dict) else ""
            out.append(
                {
                    "id": getattr(p, "id", ""),
                    "name": getattr(p, "name", ""),
                    "sale_price_ars": getattr(p, "sale_price_ars", 0),
                    "sale_price_usd": getattr(p, "sale_price_usd", 0),
                    "authenticity": getattr(p, "authenticity", "unknown"),
                    "niche": niche_for(
                        str(getattr(p, "supplier_id", "") or ""),
                        f"{getattr(p, 'name', '')} {getattr(p, 'category', '')}",
                    ),
                    "image": (getattr(p, "images", None) or [""])[0],
                    "meli_url": f"https://articulo.mercadolibre.com.ar/{meli_id}" if meli_id else "",
                }
            )
        except Exception:
            continue
    return out


def build_storefront_file(
    engine: Any,
    path: Path | None = None,
    brand: str = "Droppinglabel",
    wa_number: str = "",
) -> dict[str, Any]:
    """Escribe index.html desplegable en data-dir (para Pages/Netlify)."""
    dest = path or (Path(os.environ.get("OWNEX_DATA_DIR", "data")) / STOREFRONT_FILENAME)
    products = active_products_for_storefront(engine)
    priced = [p for p in products if _price_text(p.get("sale_price_ars"), p.get("sale_price_usd"))]
    page = render_storefront(priced, brand=brand, wa_number=wa_number)
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page, encoding="utf-8")
    except OSError as exc:
        logger.warning("storefront: no se pudo escribir: %s", exc)
        return {"success": False, "error": str(exc), "products": len(priced)}
    return {"success": True, "path": str(dest), "products": len(priced), "active_total": len(products)}
