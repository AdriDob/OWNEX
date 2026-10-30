#!/usr/bin/env python3
"""
Script para validar y cargar proveedores en OWNEX desde CSV.

Uso:
    python supplier_import.py --csv proveedores.csv --dry-run
    python supplier_import.py --csv proveedores.csv --apply

CSV columnas requeridas:
    id,name,type,website,api_endpoint,commission_rate,processing_time_days,is_active,api_credentials

Ejemplo CSV:
id,name,type,website,api_endpoint,commission_rate,processing_time_days,is_active,api_credentials
sup_fut_1,Nebbux,DEV_BOUNTY,https://nebbux.com,,0.25,3,true,"{}"

Uso:
    python supplier_import.py --csv proveedores.csv --dry-run   # Simula
    python supplier_import.py --csv proveedores.csv --apply    # Aplica
"""

import argparse
import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path

# Agregar path del proyecto
sys.path.insert(0, "/home/adriel/projects/Rastro")

from cores.ecommerce.engine import get_ecommerce_engine
from cores.ecommerce.models import Supplier, SupplierType

SUPPLIER_TYPE_MAP = {
    "BUG_BOUNTY": "BUG_BOUNTY",
    "DEV_BOUNTY": "DEV_BOUNTY",
    "SECURITY_RESEARCH": "SECURITY_RESEARCH",
    "OSS_BOUNTIES": "OSS_BOUNTIES",
    "OPEN_SOURCE": "OPEN_SOURCE",
    "SOFTWARE_ENGINEERING": "SOFTWARE_ENGINEERING",
    "BACKEND": "BACKEND",
    "FRONTEND": "FRONTEND",
    "FULL_STACK": "FULL_STACK",
    "DEVOPS": "DEVOPS",
    "CLOUD": "CLOUD",
    "INFRASTRUCTURE": "INFRASTRUCTURE",
    "AI_ENGINEERING": "AI_ENGINEERING",
    "ML_ENGINEERING": "ML_ENGINEERING",
    "LLM_ENGINEERING": "LLM_ENGINEERING",
    "PROMPT_ENGINEERING": "PROMPT_ENGINEERING",
    "BROWSER_AUTOMATION": "BROWSER_AUTOMATION",
    "QA_AUTOMATION": "QA_AUTOMATION",
    "REVERSE_ENGINEERING": "REVERSE_ENGINEERING",
    "MALWARE_ANALYSIS": "MALWARE_ANALYSIS",
    "EMBEDDED": "EMBEDDED",
    "IOT": "IOT",
    "MOBILE_DEVELOPMENT": "MOBILE_DEVELOPMENT",
    "DESKTOP_DEVELOPMENT": "DESKTOP_DEVELOPMENT",
    "API_DEVELOPMENT": "API_DEVELOPMENT",
    "SDK_DEVELOPMENT": "SDK_DEVELOPMENT",
    "BLOCKCHAIN_DEVELOPMENT": "BLOCKCHAIN_DEVELOPMENT",
    "SMART_CONTRACTS": "SMART_CONTRACTS",
    "DATA_ENGINEERING": "DATA_ENGINEERING",
    "WEB_SCRAPING": "WEB_SCRAPING",
    "TECHNICAL_WRITING": "TECHNICAL_WRITING",
    "DOCUMENTATION": "DOCUMENTATION",
    "CODE_REVIEW": "CODE_REVIEW",
    "GAME_DEVELOPMENT": "GAME_DEVELOPMENT",
    "COMPETITIONS": "COMPETITIONS",
    "EMPLOYMENT": "EMPLOYMENT",
    "OPEN_CALL": "OPEN_CALL",
    "ALIEXPRESS": "ALIEXPRESS",
    "LOCAL_AR": "LOCAL_AR",
    "CHINA_WHOLESALE": "CHINA_WHOLESALE",
    "DOMESTIC_DISTRIBUTOR": "DOMESTIC_DISTRIBUTOR",
    "PRINT_ON_DEMAND": "PRINT_ON_DEMAND",
    "OTHER": "OTHER",
    "FREELANCE": "FREELANCE",
    "BOUNTY": "BOUNTY",
    "MICROTASK": "MICROTASK",
    "CHALLENGE": "CHALLENGE",
    "PRIZE": "PRIZE",
    "ROLLING": "ROLLING",
    "PROJECT": "PROJECT",
    "RETAINER": "RETAINER",
}

REQUIRED_FIELDS = ["id", "name", "type"]
OPTIONAL_FIELDS = ["website", "api_endpoint", "commission_rate", "processing_time_days", "is_active", "api_credentials"]


def parse_supplier_type(type_str: str) -> SupplierType:
    """Convierte string a SupplierType enum."""
    lower = type_str.lower()
    for st in SupplierType:
        if st.value == lower:
            return st
    if type_str.upper() in SUPPLIER_TYPE_MAP:
        # Map values are uppercase keys; normalize to lower enum value
        mapped = SUPPLIER_TYPE_MAP[type_str.upper()].lower()
        for st in SupplierType:
            if st.value == mapped:
                return st
    # Default
    return SupplierType.OTHER


