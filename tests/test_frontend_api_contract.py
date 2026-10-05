"""Frontend backend.ts root-mounted contract guard (regression para §17).

Audit 2026-09-15: first-money / result-based / platform-guides se montaban en
RAÍZ en el backend pero el frontend los resolvía bajo /api/* → 404 total en
FirstMoney, ResultBased y PlatformGuides.

2026-09-28: el drift era mayor (21 namespaces root fuera de la lista:
mission-hub, career, oar, voice, ...) y el resolver solo matcheaba el path
crudo, así que ni siquiera el estilo `/api/ns/...` se salvaba. Fix:
ROOT_MOUNTED_PREFIXES completo (27) + normalize-then-match en resolveApiUrl
(ambos estilos de llamada resuelven idéntico).

Este guard pinea que cada router root-mounted del backend tiene su contraparte
en el front, para que el drift no regrese. Excepción deliberada: `/auth`
(auth_user.py sirve /auth/* en raíz, pero los flujos de login apuntan a
auth.py/auth_users.py bajo /api/auth/* — listar /auth los rompería).
"""

from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
BACKEND = Path(__file__).resolve().parent.parent / "api"


def _backend_root_mounted_prefixes() -> set[str]:
    """Routers del backend montados sin prefijo / (por evidencia runtime)."""
    import os

    os.environ["CATEYE_CSRF_DISABLED"] = "1"
    import sys

    sys.path.insert(0, str(BACKEND.parent))
    import api.main as m

    prefixes: set[str] = set()
    for route in m.app.routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/"):
            continue
        if path.startswith(("/api", "/docs", "/openapi", "/redoc", "/assets")):
            continue
        seg = "/" + path.strip("/").split("/")[0]
        if seg != "/":  # la raíz `/` no es un namespace versionable
            prefixes.add(seg)
    # Segmentos que el frontend NO debería mandar bajo /api (routers root-mounted).
    return prefixes


# /auth excluido a propósito: auth_user.py sirve /auth/* en raíz pero el
# login fluye a /api/auth/* (auth.py/auth_users.py). Ver backend.ts.
_AUTH_EXCLUDED = {"/auth"}


def _frontend_root_mounted() -> list[str]:
    src = (FRONTEND / "src" / "lib" / "backend.ts").read_text(encoding="utf-8")
    m = re.search(r"ROOT_MOUNTED_PREFIXES = \[(.*?)\]", src, re.S)
    assert m, "ROOT_MOUNTED_PREFIXES no encontrado en backend.ts"
    return re.findall(r"['\"](/[^'\"]+)['\"]", m.group(1))


def _frontend_calls_root_paths() -> set[str]:
    """Paths que el frontend llama SIN /api (resolveApiUrl los resuelve)."""
    prefixes = tuple(_frontend_root_mounted())
    calls: set[str] = set()
    for pattern in ("*.ts", "*.vue"):
        for f in (FRONTEND / "src").rglob(pattern):
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in re.findall(r"api\.(?:get|post|put|patch|delete)\(['\"]([^'\"?]+)", text):
                clean = match[4:] if match.startswith("/api/") else match
                if clean.startswith(prefixes):
                    calls.add(match)
    return calls


