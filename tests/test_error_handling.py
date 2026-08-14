"""FASE 2 — Error handling: los 5xx nunca exponen detalles internos al cliente.

Verifica que:
1. HTTPException(500, detail=str(e)) → el cliente recibe {"detail": "Internal server error"}
   (el detalle crudo queda SOLO en el log del servidor).
2. Errores 4xx intencionales (400/404/403) preservan su detail.
3. Excepciones no manejadas → 500 genérico (no stack trace al cliente).
4. Toda respuesta lleva X-Operation-Id (trazabilidad request→log).
"""

import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.middleware.error_handling import ErrorHandlingMiddleware, http_exception_handler


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)

    @app.get("/boom-detail")
    async def boom_detail():
        raise HTTPException(500, detail=str(ValueError("sqlite3.OperationalError: no such table /secret/path")))

    @app.get("/boom-unhandled")
    async def boom_unhandled():
        raise RuntimeError("hidden traceback /etc/passwd")

    @app.get("/bad-request")
    async def bad_request():
        raise HTTPException(400, detail="invalid input: missing field x")

    @app.get("/not-found")
    async def not_found():
        raise HTTPException(404, detail="no such resource")

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_build_app())


def test_500_with_detail_is_generic(client: TestClient, caplog):
    caplog.set_level(logging.ERROR, logger="ownex.error")
    resp = client.get("/boom-detail")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal server error"
    assert "no such table" not in resp.text
    assert "/secret/path" not in resp.text
    assert "operation_id" in body
    log_text = caplog.text
    assert "http_exception" in log_text
    assert "no such table /secret/path" in log_text


def test_500_response_has_operation_id_header(client: TestClient):
    resp = client.get("/boom-detail")
    assert resp.headers.get("X-Operation-Id")
    assert resp.headers["X-Operation-Id"] == resp.json()["operation_id"]


def test_ok_response_has_operation_id_header(client: TestClient):
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.headers.get("X-Operation-Id")


def test_unhandled_exception_returns_generic_500(client: TestClient, caplog):
    caplog.set_level(logging.ERROR, logger="ownex.error")
    resp = client.get("/boom-unhandled")
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"] == "Internal server error"
    assert "/etc/passwd" not in resp.text
    assert "hidden traceback" not in resp.text
    assert "unhandled_exception" in caplog.text


def test_4xx_preserves_intentional_detail(client: TestClient):
    resp = client.get("/bad-request")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid input: missing field x"

    resp = client.get("/not-found")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "no such resource"


def test_404_default_starlette_still_works(client: TestClient):
    resp = client.get("/no-such-route")
    assert resp.status_code == 404


def test_router_500_via_real_import():
    """Smoke: el handler global está registrado en la app real."""
    import api.main as api_main

    assert api_main.http_exception_handler is not None
    handlers = {exc.__name__: h for exc, h in api_main.app.exception_handlers.items()}
    assert "HTTPException" in handlers
    assert handlers["HTTPException"] == api_main.http_exception_handler
