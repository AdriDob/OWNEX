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
    python scripts/audit_frontend_contract.py --live     # además: ejecuta los GET

## `--live`: existencia no es vida

Por defecto este script compara **paths declarados** contra **paths que el
front llama**. Eso prueba que la ruta existe, no que responda.

Medido 2026-10-08: el audit daba "380 de 380 con backend" mientras
`GET /api/assistant/insights` y `/api/assistant/insights/top` devolvían
**500** (`TypeError: can't compare offset-naive and offset-aware datetimes`).
Dos rutas que existen, que el front llama, y que revientan.

`--live` autentica un usuario de prueba y **ejecuta** cada GET, informando
los 5xx. Sin autenticar no serviría: esos endpoints devuelven 401 antes de
llegar al código que falla, así que un chequeo anónimo no ve el 500.

⚠️ `--live` pega contra los endpoints de verdad, con la DB real: es lento
(cientos de requests) y **un GET con efectos secundarios sería ejecutado**.
Por eso es opt-in y tiene `--limit` para muestrear.
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


def wait_for_background_init(timeout_s: float = 180.0) -> None:
    """Espera a que termine `run_background_init` antes de pegar los GET.

    Sin esto, `--live` reporta falsos positivos. Medido 2026-10-08: la primera
    corrida dio **29 endpoints en 500**, de los cuales 3 eran odyssey — y no
    estaban rotos. El API sirve requests *antes* de que el background init
    registre las DBs de los app plugins (`get_db_manager().list_databases()`
    vacío ⇒ `get_session("odyssey")` levanta ⇒ 500). Con la DB real y ya
    registrada, los tres devuelven 200.

    Es decir: el modo `--live` necesita el estado *post-boot*, no el que hay
    200 ms después de arrancar. Y el bug de odyssey no era el que yo estaba
    buscando.

    Las tareas están en `api.lifespan._background_tasks`; se las consulta
    desde código sync con `task.done()`.
    """
    import time

    try:
        from api.lifespan import _background_tasks
    except Exception:  # pragma: no cover
        return

    t0 = time.monotonic()
    announced = False
    while time.monotonic() - t0 < timeout_s:
        pendientes = [t for t in list(_background_tasks) if not t.done()]
        if not pendientes:
            break
        if not announced:
            print(
                f"[--live] esperando {len(pendientes)} tarea(s) de background init…",
                file=sys.stderr,
            )
            announced = True
        time.sleep(0.5)
    else:
        print(
            f"[--live] el background init no terminó en {timeout_s:.0f}s; "
            "los 5xx pueden ser falsos positivos por booting",
            file=sys.stderr,
        )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="detalle con archivo:línea")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument(
        "--live",
        action="store_true",
        help="además de comparar paths, ejecuta cada GET y reporta los 5xx",
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        help="con --live, ejecutar como máximo N GETs (0 = todos). Muestrea.",
    )
    args = ap.parse_args()

    import logging

    logging.disable(logging.CRITICAL)  # el BOOT log ensucia stdout

    from fastapi.testclient import TestClient

    from api.main import app

    # norm() en ambos lados: `/api/knowledge/` y `/api/knowledge` son el mismo
    # endpoint. Comparar exacto daba 404 falso.
    real = {norm(r.path) for r in app.routes if getattr(r, "path", None)}
    prefixes = root_prefixes()
    # `with` para que corra el lifespan: sin él, las DBs de los app plugins no
    # se registran y todo endpoint que las use da 500 — un falso positivo que
    # haría creer que están rotos cuando lo que falta es el arranque.
    client = TestClient(app)
    if args.live:
        client.__enter__()
        wait_for_background_init()

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

    # ── Verificación VIVA: una ruta declarada puede reventar ──
    # El chequeo anterior ya pega un GET por ruta, pero sin autenticar: un
    # endpoint protegido devuelve 401 antes de llegar al código que falla, así
    # que un 500 real queda invisible. Por eso --live autentica y re-pega.
    cinco_xx: list[tuple[str, str, Path, int, int]] = []
    if args.live:
        probe = "audit_contract_probe"
        login = client.post("/api/auth/login", json={"username": probe, "password": "probe-12345"})
        if login.status_code != 200:
            login = client.post("/api/auth/register", json={"username": probe, "password": "probe-12345"})
        token = (login.json().get("data") or {}).get("token")
        if not token:
            print("✗ no se pudo autenticar: --live no puede distinguir 401 de 500", file=sys.stderr)
            return 4
        headers = {
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": client.cookies.get("csrf-token", ""),
        }
        gets = [(m, r, f, ln) for (m, r), (f, ln) in sorted(calls.items(), key=lambda kv: str(kv[1])) if m == "GET"]
        if args.limit:
            gets = gets[: args.limit]
        print(f"\n--live: ejecutando {len(gets)} GET autenticados...", file=sys.stderr)
        for method, resolved, f, ln in gets:
            try:
                code = client.get(resolved, headers=headers).status_code
            except Exception as exc:  # noqa: BLE001 — un crash es el hallazgo
                cinco_xx.append((method, resolved, f, ln, 0))
                print(f"  EXC {resolved}: {exc}"[:160], file=sys.stderr)
                continue
            if code >= 500:
                cinco_xx.append((method, resolved, f, ln, code))

    vivas = len(calls) - len(rotas)
    if args.json:
        print(
            json.dumps(
                {
                    "llamadas": len(calls),
                    "templates": templates,
                    "con_backend": vivas,
                    "sin_backend": len(rotas),
                    "cinco_xx": [
                        {"method": m, "path": r, "file": str(f.relative_to(REPO)), "line": ln, "code": c}
                        for m, r, f, ln, c in cinco_xx
                    ],
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
        return 1 if (rotas or prefixes_malos or cinco_xx) else 0

    print(f"endpoints distintos que el front llama : {len(calls)}")
    print(f"  con backend                          : {vivas}")
    print(f"  SIN backend                         : {len(rotas)}")
    print(f"  (llamadas con template literal       : {templates})")
    if args.live:
        print(f"  5xx al ejecutarlas                    : {len(cinco_xx)}")
        if cinco_xx and args.list:
            print("\n=== 5xx REALES: la ruta existe pero reventa ===\n")
            for m, r, f, ln, code in cinco_xx:
                etiqueta = f"GET->{code}" if code else "GET->EXCEPTION"
                print(f"  {m:6} {r:46} [{etiqueta}]")
                print(f"         {f.relative_to(REPO)}:{ln}")
        elif cinco_xx:
            print("  usar --list para el detalle con archivo:línea")
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
    return 1 if (rotas or prefixes_malos or cinco_xx) else 0


if __name__ == "__main__":
    raise SystemExit(main())
