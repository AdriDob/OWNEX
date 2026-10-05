"""
La discovery automática devuelve datos FICTICIOS — cerrado.

Hallazgo 2026-10-05. Las 7 "fuentes" de
`cores/financial_intelligence/infinite_source_discovery.py` (LinkedIn, Indeed,
RemoteOK, WeWorkRemotely, FlexJobs, GitHub, Fiverr) **no hacen ninguna
llamada de red**: `discover_sources()` devuelve listas escritas a mano con
URLs inventadas (`linkedin.com/jobs/view/123`, `fiverr.com/gig/123`) y rates
inventados. Se los bardea como "oportunidades zero-barrier".

Eso es la misma clase de mentira que el proyecto ya pagó dos veces (pipeline
de $5.810 sin pago real; `UNKNOWN` renderizado como `$0`), y era exactamente
la feature que el owner pedía — "más fuentes sin experiencia ni entrevista".

Estos tests fijan que la puerta no se reabra por descuido.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

MODULE = Path("cores/financial_intelligence/infinite_source_discovery.py")


@pytest.fixture(scope="module")
def client():
    from api.main import app

    return TestClient(app)


def test_ninguna_fuente_hace_llamada_de_red():
    """Si algún día hay red real, este test obliga a revisarlo a propósito."""
    src = MODULE.read_text(encoding="utf-8")
    for name in re.findall(r"def (_search_\w+)", src):
        block = src[src.index(f"def {name}") : src.index(f"def {name}") + 3000]
        simulated = "simulated_jobs" in block or "Simulated results" in block
        real = bool(re.search(r"httpx|requests\.get|res\.json|resp\.json", block))
        assert simulated and not real, (
            f"{name}: cambió la forma (simulated={simulated}, red={real}). "
            "Si pasó a ser real, sacá el `410` del endpoint y actualizá este test."
        )


def test_discover_responde_410_con_el_motivo(client):
    """410 y no 5xx: el handler oculta el detail de todo 5xx (política correcta)."""
    tok = client.post("/api/auth/login", json={"username": "infinite_probe", "password": "probe-12345"})
    if tok.status_code != 200:
        tok = client.post("/api/auth/register", json={"username": "infinite_probe", "password": "probe-12345"})
    token = tok.json().get("data", {}).get("token")
    if not token:
        pytest.skip("no se pudo autenticar")
    client.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})
    h = {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": client.cookies.get("csrf-token", ""),
    }

    r = client.post("/api/infinite-sources/discover", json={}, headers=h)
    assert r.status_code == 410, "la discovery simulada no debe volver a servirse"
    detail = r.json().get("detail", "")
    assert "simulad" in detail.lower(), f"el motivo debe explicar el porqué: {detail!r}"


def test_ultra_fast_no_fabrica_oportunidades(client):
    """`generate_plan()` sin datos reales falla en vez de inventar trabajo."""
    from cores.financial_intelligence.ultra_fast_income import get_ultra_fast_income_engine

    engine = get_ultra_fast_income_engine()
    with pytest.raises(ValueError, match="oportunidades reales"):
        engine.generate_plan(None)


def test_http_exception_conserva_su_detalle(client):
    """Regresión del middleware: `except Exception` degradaba los 4xx a 500.

    Sin el `except HTTPException: raise`, todo mensaje deliberado de los
    routers (404 "no encontrado", 410 "retirado") llegaba al usuario como
    "Internal server error".
    """
    tok = (
        client.post("/api/auth/login", json={"username": "infinite_probe", "password": "probe-12345"})
        .json()
        .get("data", {})
        .get("token")
    )
    if not tok:
        pytest.skip("no se pudo autenticar")
    r = client.get("/api/does-not-exist-xyz", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404
    assert r.json().get("detail") == "Not Found", "el detail de un 4xx no puede genéricizarse"
