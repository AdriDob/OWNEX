"""Guard de rutas API duplicadas (ship-day 2026-09-28).

FastAPI resuelve por ORDEN de registro: si dos handlers comparten path+método,
el segundo es INALCANZABLE por HTTP (código muerto). Eso es exactamente lo
que se detectó en el audit final: 7 duplicados reales.

Resueltos con evidencia (6): `mission` 2º `/stale` y 2º checkpoint (body
idéntico) · `availability` alias `/max-task-hours` · `api.main` inline
`/version` (subconjunto del router) · `revenue_app` `/summary` (forma que el
front no consume) · `control` `/obsidian/sync` (sin body, superado por el
winner que sí lee {path, content, title}).

Pendiente (1): ver abajo. Este guard falla si aparece CUALQUIER duplicado
nuevo, y también si el pendiente desaparece sin actualizar el allowlist.
"""

from __future__ import annotations

import os
from collections import Counter

import pytest

# ÚNICO pendiente de decisión (ship-day 2026-09-28):
#   /api/trading/dashboard/summary GET
#     winner: trading_dashboard:trading_dashboard_summary (estado de jobs)
#     muerto: trading:dashboard_summary            (copy+masters+intelligence)
# No se borró porque el muerto es MÁS RICO que el ganador y ningún caller del
# repo lo consume: borrarlo destruiría capacidad que un cliente externo
# (Tauri/Android) podría necesitar. Decidir: (a) dejar el winner, (b) dar al
# rico un path propio, o (c) eliminarlo.
#
# RESUELTO 2026-10-04 (opción c) — commit 7a4f2acf. Se eliminó el duplicado de
# `api/routers/trading_dashboard.py`. Verificado antes de borrar:
#   - 0 referencias a `dashboard/summary` en frontend/, src-tauri/, android/,
#     apps/, desktop/ (la[#19] sospecha de que un cliente externo lo necesitaba
#     era especulativa: medida, es 0)
#   - el front usa `/api/trading/overview`, servido por trading.py, intacto
#   - `trading.py` queda como único dueño de ese path, con los 32 endpoints
#   - el test que lo exigía (`test_trading_router_mounted_and_accionable`)
#     pasa ahora de forma determinista en vez de depender del orden de
#     registro de FastAPI
# Allowlist vacío: no queda ningún duplicado pendiente de decisión.
PENDING_OWNER_DECISION: frozenset[tuple[str, tuple[str, ...]]] = frozenset()


@pytest.fixture(scope="module")
def duplicates() -> set[tuple[str, tuple[str, ...]]]:
    os.environ.setdefault("CATEYE_CSRF_DISABLED", "1")
    import api.main as m

    routes = [
        (getattr(r, "path", ""), tuple(sorted(getattr(r, "methods", []) or [])))
        for r in m.app.routes
        if getattr(r, "path", "")
    ]
    return {k for k, v in Counter(routes).items() if v > 1}


def test_no_new_duplicate_routes(duplicates: set[tuple[str, tuple[str, ...]]]) -> None:
    new = duplicates - PENDING_OWNER_DECISION
    assert not new, f"Rutas API duplicadas nuevas (la 2ª es inalcanzable por HTTP): {sorted(new)}"


def test_pending_duplicates_still_known(duplicates: set[tuple[str, tuple[str, ...]]]) -> None:
    """Si alguien eliminó uno de los pendientes sin actualizar el allowlist, falla."""
    missing = PENDING_OWNER_DECISION - duplicates
    assert not missing, (
        f"Los pendientes de decisión ya no son duplicados: {sorted(missing)} — "
        "actualizá PENDING_OWNER_DECISION con la decisión tomada."
    )
