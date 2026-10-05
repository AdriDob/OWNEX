"""Kit de diseño IG $0 — Droppinglabel.

Todo local y gratis: Pillow compone el flyer (foto proveedor + precio + CTA
WhatsApp), el brief fija formatos/reglas, y el pack semanal arma 7 días de
contenido desde el catálogo real. Sin ffmpeg, sin cuentas pagas, sin red.

Lo que NO se automatiza (requiere humano o token): publicar en IG
(Graph API con META_ACCESS_TOKEN), Shots bonitos (Canva gratis / bot de
imágenes de ChatGPT), edición de video (CapCut gratis).
"""

from __future__ import annotations

import io
import logging
from typing import Any

logger = logging.getLogger("ownex.ecommerce.design")

# Formatos IG (px). Cover de destacados usa story con zona segura central.
IG_SIZES: dict[str, dict[str, Any]] = {
    "post": {"w": 1080, "h": 1350, "uso": "feed: producto + precio"},
    "story": {"w": 1080, "h": 1920, "uso": "historias: promo, encuesta, stock, testimonio"},
    "square": {"w": 1080, "h": 1080, "uso": "feed alternativo / catálogo WA"},
    "highlight": {"w": 1080, "h": 1920, "uso": "portadas: Catálogo, Precios, Envíos, Opiniones"},
}

FREE_STACK: list[dict[str, str]] = [
    {"herramienta": "Este kit (Pillow)", "para": "flyers con precio+CTA sobre foto del proveedor", "costo": "$0 local"},
    {
        "herramienta": "Canva (plan gratis)",
        "para": "flyers lindos, portadas de destacados, plantillas",
        "costo": "$0 freemium",
    },
    {
        "herramienta": "Bot de imágenes de ChatGPT",
        "para": "fondos/mockups/ideas visuales (pedir permiso de marca)",
        "costo": "$0 con cuenta",
    },
    {"herramienta": "CapCut (gratis)", "para": "reels promo: unboxing, top 3, before/after", "costo": "$0 freemium"},
    {
        "herramienta": "Meta Business Suite",
        "para": "programar posts + historias (automatiza la constancia)",
        "costo": "$0 con cuenta IG",
    },
    {"herramienta": "WhatsApp Business", "para": "catálogo + respuestas rápidas + cierre", "costo": "$0"},
]

NICHE_WEEK = ["perfumes", "relojes", "futbol", "urbana", "perfumes", "accesorios", "relojes"]

# Tag visible por autenticidad (réplica/decant se rotulan tal cual).
AUTH_TAG = {
    "official": "original",
    "licensed": "licencia oficial",
    "replica": "réplica",
    "unknown": "",
}


def _money_text(value: Any, currency: str = "USD") -> str:
    """$ 95.000 (ARS) o USD 59.99. Vacío si no hay precio real."""
    try:
        v = float(value or 0)
    except (TypeError, ValueError, ArithmeticError):
        return ""
    if v <= 0:
        return ""
    if str(currency or "USD").upper() == "ARS":
        return f"$ {v:,.0f}".replace(",", ".")
    return f"USD {round(v, 2)}"


def product_flyer_brief(product: Any, size: str = "post", cta: str = "Pedilo por WhatsApp") -> dict[str, Any]:
    """Arma el copy del flyer desde señales reales del producto (puro, sin red).

    Precio: venta real primero (ARS preferido); si no hay precio, sugiere la
    banda OBJETIVO calculada del costo (marcada como sugerencia, no como precio).
    Tag: desde authenticity. Bloqueadores: los mismos que frenan /optimize.
    """
    from cores.ecommerce.models import publish_blockers
    from cores.ecommerce.pipeline import SourcingEngine

    blockers = publish_blockers(product)
    name = str(getattr(product, "name", "") or "").strip()
    brand = str(getattr(product, "brand", "") or "").strip()
    title = f"{name} {brand}".strip()[:60] or "Producto"
    price_text = _money_text(getattr(product, "sale_price_ars", 0), "ARS") or _money_text(
        getattr(product, "sale_price_usd", 0), getattr(product, "currency", "USD")
    )
    suggested = ""
    try:
        cost = float(getattr(product, "cost_usd", 0) or 0)
    except (TypeError, ValueError, ArithmeticError):
        cost = 0.0
    if cost > 0:
        bands = SourcingEngine().price_bands(cost_usd=cost).get("bands", {})
        objetivo = (bands.get("objetivo") or {}).get("price_usd")
        if objetivo:
            suggested = f"USD {objetivo}"
    try:
        auth = str(getattr(product, "authenticity", "unknown") or "unknown").lower()
    except Exception:
        auth = "unknown"
    return {
        "product_id": str(getattr(product, "id", "")),
        "title": title,
        "price_text": price_text,
        "suggested_price_text": suggested,
        "tag": AUTH_TAG.get(auth, ""),
        "cta": str(cta or "Pedilo por WhatsApp"),
        "size": size if size in IG_SIZES else "post",
        "blockers": blockers,
        "ready": not blockers and bool(price_text),
    }


def design_brief(niche: str = "perfumes") -> dict[str, Any]:
    """Brief de diseño por nicho: formatos, reglas y stack gratis. Puro."""
    n = (niche or "perfumes").lower()
    return {
        "niche": n,
        "formatos": IG_SIZES,
        "reglas": [
            "Fondo oscuro o foto a pantalla completa; precio en blanco grande y un solo acento.",
            "Siempre: foto, precio, CTA 'Pedilo por WhatsApp' y tag de autenticidad (original/réplica/decant).",
            "Tipografía del sistema (este kit) o plantillas Canva; nada de fuentes pagas.",
            "Réplica/decant se rotulan tal cual en el flyer, igual que en la publicación.",
        ],
        "stack_gratis": FREE_STACK,
        "video_sin_editor": "CapCut gratis: foto + zoom lento + texto precio + CTA (15-30s). Sin ffmpeg local.",
    }


