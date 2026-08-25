"""Guardián de montaje completo del backend.

Dos regresiones que este test hace imposibles:

1. **Boot parcial silencioso**: api/main.py envolvía el montaje de ~100 routers
   en try/except non-fatal; cualquier WIP roto dejaba la app viva SIN sus rutas
   (404 masivos intermitentes). Hoy mount_routers() es fail-fast y main.py no
   traga el import.
2. **Router huérfano**: api/routers/copilot.py definió 17 rutas durante semanas
   sin estar montado (el 401 del AuthMiddleware enmascaraba el 404).

Si agregás un router mayor a api/main.py, sumá un path representativo a
CANONICAL_PATHS. Si eliminás uno, actualizá la lista con justificación.
"""

from __future__ import annotations

from typing import Any


def _flatten_routes(routes: list[Any], out: set[str], depth: int = 0) -> None:
    """Resuelve los wrappers lazy (_IncludedRouter) de FastAPI reciente."""
    if depth > 5:
        return
    for r in routes:
        if hasattr(r, "original_router"):
            _flatten_routes(r.original_router.routes, out, depth + 1)
        else:
            p = getattr(r, "path", None)
            if p:
                out.add(p)


# Paths canónicos: al menos uno por cada router mayor del producto.
CANONICAL_PATHS = [
    # núcleo
    "/api/health",
    "/api/targets",
    "/api/findings",
    "/api/verdicts",
    "/api/scans/runs",
    # producto económico (Prompt 2)
    "/api/applications/income-plan",
    "/direct-work/workbank",
    # copilot — el ex-huérfano (17 rutas)
    "/api/copilot/status",
    "/api/copilot/chat",
    # trading + inversión
    "/api/trading/dashboard/summary",
    "/api/investment/status",
    "/api/investment/ccxt/info",
    # IA
    "/api/settings/ai/providers",
    # infraestructura
    "/wear-os/notifications",
    "/mobile/status",
    "/api/core/health/summary",
    "/api/knowledge/health",
]

MIN_ROUTE_FLOOR = 1100


def _all_paths() -> set[str]:
    import api.main  # noqa: PLC0415

    out: set[str] = set()
    _flatten_routes(api.main.app.routes, out)
    return out


class TestMountCompleteness:
    def test_route_floor(self) -> None:
        """El boot parcial silencioso dejaba ~11-163 rutas. El piso real es ~1280."""
        paths = _all_paths()
        assert len(paths) >= MIN_ROUTE_FLOOR, (
            f"Solo {len(paths)} rutas montadas (< {MIN_ROUTE_FLOOR}). "
            "Un include falló en silencio o el boot está parcial."
        )

    def test_canonical_paths_present(self) -> None:
        paths = _all_paths()
        missing = [p for p in CANONICAL_PATHS if p not in paths]
        assert not missing, (
            f"Rutas canónicas ausentes del app montado: {missing}. "
            "Un router quedó sin montar (ver api/main.py includes)."
        )

    def test_copilot_never_orphaned_again(self) -> None:
        paths = _all_paths()
        assert "/api/copilot/status" in paths and "/api/copilot/chat" in paths
