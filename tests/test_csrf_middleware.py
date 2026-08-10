"""SELF-2 — CSRF middleware test coverage (KNOWN_DEBT #2).

Covers the double-submit cookie contract of `api.middleware.csrf_middleware`:
  - GET sets the csrf cookie once, and only when absent.
  - POST/PUT/DELETE/PATCH without cookie+header → 403.
  - Token mismatch → 403.
  - Matching token → passes through.
  - Safe methods (GET/HEAD/OPTIONS/TRACE) exempt.
  - EXEMPT_PATHS bypass without token.
  - WebSocket scope bypass.
  - CATEYE_CSRF_DISABLED=1 explicit opt-out disables enforcement.

The tests mount a minimal FastAPI app + CSRFMiddleware in isolation so they do
not depend on `api.main` boot (slow scrapings) or the global conftest flag
``CATEYE_CSRF_DISABLED=1`` (which is deleted via monkeypatch per-test).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.middleware.csrf_middleware import (
    COOKIE_NAME,
    EXEMPT_PATHS,
    HEADER_NAME,
    SAFE_METHODS,
    CSRFMiddleware,
)


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/protected")
    async def protected_get() -> dict:
        return {"ok": True}

    @app.post("/api/protected")
    async def protected_post() -> dict:
        return {"ok": True}

    @app.put("/api/protected")
    async def protected_put() -> dict:
        return {"ok": True}

    @app.patch("/api/protected")
    async def protected_patch() -> dict:
        return {"ok": True}

    @app.delete("/api/protected")
    async def protected_delete() -> dict:
        return {"ok": True}

    @app.get("/api/health")
    async def exempt_get() -> dict:
        return {"ok": True}

    @app.post("/api/health")
    async def exempt_post() -> dict:
        return {"ok": True}

    @app.get("/api/versions")
    async def safe_head_target() -> dict:
        return {"ok": True}

    app.add_middleware(CSRFMiddleware)
    return app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # conftest sets this globally to 1; the middleware must be ACTIVE here.
    monkeypatch.delenv("CATEYE_CSRF_DISABLED", raising=False)
    return TestClient(_make_app())


def test_get_sets_csrf_cookie(client: TestClient) -> None:
    resp = client.get("/api/protected")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    cookie = resp.cookies.get(COOKIE_NAME)
    assert cookie
    assert len(cookie) == 64  # secrets.token_hex(32)


def test_get_does_not_rewrite_existing_cookie(client: TestClient) -> None:
    first = client.get("/api/protected")
    token = first.cookies.get(COOKIE_NAME)
    second = client.get("/api/protected")
    # Middleware does not re-Set-Cookie when the jar already holds one; the
    # client-side jar value must remain stable across requests.
    assert client.cookies.get(COOKIE_NAME) == token
    assert second.cookies.get(COOKIE_NAME) is None


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_state_change_without_token_403(client: TestClient, method: str) -> None:
    resp = getattr(client, method)("/api/protected")
    assert resp.status_code == 403
    assert b"CSRF validation failed" in resp.content


def test_token_mismatch_403(client: TestClient) -> None:
    client.get("/api/protected")
    resp = client.post("/api/protected", headers={HEADER_NAME: "wrong-header-token"})
    assert resp.status_code == 403


def test_missing_header_403_even_with_cookie(client: TestClient) -> None:
    client.get("/api/protected")
    resp = client.post("/api/protected")
    assert resp.status_code == 403


def test_matching_token_passes(client: TestClient) -> None:
    client.get("/api/protected")
    token = client.cookies.get(COOKIE_NAME)
    assert token
    resp = client.post("/api/protected", headers={HEADER_NAME: token})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.parametrize("method", ["get", "head", "options", "trace"])
def test_safe_methods_exempt(client: TestClient, method: str) -> None:
    # Safe methods bypass the CSRF check entirely: either the route answers
    # (200) or the framework rejects it (405/etc.) — but never a CSRF 403.
    if method == "trace":
        resp = client.request("TRACE", "/api/protected")
    else:
        resp = getattr(client, method)("/api/protected")
    assert resp.status_code != 403


def test_safe_methods_set_is_subset() -> None:
    assert SAFE_METHODS <= {"GET", "HEAD", "OPTIONS", "TRACE"}


def test_exempt_path_posts_bypass(client: TestClient) -> None:
    assert "/api/health" in EXEMPT_PATHS
    resp = client.post("/api/health")
    assert resp.status_code == 200


def test_disabled_env_var_bypasses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CATEYE_CSRF_DISABLED", "1")
    app = _make_app()
    client = TestClient(app)
    resp = client.post("/api/protected")
    assert resp.status_code == 200


def test_websocket_scope_bypasses() -> None:
    """Test that websocket scope bypasses CSRF check using pure Starlette.

    Uses Starlette's WebSocketRoute + TestClient to verify the middleware's
    websocket branch passes through without CSRF cookie/header.
    """
    from starlette.applications import Starlette
    from starlette.routing import WebSocketRoute
    from starlette.testclient import TestClient as StarletteClient
    from starlette.websockets import WebSocket

    async def ws_handler(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            pass

    app = Starlette(routes=[WebSocketRoute("/ws", ws_handler)])
    app.add_middleware(CSRFMiddleware)
    client = StarletteClient(app)
    # CSRFMiddleware must pass websocket scope through untouched — the client
    # opens a connection without any CSRF cookie/header and succeeds.
    with client.websocket_connect("/ws") as sock:
        sock.send_text("ping")