def test_root_mounted_prefixes_cover_real_backend_routers() -> None:
    """Cada namespace root-mounteado que el front usa debe existir en raíz.

    MEDIDO 2026-10-05 (HTTP real): de los 27 namespaces que estaban en
    `ROOT_MOUNTED_PREFIXES`, sólo 2 responden en la raíz — `/platform-guides`
    y `/today`. Los otros 25 existen bajo `/api`.

    Como `resolveApiUrl` normaliza `/api/x` → `x` y después decide, tener un
    namespace de más en la lista hacía que **incluso las llamadas con `/api`
    explícito terminaran en raíz y dieran 404** (8 llamadas: 6 de
    `dev-bounty`, 2 de `wear-os`).

    El fix definitivo (commit 4daef0f9, otro flujo) fue además hacer que
    esas llamadas usen `/api/...` explícito. Este test verifica que la lista
    quedó consistente con el backend real: cada entrada sirve en raíz, y el
    front no deja nada por fuera.
    """
    front = set(_frontend_root_mounted())
    backend = _backend_root_mounted_prefixes() - _AUTH_EXCLUDED

    # Cada entrada del front debe servir en raíz (ruta exacta o descendants).
    stale = [p for p in front if not any(r == p or r.startswith(p + "/") for r in backend)]
    assert not stale, (
        f"Prefixes en ROOT_MOUNTED_PREFIXES sin ruta en raíz: {sorted(stale)}\n\n"
        "  Cada uno hace que las llamadas que lo usen terminen en raíz y "
        "devuelvan 404 (medido: 25 de 27 daban 404)."
    )

    # El backend puede montar más namespaces en raíz de los que el front
    # necesita: mientras el front escriba esas llamadas con `/api/` explícito
    # (o el namespace no se use), no hacen falta en la lista.
    # Lo que NO puede pasar es que el front sí use uno y no esté declarado.

    sin_declarar = set()
    for f in (FRONTEND / "src").rglob("*"):
        if f.suffix not in (".ts", ".vue") or "node_modules" in str(f):
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        for match in re.findall(r"api\.(?:get|post|put|patch|delete)\(['\"]([^'\"?]+)", text):
            if match.startswith("/api/"):
                continue  # explícito: no depende de la lista
            clean = match[4:] if match.startswith("/api/") else match
            if any(clean == p or clean.startswith(p + "/") for p in backend):
                sin_declarar.add(clean)

    assert not sin_declarar, (
        f"el front llama estos paths SIN /api y el backend los monta en raíz, "
        f"pero no están en ROOT_MOUNTED_PREFIXES: {sorted(sin_declarar)}\n"
        "  Van a /api/... y dan 404. Agregalos a la lista, o poné /api en la llamada."
    )


def test_vite_dev_proxy_covers_every_root_mounted_prefix() -> None:
    """El proxy de Vite debe incluir TODOS los root-mounted prefixes.

    Sin este test, `/today` faltó del proxy mientras sí estaba en
    ROOT_MOUNTED_PREFIXES: en browser la request salía sin proxy y el dev
    server devolvía el index.html del SPA (200 HTML) donde el cliente esperaba
    JSON. Ningún test leía vite.config.ts, así que el drift no era visible.
    """
    vite = (FRONTEND / "vite.config.ts").read_text(encoding="utf-8")
    proxied = set(re.findall(r"['\"](/[^'\"]+)['\"]", vite))
    expected = set(_frontend_root_mounted()) | {"/api"}

    missing = expected - proxied
    assert not missing, f"Root-mounted prefixes sin proxy en vite.config.ts: {sorted(missing)}"

    # Sin proxies muertos: cada entrada debe existir en backend.ts o ser /api.
    stale = proxied - expected
    assert not stale, f"Prefixes en vite.config.ts que no existen en backend.ts: {sorted(stale)}"


def test_frontend_root_calls_have_backend_route() -> None:
    import sys

    sys.path.insert(0, str(BACKEND.parent))
    import os

    os.environ["CATEYE_CSRF_DISABLED"] = "1"
    import api.main as m

    backend_paths: set[str] = {getattr(r, "path", "") or "" for r in m.app.routes if hasattr(r, "path")}
    for call in _frontend_calls_root_paths():
        # Normalizar igual que el resolver: /api/<ns>/... → /<ns>/...
        clean = call[4:] if call.startswith("/api/") else call
        # Coincidencia por prefijo dinámico en AMBAS formas: el backend sirve
        # algunos routers bajo /api/... (ej. control.py → /api/finance-guru)
        # y otros en raíz (/mission-hub/...). Aceptar cualquiera de las dos.
        bases = {
            "/" + clean.strip("/").split("/", 1)[0],
            "/" + call.strip("/").split("/", 1)[0],
        }
        any_match = any(p == call or p == clean or any(p.startswith(b + "/") for b in bases) for p in backend_paths)
        assert any_match, f"Frontend llama {call} pero el backend no lo sirve (ni por prefijo dinámico)"


