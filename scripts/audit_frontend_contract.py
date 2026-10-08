#!/usr/bin/env python3
"""Auditoría del contrato frontend↔backend: ¿el front llama a endpoints que existen?

Por qué existe (2026-10-05). Se repite el mismo modo de fallo de #61 (Jupiter) y
#62 (SpoofCheck): **una dependencia que se rompe devuelve su valor por defecto**.
Acá el síntoma es un 404 que la UI traga con `.catch(() => ({}))` y muestra una
pantalla vacía sin avisar.

Medido con el resolver REAL del front (`frontend/src/lib/backend.ts`):

    endpoints distintos que el front llama : 402
    con backend                          : ~365
    SIN backend (404 real)               : ~30

⚠️ **Este script NO es un test.** Un test que siempre falla entrena a ignorarlo,
y uno que se desactiva solo no vigila nada. La decisión de qué hacer con cada 404
(¿se restaura el endpoint o se borra la llamada?) es del owner; este script es la
evidencia para tomarla.

Uso:
    python scripts/audit_frontend_contract.py            # resumen
    python scripts/audit_frontend_contract.py --list     # detalle con archivo:línea
    python scripts/audit_frontend_contract.py --json     # parseable
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("CATEYE_CSRF_DISABLED", "1")

REPO = Path(__file__).resolve().parent.parent
FRONTEND = REPO / "frontend" / "src"

CALL = re.compile(r"""api\.(get|post|put|patch|delete)(?:<[^>]*>)?\(\s*[`'"]([^`'"]+)""")


def root_prefixes() -> set[str]:
    """Los namespaces que el front resuelve SIN /api."""
    ts = (FRONTEND / "lib" / "backend.ts").read_text(encoding="utf-8")
    block = ts.split("ROOT_MOUNTED_PREFIXES = [", 1)[1].split("]", 1)[0]
    return set(re.findall(r"'([^']+)'", block))


def resolve(path: str, prefixes: set[str]) -> str:
    """Réplica de `resolveApiUrl` en backend.ts."""
    clean = path[4:] if path.startswith("/api/") else path
    clean = clean.split("?")[0].rstrip("/") or "/"
    is_root = any(clean == p or clean.startswith(p + "/") for p in prefixes)
    return clean if is_root else f"/api{clean}"


def norm(path: str) -> str:
    """Normaliza para COMPARAR: sin barra final.

    `/api/knowledge/` y `/api/knowledge` son el MISMO endpoint. FastAPI
    responde ambos (307 en uno). Comparar exactamente daba 404 falso: el
    router declara la ruta CON barra y el front pide SIN ella.
    """
    return path.split("?")[0].rstrip("/") or "/"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="detalle con archivo:línea")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args()

    import logging

    logging.disable(logging.CRITICAL)  # el BOOT log ensucia stdout

    from fastapi.testclient import TestClient

    from api.main import app

    # norm() en ambos lados: `/api/knowledge/` y `/api/knowledge` son el mismo
    # endpoint. Comparar exacto daba 404 falso.
    real = {norm(r.path) for r in app.routes if getattr(r, "path", None)}
    prefixes = root_prefixes()
    client = TestClient(app)

    calls: dict[tuple[str, str], tuple[Path, int]] = {}
    templates = 0
    template_prefixes: dict[tuple[str, str], tuple[Path, int]] = {}
    for f in FRONTEND.rglob("*"):
        if f.suffix not in (".ts", ".vue") or "node_modules" in str(f):
            continue
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in CALL.finditer(line):
                method, path = m.group(1).upper(), m.group(2)
                if "${" in path:
                    templates += 1
                    # Guardar el prefijo hasta el primer ${ para verificarlo:
                    # antes se contaban y se ignoraban a ciegas (punto ciego).
                    # Aplicar resolve() ANTES de guardar: el prefijo crudo
                    # `/applications` se resuelve a `/api/applications`, y
                    # comparar el crudo daba 61 falsos positivos.
                    pre = resolve(path.split("${")[0], prefixes)
                    template_prefixes.setdefault((method, pre), (f, ln))
                    continue
                calls.setdefault((method, resolve(path, prefixes)), (f, ln))

    # Verificar por HTTP real, no por comparación de strings: una ruta puede
    # existir montada bajo un router aunque no esté en el path declarado.
    rotas: list[tuple[str, str, Path, int, str]] = []
    for (method, resolved), (f, ln) in sorted(calls.items()):
        try:
            code = client.get(resolved).status_code if method == "GET" else None
            if code == 404:
                rotas.append((method, resolved, f, ln, "GET->404"))
                continue
        except Exception:  # pragma: no cover
            pass
        r_norm = norm(resolved)
        if r_norm not in real and not (r_norm.startswith("/api/") and r_norm[4:] in real):
            rotas.append((method, resolved, f, ln, "path no declarado"))

    # Verificar también los prefijos de templates literales: que exista al
    # menos una ruta bajo ese prefijo, en raíz o bajo /api. Medido 2026-10-05:
    # 38 templates = 7 prefijos que "no existían" y los 7 sí están bajo /api.
    prefixes_malos: list[tuple[str, str, Path, int]] = []
    for (method, pre), (f, ln) in template_prefixes.items():
        n = norm(pre)
        # Mismo chequeo que `_served`: raíz O bajo /api. Medido 2026-10-05:
        # sin la rama `/api` salían 61 falsos positivos (de 133 templates).
        if any(p == n or p.startswith(n + "/") for p in real):
            continue
        if n.startswith("/api") and any(p == n[4:] or p.startswith(n[4:] + "/") for p in real):
            continue
        prefixes_malos.append((method, pre, f, ln))

    vivas = len(calls) - len(rotas)
    if args.json:
        print(
            json.dumps(
                {
                    "llamadas": len(calls),
                    "templates": templates,
                    "con_backend": vivas,
                    "sin_backend": len(rotas),
                    "template_prefixes_sin_ruta": [
                        {"method": m, "prefix": p, "file": str(f.relative_to(REPO)), "line": ln}
                        for m, p, f, ln in prefixes_malos
                    ],
                    "rotas": [
                        {"method": m, "path": r, "file": str(f.relative_to(REPO)), "line": ln, "why": w}
                        for m, r, f, ln, w in rotas
                    ],
                },
                indent=2,
            )
        )
        return 1 if (rotas or prefixes_malos) else 0

    print(f"endpoints distintos que el front llama : {len(calls)}")
    print(f"  con backend                          : {vivas}")
    print(f"  SIN backend                         : {len(rotas)}")
    print(f"  (llamadas con template literal       : {templates})")
    if prefixes_malos:
        print(f"  de esos, prefijo SIN ruta en el back : {len(prefixes_malos)}\n")
        for m, pre, _f, _ln in prefixes_malos:
            print(f"      {m:6} {pre}")
    print()
    if args.list and rotas:
        print("=== 404 REALES: el front llama, el backend no sirve ===\n")
        for m, r, f, ln, w in rotas:
            print(f"  {m:6} {r:46} [{w}]")
            print(f"         {f.relative_to(REPO)}:{ln}")
    elif not args.list and rotas:
        print("  usar --list para el detalle con archivo:línea")
    return 1 if (rotas or prefixes_malos) else 0


if __name__ == "__main__":
    raise SystemExit(main())