def _font(size: int):
    """DejaVu si existe, si no default de Pillow. Nunca raisea por fuente."""
    try:
        from PIL import ImageFont

        for candidate in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "arial.ttf"):
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default()
    except Exception:
        from PIL import ImageFont

        return ImageFont.load_default()


def make_flyer(
    image_bytes: bytes,
    title: str,
    price_text: str,
    cta: str = "Pedilo por WhatsApp",
    size: str = "post",
    brand: str = "DROPPINGLABEL",
    tag: str = "",
) -> dict[str, Any]:
    """Compone un flyer PNG: foto cover + franja marca + banda con título,
    píldora de precio, CTA y tag de autenticidad. Puro local (Pillow).

    Retorna {"success", "png", "w", "h"} o {"success": False, "error"}.
    """
    spec = IG_SIZES.get(size or "post", IG_SIZES["post"])
    w, h = int(spec["w"]), int(spec["h"])
    if not image_bytes:
        return {"success": False, "error": "empty_image"}
    if not str(title or "").strip() or not str(price_text or "").strip():
        return {"success": False, "error": "title_and_price_required"}
    try:
        from PIL import Image, ImageDraw, ImageOps
    except ImportError:
        return {"success": False, "error": "pillow_missing"}
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = ImageOps.fit(img, (w, h))
        draw = ImageDraw.Draw(img, "RGBA")
        pad = int(w * 0.06)
        # Franja superior de marca (casero pero prolijo).
        f_brand = _font(40)
        brand_txt = str(brand or "DROPPINGLABEL").strip()[:24].upper()
        bb = draw.textbbox((0, 0), brand_txt, font=f_brand)
        draw.rounded_rectangle(
            [pad, pad, pad + (bb[2] - bb[0]) + 44, pad + (bb[3] - bb[1]) + 28],
            radius=18,
            fill=(0, 0, 0, 190),
        )
        draw.text((pad + 22, pad + 12), brand_txt, font=f_brand, fill=(255, 255, 255))
        # Banda inferior con contenido medido (nunca se corta el texto).
        f_title, f_price, f_cta, f_tag = _font(60), _font(96), _font(44), _font(36)
        lines = [str(title).strip()[:60], str(price_text).strip()[:32], str(cta).strip()[:48]]
        if tag:
            lines.append(str(tag).strip()[:40])
        fonts = (f_title, f_price, f_cta, f_tag)[: len(lines)]
        heights = [draw.textbbox((0, 0), ln, font=f)[3] for ln, f in zip(lines, fonts, strict=True)]
        band_h = sum(heights) + pad * (len(lines) + 2)
        draw.rectangle([0, h - band_h, w, h], fill=(0, 0, 0, 205))
        y = h - band_h + pad
        draw.text((pad, y), lines[0], font=f_title, fill=(255, 255, 255))
        y += heights[0] + pad
        # Píldora de precio (acento).
        pb = draw.textbbox((0, 0), lines[1], font=f_price)
        draw.rounded_rectangle(
            [pad, y - 10, pad + (pb[2] - pb[0]) + 48, y + heights[1] + 10],
            radius=24,
            fill=(232, 33, 39),
        )
        draw.text((pad + 24, y), lines[1], font=f_price, fill=(255, 255, 255))
        y += heights[1] + pad
        draw.text((pad, y), lines[2], font=f_cta, fill=(0, 213, 255))
        y += heights[2] + pad // 2
        if tag:
            draw.text((pad, y), lines[3], font=f_tag, fill=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return {"success": True, "png": buf.getvalue(), "w": w, "h": h, "size": size}
    except Exception as exc:
        logger.warning("design: flyer falló: %s", exc)
        return {"success": False, "error": f"render_failed: {type(exc).__name__}"}


def weekly_pack(products: list[dict[str, Any]]) -> dict[str, Any]:
    """Arma 7 días de contenido rotando nichos (perfumes→relojes→fútbol→urbana…).

    Entrada: [{id, name, sale_price_usd, niche?}]. Sin productos → plan genérico
    honesto (armar catálogo primero), jamás inventa SKUs.
    """
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    plan: list[dict[str, Any]] = []
    by_niche: dict[str, list[dict[str, Any]]] = {}
    for p in products or []:
        by_niche.setdefault(str(p.get("niche") or "generic"), []).append(p)
    used: set[str] = set()
    for i, day in enumerate(days):
        niche = NICHE_WEEK[i % len(NICHE_WEEK)]
        pick = next((p for p in by_niche.get(niche, []) if p.get("id") not in used), None)
        if pick is None:
            flat = [p for lst in by_niche.values() for p in lst if p.get("id") not in used]
            pick = flat[0] if flat else None
        if pick is None:
            plan.append({"dia": day, "niche": niche, "producto": None, "accion": "contenido de marca/testimonio"})
            continue
        used.add(str(pick.get("id")))
        plan.append(
            {
                "dia": day,
                "niche": niche,
                "producto": {"id": pick.get("id"), "name": pick.get("name"), "precio": pick.get("sale_price_usd")},
                "accion": "post feed + 2 historias (flyer kit o Canva + CTA WhatsApp)",
            }
        )
    return {"days": plan, "con_productos": len(used), "sin_productos": len(plan) - len(used)}
