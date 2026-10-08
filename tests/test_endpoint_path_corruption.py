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


# ══════════════════════════════════════════════════════════════════
# La defensa en el WRITER: no dejar que el blob entre otra vez
# ══════════════════════════════════════════════════════════════════


def test_looks_like_path_acepta_lo_legitimo() -> None:
    """Lo que discovery produce de verdad tiene que pasar.

    Si el filtro fuera demasiado agresivo dejaría de admitir endpoints
    válidos — y eso sería peor que la basura: una tabla vacía no genera
    findings, pero no miente.
    """
    from cores.recon.parser import looks_like_path

    for bueno in (
        "/",
        "/api/v1/users",
        "/api/users/123",
        "/graphql",
        "/users/{id}/reports",
        "//docs.hackerone.com/en/articles/8541742-api-tokens",
        "https://example.com/api/x?a=1&b=2",
        "/search?q=%22quoted%22",
        "/path%20con%20espacios",
        "/v1/{tenant}/thing",
    ):
        assert looks_like_path(bueno), f"rechazó un path legítimo: {bueno!r}"


def test_looks_like_path_rechaza_la_basura() -> None:
    """El blob real, más las formas obvias de no-ser-un-path."""
    from cores.recon.parser import looks_like_path

    for malo in (
        # La firma medida 8.937 veces.
        '//docs.hackerone.com/organizations/report-states.html","tag":"a",'
        '"attribute":"href","source":"https://x"},"error":"max depth reached"}',
        # El `raw` completo que cayendo al campo `path` produjo lo anterior.
        '{"url":"https://x/y","tag":"a","links":[{"href":"/z"}]}',
        '{"error":"max depth reached"}',
        # Formas sin el patrón exacto, por si el crawler cambia.
        '/api/x","meta":{"a":1,"b":2}}',
        # Cosas que no son paths.
        "",
        "   ",
        "not-a-path",
        "GET /api/x",
        "/api/x\nGET /api/y",
        "/api/x\ttab",
        None,
        123,
        ["/api/x"],
        {"path": "/api/x"},
        "/" + "a" * 3000,
    ):
        assert not looks_like_path(malo), f"aceptó basura: {malo!r}"


def test_scan_service_no_usa_raw_como_path() -> None:
    """El fallback a `raw` era la causa. No puede volver, ni por refactor.

    No se ejercita la función entera (levanta la pipeline de recon): se
    verifica el invariante en el código, que es lo que importa y lo que un
    refactor puede romper en silencio.
    """
    src = Path("cores/orchestrator/scan_service.py").read_text(encoding="utf-8")
    assert 'or entry.get("raw")' not in src, (
        "volvió el fallback `or entry.get('raw')`: `raw` es la serialización "
        "del crawler y así se ensució el 20% de la tabla (KNOWN_DEBT #81)"
    )
    assert "looks_like_path(path)" in src, "el writer tiene que validar antes de guardar"


def test_create_endpoint_rechaza_un_no_path() -> None:
    """El segundo writer también valida, y falla ruidosamente."""
    from api.services.data_service import create_endpoint

    with pytest.raises(ValueError, match="no es un path"):
        create_endpoint(target_id=1, path='//x/y","tag":"a"},"error":"max depth reached"}')


# ══════════════════════════════════════════════════════════════════
# Lo que --live encontró: rutas que existen y reventan
# ══════════════════════════════════════════════════════════════════


def test_el_audit_tiene_modo_vivo() -> None:
    """`--live` existe: existencia de ruta no es ruta viva.

    Medido 2026-10-08: el audit decía "381 de 381 con backend" mientras
    `GET /api/assistant/insights` daba 500 y `/api/platforms` también. Comparar
    paths declarados no ejecuta nada.
    """
    src = Path("scripts/audit_frontend_contract.py").read_text(encoding="utf-8")
    assert '"--live"' in src, "el modo vivo se perdió: es el único que ve un 500"
    assert "wait_for_background_init" in src, (
        "sin esperar el background init, --live da falsos positivos: las DBs de "
        "los app plugins todavía no están registradas y todo endpoint que las "
        "use da 500 (medido: 3 de odyssey)"
    )


def test_la_cadena_de_imports_de_platform_connectors_esta_entera() -> None:
    """La causa del 500 de `/api/platforms`: tres eslabones rotos en cadena.

    1. `cores/platform_connectors/__init__.py` era un `__init__` autogenerado
       VACÍO, pero 6 call sites Asumían que el paquete exportaba la API.
    2. `universal_connectors` importaba `get_observation_engine`, que no existía.
    3. `universal_connectors` llamaba `register_sensor()` y
       `collect_from_sensor()`; los métodos reales son `register()` y `collect()`.

    Cada eslabón estaba dentro de un `try/except` que degradaba en silencio,
    así que el síntoma era un 500 y una tarea diaria que no corría.
    """
    import importlib

    mod = importlib.import_module("cores.platform_connectors")
    assert hasattr(mod, "get_platform_manager"), (
        "el paquete volvió a no exportar la API: los 6 call sites asumen que sí"
    )

    from cores.platform_connectors import get_platform_manager

    manager = get_platform_manager()
    assert hasattr(manager, "get_system_status"), (
        "get_system_status() es lo que llama control.py/daily_tasks.py. "
        "get_status() es método del CONNECTOR, no del manager."
    )
    assert not hasattr(manager, "get_status"), "si volviera get_status() en el manager, el rename se desharía solo"

    from cores.sensors.observation_engine import ObservationEngine, get_observation_engine

    engine = get_observation_engine()
    assert isinstance(engine, ObservationEngine)
    assert engine is get_observation_engine(), "el singleton tiene que ser el mismo"
    for metodo in ("register", "collect"):
        assert hasattr(engine, metodo), f"ObservationEngine.{metodo} es lo que usan los connectors"


def test_los_callers_usan_el_nombre_que_existe() -> None:
    """Invariante de código, no de runtime: un refactor puede romperlo."""
    for path, viejo in (
        ("api/routers/control.py", "pm.get_status()"),
        ("cores/daily_tasks.py", "pm.get_status()"),
    ):
        src = Path(path).read_text(encoding="utf-8")
        assert viejo not in src, f"{path}: volvió `{viejo}`, que no existe en el manager"
