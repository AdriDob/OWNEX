#!/usr/bin/env python3
"""Repara los `endpoints.path` corruptos de la tabla de descubrimiento.

Medido 2026-10-08 sobre la tabla completa: **8.937 de 44.597 endpoints (20%)**
tienen un `path` que no es un path — es un path pegado a un blob JSON a medio
serializar:

    //docs.hackerone.com/organizations/report-states.html","tag":"a",
    "attribute":"href","source":"https://..."},"error":"max depth reached"}

El patrón es único (una sola firma, verificado sobre la DB) y el prefijo
recuperado es siempre un path verosímil (69 chars de media), lo que hace la
reparación mecánica. Aun así son 8.937 filas de la tabla principal de
descubrimiento: por eso **el default es dry-run** y hay que pasar `--apply`
explícitamente.

## Por qué importa más de lo que parece

El scoring corre sobre ese string: `unified_score(path, ...)` saca el riesgo
de ahí, y `has_admin` / `has_exports` / `has_graphql` matchean substrings
contra él. Un endpoint de documentación puede marcar "tiene exports" sólo
porque la URL de origen que quedó pegada al path contiene la palabra.

## Uso

    python scripts/repair_corrupted_endpoint_paths.py             # dry-run
    python scripts/repair_corrupted_endpoint_paths.py --apply     # escribe
    python scripts/repair_corrupted_endpoint_paths.py --backup    # copia antes

`--apply` hace siempre un `.bak` con la fecha antes de escribir, así que
`--backup` es redundante y queda sólo por claridad. Para devolver todo:
restaurar el `.bak`.

Guard de seguridad: si una fila queda con `path` vacío tras la limpieza, o si
la proporción de filas a reparar baja del 1% (señal de que cambió el patrón y
la regla ya no aplica), el script **aborta sin escribir**.

Ver KNOWN_DEBT #81.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

#: Frontera de la corrupción: el path sano termina justo antes de esto.
CORRUPTION_BOUNDARY = '","tag":"'

#: Si se corrige menos de esto, el patrón cambió y la regla ya no aplica.
MIN_RATIO = 0.01

DEFAULT_DB = Path("/home/adriel/.ownex/database/catseye.db")


def clean_path(path: str) -> str:
    """La regla de reparación, en una línea y sin efectos secundarios."""
    return path.split(CORRUPTION_BOUNDARY)[0] if CORRUPTION_BOUNDARY in path else path


def find_corrupted(con: sqlite3.Connection) -> list[tuple[int, str, str]]:
    """(id, path_actual, path_limpio) de cada fila a reparar."""
    rows = con.execute("select id, path from endpoints where path is not null").fetchall()
    out: list[tuple[int, str, str]] = []
    for row_id, path in rows:
        if CORRUPTION_BOUNDARY not in path:
            continue
        limpio = clean_path(path)
        if limpio and limpio != path:
            out.append((row_id, path, limpio))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="ruta de catseye.db")
    ap.add_argument("--apply", action="store_true", help="escribe los cambios (default: dry-run)")
    ap.add_argument("--backup", action="store_true", help="copia la DB antes de escribir")
    ap.add_argument("--limit", type=int, default=10, help="cuántos ejemplos imprimir")
    args = ap.parse_args(argv)

    if not args.db.exists():
        print(f"✗ no existe {args.db}", file=sys.stderr)
        return 2

    con = sqlite3.connect(str(args.db))
    try:
        total = con.execute("select count(*) from endpoints where path is not null").fetchone()[0]
        rows = find_corrupted(con)
        if not rows:
            print(f"✓ 0 filas a reparar de {total}. No hay nada que hacer.")
            return 0

        ratio = len(rows) / max(total, 1)
        print(f"endpoints totales      : {total:,}")
        print(f"paths corruptos        : {len(rows):,} ({ratio:.1%})")
        print(f"longitud media del path: {sum(len(r[2]) for r in rows) / len(rows):.0f} chars")
        print()
        for row_id, viejo, nuevo in rows[: args.limit]:
            print(f"  #{row_id}: {nuevo}")
            print(f"     desde: {viejo[:100]}...")
        if len(rows) > args.limit:
            print(f"  … y {len(rows) - args.limit} más")

        if ratio < MIN_RATIO:
            print(
                f"\n✗ ABORTADO: sólo {ratio:.2%} de las filas matchea la firma "
                f"(mínimo {MIN_RATIO:.0%}). El patrón de corrupción cambió y esta "
                "regla ya no aplica. Revisá antes de escribir.",
                file=sys.stderr,
            )
            return 3

        if any(not n.strip() for _, _, n in rows):
            print("\n✗ ABORTADO: alguna fila quedaría con el path vacío.", file=sys.stderr)
            return 3

        if not args.apply:
            print("\n— dry-run: no se escribió nada. Pasá --apply para aplicar.")
            return 0

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        bak = args.db.with_suffix(f".bak-{stamp}")
        shutil.copy2(args.db, bak)
        print(f"\nbackup: {bak}")

        con.executemany(
            "update endpoints set path = ? where id = ?",
            [(nuevo, row_id) for row_id, _, nuevo in rows],
        )
        con.commit()
        restantes = con.execute(
            "select count(*) from endpoints where path like ?", (f"%{CORRUPTION_BOUNDARY}%",)
        ).fetchone()[0]
        print(f"✓ {len(rows):,} filas reparadas. Quedan {restantes} con la firma.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
