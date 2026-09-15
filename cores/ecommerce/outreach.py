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


def _category_key(supplier_id: str, supplier_name: str) -> str:
    sid = (supplier_id or "").lower()
    name = (supplier_name or "").lower()
    blob = f"{sid} {name}"
    if "urban" in blob or "street" in blob or "moha" in blob or "47 street" in name.lower():
        return "urban"
    if "fut" in blob or "sport" in blob or "gol" in blob or "sur sport" in blob:
        return "futbol"
    if "watch" in blob or "reloj" in blob or "time" in blob or "cronos" in blob or "horus" in blob or "tempo" in blob:
        return "relojes"
    if "perf" in blob or "aroma" in blob or "decant" in blob or "scent" in blob or "viales" in blob:
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


def build_message(supplier_id: str, supplier_name: str) -> dict[str, str]:
    key = _category_key(supplier_id, supplier_name)
    tmpl = OUTREACH_TEMPLATES.get(key, OUTREACH_TEMPLATES["generic"])
    body = tmpl.format(name=supplier_name)
    # Wa link: use phone if known, else generic (user fills)
    wa_text = quote(body)
    wa_url = f"https://wa.me/?text={wa_text}"
    return {"category_key": key, "body": body, "wa_url": wa_url, "char_count": str(len(body))}


def outreach_store_path() -> Path:
    base = Path(os.environ.get("OWNEX_DATA_DIR", "data"))
    return base / "ecommerce_outreach.json"


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
                self._data[rid] = OutreachRecord(**rec)
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
