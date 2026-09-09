"""Tax AR — Monotributo, Factura E, Ganancias, Anticipos, CSV para contador.

Argentina: exportación de servicios (bounty/freelance/cripto) = Factura E
(exenta de IVA). Monotributo: recategorización semestral, pago mensual.
Ganancias: deducción gastos (equipo, internet, cursos, seguro, contador).

Persistencia: ~/.config/ownex/tax_ar/state.json
"""

from __future__ import annotations

import csv
import json
import logging
import os
from datetime import date
from typing import Any

logger = logging.getLogger("core.tax_ar")

# Tablas 2024/2025 (actualizar anualmente)
MONOTRIBUTO_CATEGORIAS = [
    {"cat": "A", "ingresos_anuales": 6450000, "cuota_mensual": 10570.33, "iva": 0, "ganancias": 0},
    {"cat": "B", "ingresos_anuales": 9675000, "cuota_mensual": 16097.53, "iva": 0, "ganancias": 0},
    {"cat": "C", "ingresos_anuales": 13600000, "cuota_mensual": 22614.70, "iva": 0, "ganancias": 0},
    {"cat": "D", "ingresos_anuales": 17950000, "cuota_mensual": 30879.45, "iva": 0, "ganancias": 0},
    {"cat": "E", "ingresos_anuales": 22600000, "cuota_mensual": 39932.70, "iva": 0, "ganancias": 0},
    {"cat": "F", "ingresos_anuales": 28500000, "cuota_mensual": 51877.25, "iva": 0, "ganancias": 0},
    {"cat": "G", "ingresos_anuales": 36000000, "cuota_mensual": 67817.55, "iva": 0, "ganancias": 0},
    {"cat": "H", "ingresos_anuales": 48000000, "cuota_mensual": 94623.90, "iva": 0, "ganancias": 0},
    {"cat": "I", "ingresos_anuales": 60000000, "cuota_mensual": 123223.45, "iva": 0, "ganancias": 0},
    {"cat": "J", "ingresos_anuales": 72000000, "cuota_mensual": 155407.35, "iva": 0, "ganancias": 0},
    {"cat": "K", "ingresos_anuales": 84000000, "cuota_mensual": 190595.60, "iva": 0, "ganancias": 0},
]

GASTOS_DEDUCIBLES_POR_DEFECTO = {
    "equipo": 0.05,  # % ingresos anuales (laptop, celular, monitores)
    "internet": 0.02,  # conexión + hosting
    "capacitacion": 0.03,  # cursos, certificaciones, conferencias
    "seguro": 0.01,  # seguro equipo, responsabilidad civil
    "contador": 0.02,  # honorarios contables
    "oficina": 0.03,  # coworking, alquiler parcial, servicios
    "software": 0.015,  # licencias, SaaS, cloud
    "viajes": 0.02,  # conferencias, meetups
}

_DEFAULT_STATE = {
    "cuil": "",
    "categoria_actual": "",
    "ingresos_anuales_usd": 0.0,
    "gastos_deducibles": {},
    "facturas_emitidas": [],
    "pagos_monotributo": [],
    "anticipos_ganancias": [],
    "ultima_recategorizacion": None,
}


