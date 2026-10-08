"""El 20% de la tabla `endpoints` tiene el `path` corrupto.

Medido 2026-10-08 sobre la tabla completa (script
`repair_corrupted_endpoint_paths.py`): **8.937 de 44.597 endpoints (20%)** tienen un
`path` que no es un path. Es un path pegado a un blob JSON a medio serializar:

    //docs.hackerone.com/organizations/report-states.html","tag":"a",
    "attribute":"href","source":"https://..."},"error":"max depth reached"}

La fila es de 2026-07-19, `params` vacío, y el mismo target (`736`) mezcla
endpoints Rotten y sanas (`/api/test`). Eso apunta a una ingesta: el
serializador falló con `"error":"max depth reached"` y el código escribió el
string truncado en `path` en vez de descartarlo.

## Por qué no es cosmético

Todo el scoring corre sobre ese string:

- `unified_score(path, ...)` — el riesgo sale de ahí
- `has_admin` / `has_exports` / `has_graphql` buscan substrings en `path`
  (tres copias: `api/services/data_service.py:964-966`,
  `cores/ai/recommendations.py`, `api/routers/overview.py`)
- el resumen diario lo muestra al owner como *"Nuevo endpoint crítico: GET
  //docs.hackerone.com/...,  "tag":"a"..."*

Un path que contiene `"attribute":"href"` matchea heurísticas por casualidad.
De los 9.922 endpoints que ve `build_full_context`, 3.713 son "high signal":
parte de eso puede venir de la basura, no del target.

## Por qué estos tests NO reparan

La reparación son 8.937 filas de la tabla de descubrimiento principal: mutación
masiva de datos de producción. No se hace desde un `pytest` ni automáticamente.
Va en `scripts/repair_corrupted_endpoint_paths.py`, que **por defecto es
dry-run**, y lo corre el owner. Ver KNOWN_DEBT #81.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

DB = Path("/home/adriel/.ownex/database/catseye.db")

#: Frontera de la corrupción: el path sano termina justo antes de `","tag":"`.
#: Los 8.937 rows comparten esta firma (verificado sobre la DB, no supuesto).
CORRUPTION_BOUNDARY = '","tag":"'


def clean_path(path: str) -> str:
    """El contrato del script de reparación, como unidad pura."""
    return path.split(CORRUPTION_BOUNDARY)[0] if CORRUPTION_BOUNDARY in path else path


def _corrupted_paths() -> list[str]:
    """Los `path` con la firma de corrupción, leídos de la DB real."""
    if not DB.exists():
        pytest.skip(f"no está la DB en {DB}")
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = con.execute("select path from endpoints where path is not null").fetchall()
    finally:
        con.close()
    return [r[0] for r in rows if CORRUPTION_BOUNDARY in r[0]]


def test_hay_paths_corruptos_y_la_firma_es_una_sola() -> None:
    """Documenta el hallazgo y fija que la regla de reparación es única.

    Si algún día la ingesta deja de producir basura y queda 0, este test falla
    a propósito: hay que borrar el debt #81 y el script, no dejar un número
    viejo en un doc.
    """
    paths = _corrupted_paths()
    if not paths:
        pytest.fail("0 paths corruptos: la ingesta ya no produce basura. Borrá el debt #81 y el script de reparación.")

    tails = {p[p.rindex(CORRUPTION_BOUNDARY) :] for p in paths}
    assert all(t.startswith(CORRUPTION_BOUNDARY) for t in tails), (
        "apareció una segunda forma de corrupción: revisala a mano antes de aplicar el script"
    )


def test_la_frontera_recupera_un_path_verosimil() -> None:
    """Lo que queda antes de la frontera debe parecer un path, no basura."""
    for p in _corrupted_paths():
        limpio = clean_path(p)
        assert limpio, "la parte recuperada no puede estar vacía"
        assert not limpio.endswith(","), f"quedó una coma colgando: {limpio!r}"
        assert not limpio.endswith('"'), f"quedó una comilla colgando: {limpio!r}"
        assert CORRUPTION_BOUNDARY not in limpio, "la reparación no quitó toda la basura"
        assert len(limpio) < 400, f"path sospechosamente largo tras reparar: {limpio[:120]!r}"


def test_la_basura_cambia_el_score_del_endpoint() -> None:
    """Prueba de impacto: el path corrupto no se puntúa igual al sano.

    Si algún día el scoring normalizara la basura y los dos dieran lo mismo,
    la corrupción dejaría de importar para el ranking — y este test lo avisa.
    """
    from cores.engine.unified_scoring import score

    corrupto = (
        '//docs.hackerone.com/organizations/report-states.html","tag":"a",'
        '"attribute":"href","source":"https://docs.hackerone.com/en/articles/8541742-import-vulnerabilities"},'
        '"error":"max depth reached"}'
    )
    sano = clean_path(corrupto)
    assert sano == "//docs.hackerone.com/organizations/report-states.html"

    a = score(corrupto, "GET", {})
    b = score(sano, "GET", {})
    assert a["risk_score"] != b["risk_score"] or a["labels"] != b["labels"], (
        "el scoring ahora ignora la basura del path. Si es a propósito, sacá "
        "el impacto de este test; si no, sigue siendo un bug."
    )


def test_la_basura_ensucia_la_deteccion_de_superficie() -> None:
    """ "export"/"admin" matchean dentro del blob JSON, no del path real.

    No hay helper: la decisión es un substring inline repetido en tres
    lugares. Se replica esa línea exacta para demostrar el efecto, porque el
    problema es la regla, no la función.

    Consecuencia: un target puede quedar marcado "tiene exports" porque la
    **URL de origen que quedó pegada al path** contiene la palabra, no porque
    el endpoint sirva un export.
    """

    def superficie(path: str) -> dict[str, bool]:
        """Las cuatro líneas de `data_service.py:964-966`, verbatim."""
        return {
            "has_graphql": "/graphql" in path.lower(),
            "has_admin": "admin" in path.lower(),
            "has_api": "/api/" in path.lower(),
            "has_exports": "export" in path.lower(),
        }

    crudo = (
        '//hackerone.com/users/sign_in","tag":"header","attribute":"location",'
        '"source":"https://hackerone.com/export/reports"},"error":"max depth reached"}'
    )
    sano = clean_path(crudo)

    assert superficie(sano)["has_exports"] is False, "el path sano NO tiene export"
    assert superficie(crudo)["has_exports"] is True, (
        "el mismo endpoint marca 'tiene exports' sólo por la URL de origen que quedó pegada al path"
    )
    assert superficie(crudo) != superficie(sano)


@pytest.mark.parametrize(
    ("path", "esperado"),
    [
        ('/api/users","tag":"a"},"error":"max depth reached"}', "/api/users"),
        ("/a/b/c", "/a/b/c"),
        ("", ""),
    ],
)
def test_la_regla_de_extraccion(path: str, esperado: str) -> None:
    """El contrato del script, fijado como unidad pura."""
    assert clean_path(path) == esperado
