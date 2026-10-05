"""
CSRF double-submit — el loop de escritura del producto.

Contexto (bug preexistente, medido 2026-10-05): el middleware ponía la cookie
`csrf-token` con `httponly=True`, lo que hace IMPOSIBLE el patrón double-submit
que su propio docstring describe (el cliente debe leer la cookie y reenviarla
en `X-CSRF-Token`). El frontend nunca mandaba ese header, así que TODO
POST/PUT/DELETE/PATCH del navegador devolvía 403: aprobar entregas, cambiar
modos, resolver alertas. Los e2e no lo veían porque no hacen POST.

Estos tests fijan las TRES propiedades:
  1. La cookie es legible por JS (si no, el patrón no puede funcionar).
  2. Sin header o con header falso ⇒ 403 (la protección sigue viva).
  3. Con el header correcto ⇒ pasa (y si falla, es la máquina de estados).
"""

import importlib
import os

import pytest

from api.middleware.csrf_middleware import COOKIE_NAME, HEADER_NAME, SAFE_METHODS
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    # `tests/conftest.py:11` desactiva CSRF para TODA la suite con
    # `CATEYE_CSRF_DISABLED=1` — por eso ningún test podía detectar que el
    # navegador recibía 403 en cada POST. Aquí se reactiva y se recarga el
    # módulo antes de importar la app.
    os.environ.pop("CATEYE_CSRF_DISABLED", None)
    importlib.reload(importlib.import_module("api.middleware.csrf_middleware"))
    from api.main import app

    return TestClient(app)


@pytest.fixture(scope="module")
def token(client):
    r = client.post("/api/auth/login", json={"username": "csrf_probe", "password": "csrf-probe-12345"})
    if r.status_code != 200:
        r = client.post("/api/auth/register", json={"username": "csrf_probe", "password": "csrf-probe-12345"})
    data = r.json()
    tok = data.get("data", {}).get("token")
    if not tok:
        pytest.skip("no se pudo autenticar")
    return tok


def _prime(client, token):
    """Un GET cualquiera deja la cookie csrf puesta."""
    client.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})


def test_la_cookie_csrf_debe_ser_legible_por_js(client, token):
    """Si es httpOnly, el double-submit es imposible y nada puede funcionar.

    Se lee el atributo del `Set-Cookie` real, no la cookie ya normalizada del
    cliente (TestClient la guarda aunque venga `HttpOnly`), porque lo que
    importa es lo que el navegador decide dejar leer a JS.
    """
    c = TestClient(client.app)
    r = c.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})
    raw = r.headers.get("set-cookie", "")
    if COOKIE_NAME not in raw:
        # La cookie ya venía de un GET previo: se fuerza uno nuevo.
        c.cookies.clear()
        r = c.get("/api/system/status", headers={"Authorization": f"Bearer {token}"})
        raw = r.headers.get("set-cookie", "")
    assert COOKIE_NAME in raw, "no se emitió la cookie csrf"
    assert "httponly" not in raw.lower(), f"la cookie {COOKIE_NAME} no puede ser httpOnly: el cliente debe poder leerla"


def test_post_sin_header_sigue_bloqueado(client, token):
    """La protección NO se desactivó: sin header, 403."""
    _prime(client, token)
    r = client.post(
        "/dev-bounty/execute",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403, "sin X-CSRF-Token el POST debe rechazarse"


def test_post_con_header_falso_sigue_bloqueado(client, token):
    _prime(client, token)
    r = client.post(
        "/dev-bounty/execute",
        json={},
        headers={"Authorization": f"Bearer {token}", HEADER_NAME: "0" * 64},
    )
    assert r.status_code == 403, "un token que no corresponde debe rechazarse"


def test_post_con_header_correcto_pasa_csrf(client, token):
    """Con el token correcto NO puede ser 403: si falla, es otra capa."""
    _prime(client, token)
    csrf = client.cookies.get(COOKIE_NAME)
    assert csrf, "no hay cookie csrf para reenviar"
    r = client.post(
        "/dev-bounty/execute",
        json={},
        headers={"Authorization": f"Bearer {token}", HEADER_NAME: csrf},
    )
    assert r.status_code != 403, "con el header correcto el CSRF no debe bloquear"


def test_metodos_seguros_no_exigen_csrf(client):
    for method in ("get", "head", "options"):
        assert method.upper() in SAFE_METHODS