class TaxAR:
    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir or os.path.expanduser("~/.config/ownex/tax_ar/")
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def state_path(self) -> str:
        return os.path.join(self.data_dir, "state.json")

    def _load(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as f:
                s = json.load(f)
                for k, v in _DEFAULT_STATE.items():
                    s.setdefault(k, v)
                return s
        except Exception:
            return dict(_DEFAULT_STATE)

    def _save(self, s: dict[str, Any]) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)

    def set_cuil(self, cuil: str) -> dict[str, Any]:
        cuil = cuil.replace("-", "").replace(" ", "")
        if len(cuil) != 11 or not cuil.isdigit():
            return {"success": False, "message": "CUIL inválido (11 dígitos)."}
        s = self._load()
        s["cuil"] = cuil
        self._save(s)
        return {"success": True, "cuil": cuil}

    def set_categoria(self, cat: str) -> dict[str, Any]:
        cat = cat.upper()
        if not any(c["cat"] == cat for c in MONOTRIBUTO_CATEGORIAS):
            return {
                "success": False,
                "message": f"Categoría inválida. Opciones: {[c['cat'] for c in MONOTRIBUTO_CATEGORIAS]}",
            }
        s = self._load()
        s["categoria_actual"] = cat
        self._save(s)
        return {"success": True, "categoria": cat}

    def registrar_ingreso_usd(self, usd: float, fecha: str = "") -> dict[str, Any]:
        s = self._load()
        s["ingresos_anuales_usd"] = float(s.get("ingresos_anuales_usd", 0)) + float(usd)
        self._save(s)
        return {"success": True, "total_usd": s["ingresos_anuales_usd"]}

    def sugerir_categoria(self, usd_anual: float, usd_ars: float = 1000) -> dict[str, Any]:
        ars = usd_anual * usd_ars
        for c in reversed(MONOTRIBUTO_CATEGORIAS):
            if ars <= c["ingresos_anuales"]:
                return {
                    "success": True,
                    "sugerida": c["cat"],
                    "cuota_mensual": c["cuota_mensual"],
                    "margen": c["ingresos_anuales"] - ars,
                }
        return {
            "success": True,
            "sugerida": "K",
            "cuota_mensual": MONOTRIBUTO_CATEGORIAS[-1]["cuota_mensual"],
            "margen": 0,
        }

    def calcular_gastos_deducibles(self, ingresos_usd: float, usd_ars: float = 1000) -> dict[str, Any]:
        ars = ingresos_usd * usd_ars
        gastos = {}
        total = 0
        for k, pct in GASTOS_DEDUCIBLES_POR_DEFECTO.items():
            monto = round(ars * pct, 2)
            gastos[k] = monto
            total += monto
        s = self._load()
        s["gastos_deducibles"] = gastos
        self._save(s)
        return {
            "success": True,
            "gastos": gastos,
            "total_ars": round(total, 2),
            "base_imponible_estimada": round(ars - total, 2),
        }

    def registrar_factura_e(self, cliente: str, usd: float, fecha: str = "", cae: str = "") -> dict[str, Any]:
        s = self._load()
        f = {
            "id": f"FE-{len(s['facturas_emitidas']) + 1:05d}",
            "cliente": cliente,
            "usd": float(usd),
            "fecha": fecha or date.today().isoformat(),
            "cae": cae,
            "tipo": "E",
        }
        s["facturas_emitidas"].append(f)
        self._save(s)
        return {"success": True, "factura": f}

    def exportar_csv_contador(self, path: str = "") -> dict[str, Any]:
        s = self._load()
        out = path or os.path.join(self.data_dir, f"tax_contador_{date.today().isoformat()}.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["tipo", "fecha", "concepto", "monto_ars", "monto_usd", "detalle"])
            for fac in s.get("facturas_emitidas", []):
                w.writerow(["Factura E", fac["fecha"], fac["cliente"], "", fac["usd"], f"CAE: {fac.get('cae', '')}"])
            for g in s.get("gastos_deducibles", {}).items():
                w.writerow(["Gasto deducible", date.today().isoformat(), g[0], g[1], "", "Deducible Ganancias"])
        return {
            "success": True,
            "path": out,
            "rows": len(s.get("facturas_emitidas", [])) + len(s.get("gastos_deducibles", {})),
        }

    def get_status(self) -> dict[str, Any]:
        s = self._load()
        cat_info = next((c for c in MONOTRIBUTO_CATEGORIAS if c["cat"] == s.get("categoria_actual", "")), {})
        return {
            "success": True,
            "cuil": s.get("cuil", ""),
            "categoria": s.get("categoria_actual", ""),
            "cuota_mensual": cat_info.get("cuota_mensual", 0),
            "ingresos_usd": s.get("ingresos_anuales_usd", 0),
            "facturas": len(s.get("facturas_emitidas", [])),
            "gastos_deducibles": s.get("gastos_deducibles", {}),
            "proxima_recategorizacion": self._proxima_recat(),
        }

    def _proxima_recat(self) -> str:
        hoy = date.today()
        if hoy.month <= 7:
            return f"{hoy.year}-07-20"
        return f"{hoy.year + 1}-01-20"


_tax: TaxAR | None = None


def get_tax_ar() -> TaxAR:
    global _tax
    if _tax is None:
        _tax = TaxAR()
    return _tax
