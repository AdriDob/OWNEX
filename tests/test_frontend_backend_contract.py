"""Guard de contrato frontend↔backend con allowlist que se autoverifica.

Por qué existe (2026-10-05). Auditoría de las 624 llamadas `api.*` del
frontend contra las 1734 rutas del backend, usando **el resolver real del
front** (`frontend/src/lib/backend.ts::resolveApiUrl`):

    endpoints distintos que el front llama : 402
    con backend                          : 363
    SIN backend                         :  39   ← 404 garantizado

Los 39 caen en pantallas que el owner ve: `DashboardAegis`, `SettingsAtlas`,
`ModeManagerPanel`, `CopilotConsolidated`, `ProfileConsolidated`,
`QuickCapture`, `SecurityConsolidated`.

Es la misma clase que #61 (Jupiter: la API migró y devolvía su valor por
defecto) y #62 (SpoofCheck: host muerto, `None` en silencio). La diferencia es
que acá el síntoma es visible — un 404 — y el problema es que la UI lo traga
con `.catch(() => ({}))` y muestra una pantalla vacía sin avisar.

## Las dos trampas de este guard (las caí las dos al escribirlo)

1. **Comparar el path crudo.** El front resuelve `/trading/overview` →
   `/api/trading/overview`. Comparar crudo da 227 falsos positivos.
2. **Ignorar los root-mounted.** `ROOT_MOUNTED_PREFIXES` (27 namespaces) se
   sirven **sin** `/api`. Hay que aceptar ambas formas.

## Por qué un allowlist y no "0 rotas"

Un test que siempre falla entrena a ignorarlo; uno que se desactiva solo no
vigila nada. El allowlist documenta **qué está roto y por qué**, y los dos
tests de `TestElAllowlistEsVeraz` impiden que mienta: si uno de estos endpoints
vuelve a funcionar, hay que sacarlo; si uno nuevo aparece, el test falla.

**El allowlist NO es permiso para dejarlo así.** Cada entrada dice qué pantalla
se ve vacía. Cerrarlos es una decisión de producto por endpoint, no de este
archivo.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FRONTEND = REPO / "frontend" / "src"

CALL = re.compile(r"""api\.(get|post|put|patch|delete)(?:<[^>]*>)?\(\s*[`'"]([^`'"]+)""")
_PREF_RE = re.compile(r"'([^']+)'")


def _root_prefixes() -> set[str]:
    """Los namespaces que el front resuelve SIN /api, como los define el front."""
    ts = (FRONTEND / "lib" / "backend.ts").read_text(encoding="utf-8")
    block = ts.split("ROOT_MOUNTED_PREFIXES = [", 1)[1].split("]", 1)[0]
    return set(_PREF_RE.findall(block))


def _resolve(path: str, prefixes: set[str]) -> str:
    """Réplica de `resolveApiUrl` en backend.ts.

    Copia a propósito: el guard tiene que medir lo que el front REALMENTE
    pide. Si el resolver cambia, este test debe cambiar también — y que lo
    note un test rojo, no el owner en producción.
    """
    clean = path[4:] if path.startswith("/api/") else path
    clean = clean.split("?")[0].rstrip("/") or "/"
    is_root = any(clean == p or clean.startswith(p + "/") for p in prefixes)
    return clean if is_root else f"/api{clean}"


def _served(resolved: str, real: set[str]) -> bool:
    """Acepta la forma root-mounted y la /api.

    `/dev-bounty/status` se sirve en RAÍZ aunque su router lo declare
    `/api/dev-bounty/status`. Ignorar esto mete falsos positivos que hacen
    desconfiar del guard entero.
    """
    if resolved in real:
        return True
    return resolved.startswith("/api/") and resolved[4:] in real


@pytest.fixture(scope="module")
def backend_paths() -> set[str]:
    os.environ.setdefault("CATEYE_CSRF_DISABLED", "1")
    logging.disable(logging.CRITICAL)
    from api.main import app

    return {r.path for r in app.routes if getattr(r, "path", None)}


@pytest.fixture(scope="module")
def frontend_calls() -> dict[tuple[str, str], tuple[Path, int]]:
    """(método, path_resuelto) -> (archivo, línea). Excluye templates literales."""
    prefixes = _root_prefixes()
    out: dict[tuple[str, str], tuple[Path, int]] = {}
    for f in FRONTEND.rglob("*"):
        if f.suffix not in (".ts", ".vue") or "node_modules" in str(f):
            continue
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in CALL.finditer(line):
                method, path = m.group(1).upper(), m.group(2)
                if "${" in path:
                    continue  # path dinámico: no se puede resolver estático
                out.setdefault((method, _resolve(path, prefixes)), (f, ln))
    return out


class TestElGuardReplicaElResolver:
    def test_cada_root_mounted_existe_de_verdad_en_raiz(self, backend_paths: set[str]) -> None:
        """Una entrada en ROOT_MOUNTED_PREFIXES que da 404 en raíz rompe llamadas.

        MEDIDO 2026-10-05: de los 27 que había, **25 daban 404** y sólo 2
        respondían. Y como `resolveApiUrl` normaliza `/api/x` → `x` y después
        decide, incluso las llamadas con `/api` explícito terminaban en raíz:
        8 rotas (6 de `dev-bounty`, 2 de `wear-os`), 355 no afectadas.

        Este test es el que impida que la lista vuelva a inflarse.
        """
        # Un namespace por sí solo puede dar 404 aunque su router exista bajo
        # ese prefijo (`/wear-os` → 404, pero `/wear-os/approvals` → 200). Por
        # eso se verifica que el prefijo tenga AL MENOS un descendant en la
        # app real, no que el namespace exacto exista.
        falsos = [
            p
            for p in _root_prefixes()
            # Exacto (p.ej. /today) o con descendants (p.ej. /wear-os ->
            # /wear-os/approvals).
            if p not in backend_paths and not any(r.startswith(p + "/") for r in backend_paths)
        ]
        assert not falsos, (
            "estos namespaces están en ROOT_MOUNTED_PREFIXES pero el backend NO "
            f"sirve NINGUNA ruta bajo ellos: {falsos}\n\n"
            "  Cada uno hace que las llamadas que lo usen terminen en raíz y "
            "devuelvan 404. Sacalos de la lista (verificado: existen bajo "
            "/api), o montalos en raíz si eso es lo correcto."
        )

    def test_ambos_estilos_de_llamada_resuelven_igual(self) -> None:
        """`/x` y `/api/x` resuelven al mismo lado: el resolver normaliza."""
        prefixes = _root_prefixes()
        assert _resolve("/dev-bounty/status", prefixes) == _resolve("/api/dev-bounty/status", prefixes)

    def test_el_scanner_encuentra_las_llamadas(self, frontend_calls) -> None:
        """Guard contra un guard que dejó de mirar."""
        assert len(frontend_calls) > 300, f"sólo {len(frontend_calls)} endpoints: el scanner se rompió"


# ══════════════════════════════════════════════════════════════════
# Los 39 404 conocidos, agrupados por causa.
#
#   app-sin-backend : la pantalla existe, su API nunca se cableó
#   drift            : el backend movió el contrato, el front quedó atrás
#   root-vs-api     : ELIMINADO 2026-10-05 — la lista ROOT_MOUNTED_PREFIXES
#                     estaba inflada (25 de 27 daban 404 en raíz). Corregido
#                     en frontend/src/lib/backend.ts; ahora 404 = 0 de este tipo.
#
# ESTE allowlist NO ES "está bien así". Cada entrada es una pantalla que el
# owner ve vacía. Cerrarlas es decisión de producto, endpoint por endpoint.
# ══════════════════════════════════════════════════════════════════

CONOCIDOS_ROTOS: dict[str, tuple[str, str]] = {
    # ── Apps sin backend: la UI existe, la API nunca existió ──
    "/wear-os/approvals/pending": ("drift", "el back sirve /wear-os/approvals, no /approvals/pending"),
    "/wear-os/approval-request": ("drift", "el back sirve /wear-os/approval/{id} (raiz), no /request"),
    "/api/odyssey/analytics/summary": (
        "app-sin-backend",
        "DashboardOdyssey: analytics nunca existio; pantalla sin backend",
    ),
    "/api/odyssey/analytics/roi": ("app-sin-backend", "DashboardOdyssey: ROI nunca existio"),
    "/api/odyssey/analytics/performance": ("app-sin-backend", "DashboardOdyssey: performance nunca existio"),
    # ── trading-lab: ELIMINADO 2026-10-05. Los 6 endpoints nunca existieron
    #     y sus 6 funciones tenian 0 consumidores. Codigo muerto borrado de
    #     ownexData.ts (162 lineas). Ver #24 y #63.
    # ── Drift: el contrato se movió ──
    "/api/cycles/security/executive": ("drift", "el summary vive en /api/trading"),
    "/api/hypotheses": ("drift", "las hipótesis viven bajo /api/security"),
    "/api/files/list": ("drift", "workspace: sin listar archivos"),
    "/api/knowledge": ("drift", "knowledge: sin endpoint raíz"),
    "/api/learning/progress": ("drift", "progreso de aprendizaje sin endpoint"),
    "/api/mission/status": ("drift", "el estado de misión cambió de namespace"),
    "/api/modes/active": ("drift", "modes: sin endpoint /api/modes"),
    "/api/modes/history": ("drift", "modes: sin historial"),
    "/api/modes/set-force": ("drift", "modes: sin forzar modo"),
    "/api/profile-kit": ("drift", "profile-kit sin endpoint"),
    "/api/identity": ("drift", "sin endpoint de identidad"),
    "/api/quick-capture": ("drift", "captura rápida sin endpoint"),
    "/api/system/readiness": ("drift", "readiness no está en /api/system"),
    "/platform-guides": ("drift", "platform-guides sin endpoint raíz"),
}


class TestElAllowlistEsVeraz:
    """Sin esto, el allowlist es una lista de deseos que nadie chequea."""

    def test_los_conocidos_siguen_rotos(self, backend_paths: set[str]) -> None:
        """Si uno volvió a funcionar, sobra en la lista → hay que sacarlo."""
        falsos = [p for p in CONOCIDOS_ROTOS if _served(p, backend_paths)]
        assert not falsos, (
            "estos endpoints YA EXISTEN y hay que SACARLOS de CONOCIDOS_ROTOS:\n  "
            + "\n  ".join(falsos)
            + "\n  (si se arreglaron, la lista miente y el guard deja de avisar)"
        )

    def test_los_conocidos_existen_de_verdad_en_el_front(self) -> None:
        """Cada entrada debe ser una llamada REAL del front, no una invención."""
        llamadas = {
            _resolve(m.group(2), _root_prefixes())
            for f in FRONTEND.rglob("*")
            if f.suffix in (".ts", ".vue") and "node_modules" not in str(f)
            for m in CALL.finditer(f.read_text(encoding="utf-8"))
            if "${" not in m.group(2)
        }
        inventados = [p for p in CONOCIDOS_ROTOS if p not in llamadas]
        assert not inventados, "estas entradas del allowlist no las llama nadie — borralas:\n  " + "\n  ".join(
            inventados
        )


class TestNoPhantomRoutes:
    def test_todo_lo_llamado_por_el_front_existe(self, frontend_calls, backend_paths: set[str]) -> None:
        """Éste es el guard real: falla cuando aparece un 404 NUEVO.

        Los conocidos están verificados arriba; un path que no esté en el
        allowlist y el backend no sirva es deuda nueva.
        """
        nuevas = [
            (m, r, f, ln)
            for (m, r), (f, ln) in sorted(frontend_calls.items(), key=lambda kv: str(kv[1]))
            if not _served(r, backend_paths) and r not in CONOCIDOS_ROTOS
        ]
        assert not nuevas, (
            f"{len(nuevas)} endpoint(s) 404 que el front llama y el backend no sirve, "
            "y NO están en CONOCIDOS_ROTOS:\n"
            + "\n".join(f"  · {m} {r}\n      {f.relative_to(REPO)}:{ln}" for m, r, f, ln in nuevas)
            + "\n\n  Decidir: restaurar el endpoint, o borrar la llamada y agregar la entrada al allowlist."
        )