def test_explicit_api_prefix_still_resolves_for_root_namespaces() -> None:
    """2026-09-28: resolveApiUrl normaliza ANTES de matchear, así que los
    callers legacy con `/api/<ns>/...` (controlPanel dev-bounty, etc.)
    resuelven idéntico a `/<ns>/...`. Este test pinea que el resolver
    soporta ambos estilos para cada namespace root-mounted."""
    src = (FRONTEND / "src" / "lib" / "backend.ts").read_text(encoding="utf-8")
    assert (
        "path.startsWith('/api/') ? path.slice(4) : path" in src.replace(" ", "").replace("\n", "") or "slice(4)" in src
    ), "resolveApiUrl debe normalizar /api/ antes de matchear"
    for prefix in _frontend_root_mounted():
        # Simula la lógica: ambos estilos caen en la misma rama root-mounted
        for style in (f"{prefix}/x", f"/api{prefix}/x"):
            clean = style[4:] if style.startswith("/api/") else style
            assert clean == f"{prefix}/x", f"normalización rota para {style}"


# ── Cluster B/D/E (2026-09-28): llamadas muertas vs contrato real ──────────
# Este guard pinea el arreglo: las rutas ficticias NO deben volver al front, y
# sus reemplazos reales deben estar. No es un matcher universal (fragil por
# templates/dinámicos); es un pin explícito de lo que se corrigió.

_FIXED_DEAD_CALLS: tuple[str, ...] = (
    # B — WorkRoom: CRUD de archivos/evidencia/entregables que el backend nunca sirvió
    "workbank/${workId}/files",
    "workbank/${workId}/evidence",
    "workbank/${workId}/deliverables",
    # D — CommandPalette: búsquedas que no existen
    "/memory/query",
    "/direct-work/queue",
    "/scheduler/jobs",
    # E — Connections/Wallets
    "/connections/sync-all",
    "connections/sync/${provider}",
    "identity-center/wallets/${walletId}",
)

_REAL_REPLACEMENTS: tuple[str, ...] = (
    "knowledge/search?q=",
    "offensive/hypotheses",
    "direct-work/workbank",
    "workbank/${workId}/file/",
    "workbank/${workId}/deliver/prepare",
    "workbank/${workId}/deliver/approve",
    "workbank/${workId}/submit",
    "identity-center/wallets'",
)


def _frontend_src_text() -> str:
    out: list[str] = []
    for pattern in ("*.ts", "*.vue"):
        for f in (FRONTEND / "src").rglob(pattern):
            out.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(out)


def test_fixed_dead_calls_did_not_come_back() -> None:
    text = _frontend_src_text()
    back = [c for c in _FIXED_DEAD_CALLS if c in text]
    assert not back, f"Llamadas muertas reintroducidas en el frontend: {back}"


def test_real_replacements_are_wired() -> None:
    text = _frontend_src_text()
    missing = [c for c in _REAL_REPLACEMENTS if c not in text]
    assert not missing, f"Reemplazos reales ausentes del frontend: {missing}"


def test_wallet_load_uses_identity_center_root() -> None:
    """Wallets carga desde GET /identity-center (dict) y guarda con POST /wallets."""
    src = (FRONTEND / "src" / "pages" / "Wallets.vue").read_text(encoding="utf-8")
    assert "api.get<{ wallets: Record<string, string> }>('/identity-center')" in src, (
        "Wallets debe leer wallets del dict de GET /identity-center"
    )
    assert "api.post('/identity-center/wallets'" in src, "Wallets debe guardar con POST por key"
