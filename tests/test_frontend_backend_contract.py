"""Guard de contrato frontend↔backend con allowlist que se autoverifica.

Por qué existe (2026-10-05). Auditoría de las 624 llamadas `api.*` del
frontend contra las 1734 rutas del backend, usando **el resolver real del
front** (`frontend/src/lib/backend.ts::resolveApiUrl`):

    endpoints distintos que el front llama : 402
    con backend                          : 363
    SIN backend                         :  39   ← 404 garantizado

Los 39 caen en pantallas que el owner ve: `DashboardAegis`, `SettingsAtlas`,
`ModeManagerPanel`, `CopilotConsolidated`, `ProfileConsolidated`,
`QuickCapture`, `SecurityConsolidated`, `TradingConsolidated` (vía trading-lab).

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
    def test_los_root_mounted_siguen_declarados(self) -> None:
        prefixes = _root_prefixes()
        assert len(prefixes) >= 25, f"se esperaban ~27 root-mounted, hay {len(prefixes)}"
        assert "/dev-bounty" in prefixes, "cambió el resolver; actualizá la réplica"

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
#   root-vs-api     : el front pide en raíz, el backend sirve bajo /api
#
# ESTE allowlist NO ES "está bien así". Cada entrada es una pantalla que el
# owner ve vacía. Cerrarlas es decisión de producto, endpoint por endpoint.
# ══════════════════════════════════════════════════════════════════

CONOCIDOS_ROTOS: dict[str, tuple[str, str]] = {
    # ── Apps sin backend: la UI existe, la API nunca existió ──
    "/api/aegis/targets": ("app-sin-backend", "SettingsAegis: targets sin API"),
    "/api/aegis/findings": ("app-sin-backend", "DashboardAegis: findings sin API"),
    "/api/aegis/findings/open": ("app-sin-backend", "DashboardAegis: findings abiertos sin API"),
    "/api/aegis/targets/active": ("app-sin-backend", "DashboardAegis: targets activos sin API"),
    "/api/aegis/scans/today": ("app-sin-backend", "DashboardAegis: scans del día sin API"),
    "/api/atlas/health": ("app-sin-backend", "SettingsAtlas: health de atlas sin API"),
    "/api/odyssey/analytics/summary": ("app-sin-backend", "DashboardOdyssey: analytics sin API"),
    "/api/odyssey/analytics/roi": ("app-sin-backend", "DashboardOdyssey: ROI sin API"),
    "/api/odyssey/analytics/performance": ("app-sin-backend", "DashboardOdyssey: performance sin API"),
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
    "/api/trading-lab/dashboard": ("drift", "trading-lab: 8 funciones sin API (ver #24)"),
    "/api/trading-lab/engines": ("drift", "trading-lab: engines sin API"),
    "/api/trading-lab/risk/summary": ("drift", "trading-lab: risk sin API"),
    "/api/trading-lab/strategies/rankings": ("drift", "trading-lab: rankings sin API"),
    "/api/trading-lab/validation/status": ("drift", "trading-lab: validation sin API"),
    "/api/trading-lab/capital/snapshot": ("drift", "trading-lab: capital sin API"),
    "/platform-guides": ("drift", "platform-guides sin endpoint raíz"),
    "/wear-os/approvals/pending": ("drift", "wear-os: approvals sin API"),
    "/wear-os/approval-request": ("drift", "wear-os: request sin API"),
    # ── root-vs-api: el front pide en raíz, el backend sirve bajo /api ──
    "/dev-bounty/status": ("root-vs-api", "el backend sirve /api/dev-bounty/*"),
    "/dev-bounty/activate": ("root-vs-api", "el backend sirve /api/dev-bounty/*"),
    "/dev-bounty/deactivate": ("root-vs-api", "el backend sirve /api/dev-bounty/*"),
    "/dev-bounty/run": ("root-vs-api", "el backend sirve /api/dev-bounty/*"),
    "/dev-bounty/queue": ("root-vs-api", "el backend sirve /api/dev-bounty/*"),
    "/dev-bounty/beginner-mode": ("root-vs-api", "el backend sirve /api/dev-bounty/*"),
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
