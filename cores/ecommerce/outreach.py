"""Supplier Outreach — mensaje listo + tracking $0.

Minimal human reasoning: OWNEX genera el mensaje por categoría/proveedor,
abre WhatsApp con 1 click, y trackea 🟢/🟡/🔴 sin planilla manual.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

OUTREACH_TEMPLATES: dict[str, str] = {
    "urban": (
        "Hola {name}! Soy Adriel — vendemos ropa urbana en MercadoLibre (tráfico orgánico, sin redes). "
        "Buscamos proveedores por comisión/dropshipping: ustedes mantienen stock y despachan 24-72h con tracking, "
        "nosotros traemos las ventas. ¿Trabajan por comisión % o margen reventa? ¿Stock verificable (Sheet/API/Drive)? "
        "¿Envío directo al cliente con paquete neutro? ¿Devoluciones/cambios? Tenemos catálogo Meli listo — si nos pasás ficha + fotos + tabla talles, publicamos hoy. ¡Gracias!"
    ),
    "futbol": (
        "Hola {name}! Soy Adriel — vendemos camisetas de fútbol importadas en MercadoLibre (orgánico Meli). "
        "Buscamos proveedor por comisión/dropshipping: ustedes guardan stock y despachan 24-48h con tracking (Andreani/OCA), "
        "nosotros vendemos. ¿Comisión % sobre venta? ¿Stock diario verificable? ¿Paquete neutro? ¿Réplica AAA o sublimada? "
        "Tenemos 100 proveedores en evaluación — priorizamos al que responde con datos + fotos pro. ¿Me pasás catálogo + precios?"
    ),
    "relojes": (
        "Hola {name}! Soy Adriel — vendemos relojes en MercadoLibre (orgánico, sin redes, sin talles = margen alto). "
        "Buscamos proveedor por comisión/dropshipping: ustedes despachan 24-48h con tracking y garantía, nosotros traemos ventas. "
        "¿Comisión %? ¿Stock verificable? ¿Acero inox / smart? ¿Devoluciones? Si me pasás catálogo con fotos + precio costo, "
        "armamos publicación hoy. ¡Gracias!"
    ),
    "perfumes": (
        "Hola {name}! Soy Adriel — vendemos perfumes/decants nicho en MercadoLibre (sin talles, margen rey, repetición). "
        "Buscamos proveedor por comisión/dropshipping: ustedes despachan con lote/garantía y tracking 24-48h, nosotros vendemos. "
        "¿Comisión % o margen? ¿Stock/lote verificable? ¿Decants 5/10ml o frasco sellado? ¿Devoluciones? Con catálogo + fotos, publicamos hoy."
    ),
    "accesorios": (
        "Hola {name}! Soy Adriel — vendemos accesorios (gorras, acero, lentes, mochilas) en MercadoLibre — complemento para subir ticket. "
        "Buscamos proveedor por comisión/dropshipping: ustedes mantienen stock y despachan 24-72h con tracking, nosotros vendemos. "
        "¿Comisión %? ¿Stock verificable? ¿Paquete neutro? ¿Cambios? Si me pasás fotos + precio, lo subimos hoy. ¡Gracias!"
    ),
    "generic": (
        "Hola {name}! Soy Adriel — vendemos en MercadoLibre (tráfico orgánico). Buscamos proveedores por comisión/dropshipping: "
        "ustedes mantienen stock y despachan 24-72h con tracking, nosotros traemos las ventas. ¿Comisión %? ¿Stock verificable? "
        "¿Envío directo con paquete neutro? ¿Devoluciones? Con catálogo + fotos, publicamos hoy. ¡Gracias!"
    ),
}


# ── Variante Instagram ($0, orgánico, sin pauta) ──
# Mismo contrato que OUTREACH_TEMPLATES pero encuadrado en venta por IG:
# el proveedor mantiene stock y despacha, nosotros publicamos y cerramos
# por WhatsApp. Descripción honesta siempre (réplica = réplica, decant = decant).
OUTREACH_TEMPLATES_IG: dict[str, str] = {
    "urban": (
        "Hola {name}! Soy Adriel — vendemos ropa urbana en Instagram (contenido orgánico, cierre por WhatsApp, sin local ni stock). "
        "Buscamos proveedores por comisión: ustedes mantienen stock y despachan 24-72h con tracking y paquete neutro, "
        "nosotros publicamos y traemos las ventas. ¿Comisión % o margen reventa? ¿Stock verificable (Sheet/Drive)? "
        "¿Tabla de talles + fotos pro para publicar? Si me pasás ficha + precios, salimos esta semana. ¡Gracias!"
    ),
    "futbol": (
        "Hola {name}! Soy Adriel — vendemos camisetas de fútbol importadas en Instagram (alta calidad, réplica AAA/sublimada, "
        "siempre descrita tal cual, cierre por WhatsApp). Buscamos proveedor por comisión: ustedes guardan stock y despachan "
        "24-48h con tracking (Andreani/OCA), nosotros vendemos. ¿Comisión %? ¿Stock diario verificable? ¿Paquete neutro? "
        "¿Tabla de talles + fotos reales de la prenda? Priorizamos al que responde con datos + fotos. ¿Me pasás catálogo + precios?"
    ),
    "relojes": (
        "Hola {name}! Soy Adriel — vendemos relojes en Instagram (ticket alto, sin talles, cierre por WhatsApp). "
        "Buscamos proveedor por comisión: ustedes despachan 24-48h con tracking, garantía y paquete cuidado, nosotros publicamos. "
        "¿Comisión %? ¿Stock verificable? ¿Acero/smart/analógico? ¿Garantía y devoluciones? Con catálogo + fotos detalle + precio costo, "
        "armamos las publicaciones esta semana. ¡Gracias!"
    ),
    "perfumes": (
        "Hola {name}! Soy Adriel — vendemos perfumes árabes y nicho en Instagram (decants 5/10ml de originales + frascos sellados, "
        "siempre con lote y originalidad verificable, cierre por WhatsApp). Buscamos proveedor por comisión: ustedes despachan "
        "24-48h con tracking, nosotros vendemos. ¿Comisión % o margen? ¿Stock/lote verificable? ¿Decants o sellado? ¿Devoluciones? "
        "Con catálogo + fotos, publicamos esta semana."
    ),
    "accesorios": (
        "Hola {name}! Soy Adriel — vendemos accesorios en Instagram (acero, gorras, lentes — suben el ticket, cierre por WhatsApp). "
        "Buscamos proveedor por comisión: ustedes mantienen stock y despachan 24-72h con tracking y paquete neutro, nosotros publicamos. "
        "¿Comisión %? ¿Stock verificable? ¿Cambios? Si me pasás fotos + precio, lo subimos esta semana. ¡Gracias!"
    ),
    "generic": (
        "Hola {name}! Soy Adriel — vendemos en Instagram (orgánico, cierre por WhatsApp, sin stock propio). "
        "Buscamos proveedores por comisión: ustedes mantienen stock y despachan 24-72h con tracking y paquete neutro, "
        "nosotros publicamos y traemos las ventas. ¿Comisión %? ¿Stock verificable? ¿Devoluciones? Con catálogo + fotos, "
        "publicamos esta semana. ¡Gracias!"
    ),
}

CANALES_VALIDOS = ("meli", "ig")


# ── Propuesta de reventa (pitch a tiendas existentes) ──
# No pide comisión de entrada ni stock: ofrece clientes + vidriera a cambio de
# unitario + despacho a nombre Droppinglabel. Se envía a CUALQUIER proveedor
# (con o sin programa de reventa); el flag reseller_program solo ordena.
RESELLER_PITCH_NICHO = {
    "futbol": "camisetas de fútbol",
    "perfumes": "perfumes árabes",
    "relojes": "relojes y accesorios",
    "urban": "ropa urbana",
    "accesorios": "accesorios",
    "generic": "tus productos",
}

RESELLER_PITCH_TEMPLATE = (
    "Hola {name}! Soy Adriel, de Droppinglabel (tienda en Instagram de {nicho}). "
    "Te propongo algo simple: revendo tu catálogo en mi Instagram — yo publico tus productos, "
    "traigo los clientes y cierro por WhatsApp; ustedes solo preparan y despachan a mi cliente "
    "a nombre de Droppinglabel. Ustedes ganan ventas extra sin moverse: sin costo fijo, solo pagan "
    "comisión sobre lo que se vende. ¿Trabajan con revendedores por comisión o precio mayorista unitario? "
    "¿Despachan a nombre de mi tienda (paquete neutro)? Si me pasan catálogo + precios + fotos, "
    "arrancamos esta semana. ¡Gracias!"
)


def build_reseller_pitch(supplier_id: str, supplier_name: str) -> dict[str, str]:
    """Propuesta de reventa lista para enviar (corta, por WhatsApp)."""
    niche = niche_for(supplier_id, supplier_name)
    body = RESELLER_PITCH_TEMPLATE.format(name=supplier_name, nicho=RESELLER_PITCH_NICHO.get(niche, "tus productos"))
    return {"niche": niche, "body": body, "wa_url": f"https://wa.me/?text={quote(body)}"}


def niche_for(supplier_id: str, supplier_name: str) -> str:
    sid = (supplier_id or "").lower()
    name = (supplier_name or "").lower()
    blob = f"{sid} {name}"
    if "urban" in blob or "street" in blob or "moha" in blob or "47 street" in name.lower():
        return "urban"
    if "fut" in blob or "sport" in blob or "gol" in blob or "sur sport" in blob:
        return "futbol"
    if "camiseta" in blob or "tribuna" in blob or "hincha" in blob or "bocha" in blob or "mundial" in blob:
        return "futbol"
    if "watch" in blob or "reloj" in blob or "time" in blob or "cronos" in blob or "horus" in blob or "tempo" in blob:
        return "relojes"
    if "perf" in blob or "aroma" in blob or "decant" in blob or "scent" in blob or "viales" in blob:
        return "perfumes"
    if "arab" in blob or "oud" in blob or "lattafa" in blob or "musk" in blob or "attar" in blob:
        return "perfumes"
    if (
        "acc" in blob
        or "gorra" in blob
        or "acero" in blob
        or "lentes" in blob
        or "bolso" in blob
        or "mochila" in blob
        or "cap" in blob
        or "steel" in blob
    ):
        return "accesorios"
    return "generic"


def build_message(supplier_id: str, supplier_name: str, canal: str = "meli") -> dict[str, str]:
    """Mensaje listo por categoría y canal (``meli`` o ``ig``). Default meli = contrato histórico."""
    key = niche_for(supplier_id, supplier_name)
    table = OUTREACH_TEMPLATES_IG if str(canal or "meli").lower() == "ig" else OUTREACH_TEMPLATES
    tmpl = table.get(key, table["generic"])
    body = tmpl.format(name=supplier_name)
    # Wa link: use phone if known, else generic (user fills)
    wa_text = quote(body)
    wa_url = f"https://wa.me/?text={wa_text}"
    return {
        "category_key": key,
        "canal": str(canal or "meli").lower(),
        "body": body,
        "wa_url": wa_url,
        "char_count": str(len(body)),
    }


def outreach_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "ecommerce_outreach.json"


def next_step_for_status(status: str) -> str:
    """Siguiente paso accionable por estado de outreach (nunca genérico)."""
    s = (status or "pending").lower()
    if s == "pending":
        return "Contactar por WhatsApp (1 click) → se marca contacted solo"
    if s == "contacted":
        return "Esperar 48h → si responde pedir ficha+precios (marcar replied), si no re-contactar"
    if s == "replied":
        return "Validar ficha (precio/stock/talles/envío) → sync-catalog → DRAFT"
    if s == "verified":
        return "sync-catalog → DRAFT → precio VIABLE (≥25%) → publicar (Meli/IG)"
    if s == "rejected":
        return "Descartado — no contactar, pasar al siguiente proveedor"
    return "Contactar por WhatsApp (1 click)"


@dataclass(slots=True)
class OutreachRecord:
    supplier_id: str
    status: str = "pending"  # pending | contacted | replied | verified | rejected
    last_contact_at: str | None = None
    wa_url: str = ""
    message: str = ""
    notes: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "supplier_id": self.supplier_id,
            "status": self.status,
            "next_step": next_step_for_status(self.status),
            "last_contact_at": self.last_contact_at,
            "wa_url": self.wa_url,
            "message": self.message[:300],
            "notes": self.notes,
            "history": self.history[-5:],
        }


class OutreachStore:
    def __init__(self, path: Path | None = None):
        self.path = path or outreach_store_path()
        self._data: dict[str, OutreachRecord] = {}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            for rid, rec in raw.items():
                if not isinstance(rec, dict):
                    continue
                # next_step es derivado (no campo del dataclass): ignorarlo al recargar.
                rec.pop("next_step", None)
                try:
                    self._data[rid] = OutreachRecord(**rec)
                except TypeError:
                    continue
        except Exception:
            pass

    def _save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {k: v.to_dict() | {"message": v.message} for k, v in self._data.items()},
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def get(self, supplier_id: str) -> OutreachRecord | None:
        return self._data.get(supplier_id)

    def mark_contacted(self, supplier_id: str, wa_url: str, message: str, notes: str = "") -> OutreachRecord:
        rec = self._data.get(supplier_id) or OutreachRecord(supplier_id=supplier_id)
        rec.status = "contacted"
        rec.last_contact_at = datetime.now(UTC).isoformat()
        rec.wa_url = wa_url
        rec.message = message
        if notes:
            rec.notes = notes
        rec.history.append({"at": rec.last_contact_at, "action": "contacted", "wa_url": wa_url})
        self._data[supplier_id] = rec
        self._save()
        return rec

    def mark(self, supplier_id: str, status: str, notes: str = "") -> OutreachRecord | None:
        rec = self._data.get(supplier_id)
        if not rec:
            return None
        rec.status = status
        if notes:
            rec.notes = notes
        rec.history.append({"at": datetime.now(UTC).isoformat(), "action": status, "notes": notes})
        self._save()
        return rec

    def list_all(self) -> dict[str, OutreachRecord]:
        return dict(self._data)

    def summary(self) -> dict[str, Any]:
        total = len(self._data)
        by_status: dict[str, int] = {}
        for r in self._data.values():
            by_status[r.status] = by_status.get(r.status, 0) + 1
        return {"total": total, "by_status": by_status, "path": str(self.path)}


_store: OutreachStore | None = None


def get_outreach_store() -> OutreachStore:
    global _store
    if _store is None:
        _store = OutreachStore()
    return _store