def validate_row(row: dict, row_num: int) -> tuple[bool, list[str]]:
    """Valida una fila del CSV. Retorna (es_valido, lista_errores)."""
    errors = []

    for field in REQUIRED_FIELDS:
        if not row.get(field) or not str(row.get(field, "")).strip():
            errors.append(f"Fila {row_num}: campo requerido '{field}' vacío")

    # Validar type
    if row.get("type"):
        try:
            parse_supplier_type(row["type"])
        except Exception:
            errors.append(f"Fila {row_num}: tipo '{row['type']}' inválido")

    # Validar commission_rate
    if row.get("commission_rate"):
        try:
            rate = Decimal(str(row["commission_rate"]))
            if rate < 0 or rate > 1:
                errors.append(f"Fila {row_num}: commission_rate debe ser 0-1 (ej: 0.25 = 25%)")
        except Exception:
            errors.append(f"Fila {row_num}: commission_rate inválido")

    # Validar processing_time_days
    if row.get("processing_time_days"):
        try:
            days = int(row["processing_time_days"])
            if days < 0:
                errors.append(f"Fila {row_num}: processing_time_days debe ser >= 0")
        except Exception:
            errors.append(f"Fila {row_num}: processing_time_days debe ser entero")

    # Validar is_active
    if row.get("is_active"):
        val = str(row["is_active"]).lower()
        if val not in ("true", "false", "1", "0", "yes", "no", "sí", "no"):
            errors.append(f"Fila {row_num}: is_active debe ser true/false")

    # Validar URL si existe
    for field in ["website", "api_endpoint"]:
        if row.get(field):
            url = str(row[field]).strip()
            if url and not (url.startswith("http://") or url.startswith("https://")):
                errors.append(f"Fila {row_num}: {field} debe ser URL válida (http/https)")

    return len(errors) == 0, errors


async def import_suppliers(csv_path: str, dry_run: bool = True) -> dict:
    """Importa proveedores desde CSV a OWNEX."""
    engine = get_ecommerce_engine()
    results = {
        "total": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
    }

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):  # start=2 porque header es fila 1
            # Limpiar valores vacíos
            row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
            row = {k: v for k, v in row.items() if v is not None and v != ""}

            valid, errors = validate_row(row, row_num)
            if not valid:
                results["errors"].append({"row": row_num, "id": row.get("id", "?"), "errors": errors})
                results["skipped"] += 1
                continue

            supplier_id = row["id"].strip()
            supplier_type = parse_supplier_type(row["type"])

            # Verificar si existe
            existing = engine.get_supplier(row["id"].strip())
            supplier_data = {
                "id": supplier_id,
                "name": row["name"].strip(),
                "type": supplier_type,
                "processing_time_days": int(row.get("processing_time_days", 3) or 3),
                "is_active": str(row.get("is_active", "true")).lower() in ("true", "1", "yes", "sí", "si"),
            }

            # Campos opcionales
            if row.get("website"):
                supplier_data["website"] = row["website"].strip()
            if row.get("api_endpoint"):
                supplier_data["api_endpoint"] = row["api_endpoint"].strip()
            if row.get("commission_rate"):
                supplier_data["commission_rate"] = Decimal(str(row["commission_rate"]))
            if row.get("api_credentials"):
                supplier_data["api_credentials"] = row["api_credentials"]

            try:
                existing = engine.get_supplier(supplier_id)
                if existing:
                    if not dry_run:
                        engine.update_supplier(supplier_id, **supplier_data)
                    results["updated"] += 1
                    print(f"  🔄 Actualizado: {supplier_id} ({row['name']})")
                else:
                    if not dry_run:
                        supplier = Supplier(**supplier_data)
                        engine.add_supplier(supplier)
                    results["created"] += 1
                    print(f"  ✅ Creado: {supplier_id} ({row['name']})")

                results["total"] += 1

            except Exception as e:
                results["errors"].append({"row": row_num, "id": supplier_id, "error": str(e)})
                results["skipped"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="Importar proveedores a OWNEX desde CSV")
    parser.add_argument("--csv", required=True, help="Archivo CSV con proveedores")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin guardar")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios reales")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("❌ Debe especificar --dry-run o --apply")
        return 1

    if not Path(args.csv).exists():
        print(f"❌ Archivo no encontrado: {args.csv}")
        return 1

    print(f"{'🔍 DRY-RUN' if args.dry_run else '🚀 APLICANDO'} — Cargando {args.csv}")

    try:
        results = asyncio.run(import_suppliers(args.csv, dry_run=args.dry_run))
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    print("\n=== RESULTADO ===")
    print(f"Total procesados: {results['total']}")
    print(f"  ✅ Creados: {results['created']}")
    print(f"  🔄 Actualizados: {results['updated']}")
    print(f"  ⏭️ Saltados: {results['skipped']}")
    print(f"  ❌ Errores: {len(results['errors'])}")

    if results["errors"]:
        print("\nErrores:")
        for e in results["errors"]:
            print(f"  Fila {e['row']} ({e['id']}): {e['errors']}")

    if args.dry_run:
        print("\n💡 Ejecuta con --apply para aplicar cambios reales")

    return 0 if not results["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
