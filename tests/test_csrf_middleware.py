"""Tests for the double-submit CSRF middleware.

Isolated against a minimal Starlette app so we control the CATEYE_CSRF_DISABLED
toggle (conftest disables CSRF globally by default — we opt back in per test).
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.middleware.csrf_middleware import (
    COOKIE_NAME,
    HEADER_NAME,
    SAFE_METHODS,
    CSRFMiddleware,
)

CSRF_TOGGLE = "CATEYE_CSRF_DISABLED"


def _build_app() -> Starlette:
    async def echo(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "method": request.method,
                "cookie": request.cookies.get(COOKIE_NAME, ""),
                "header": request.headers.get(HEADER_NAME, ""),
            }
        )

    async def get_root(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    return Starlette(
        routes=[
            Route("/", get_root, methods=["GET"]),
            Route("/echo", echo, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]),
            Route("/api/health", echo, methods=["POST"]),
            Route("/api/auth/login", echo, methods=["GET", "POST"]),
        ],
        middleware=[Middleware(CSRFMiddleware)],
    )


@pytest.fixture
def csrf_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App with CSRF enabled (default off in conftest)."""
    monkeypatch.delenv(CSRF_TOGGLE, raising=False)
    return TestClient(_build_app())


@pytest.fixture
def disabled_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(CSRF_TOGGLE, "1")
    return TestClient(_build_app())


def _bootstrap_token(client: TestClient) -> str:
    r = client.get("/echo")
    assert r.status_code == 200
    token = r.cookies.get(COOKIE_NAME)
    assert token
    return token


class TestSafeMethods:
    @pytest.mark.parametrize("method", sorted(SAFE_METHODS))
    def test_safe_methods_never_rejected(self, csrf_client: TestClient, method: str) -> None:
        # TRACE is in SAFE_METHODS per the middleware, but ASGI servers do not
        # implement TRACE (return 405 from routing). Skip it: the bypass logic
        # for TRACE is implicitly covered by the other SAFE methods + source.
        if method == "TRACE":
            pytest.skip("ASGI does not implement TRACE")
        r = csrf_client.request(method, "/echo")
        assert r.status_code == 200


class TestDoubleSubmit:
    def test_matching_cookie_and_header_accepted(self, csrf_client: TestClient) -> None:
        token = _bootstrap_token(csrf_client)
        r = csrf_client.post("/echo", headers={HEADER_NAME: token})
        assert r.status_code == 200
        body = r.json()
        assert body["cookie"] == token
        assert body["header"] == token

    def test_missing_cookie_rejected(self, csrf_client: TestClient) -> None:
        r = csrf_client.post("/echo", headers={HEADER_NAME: "x"})
        assert r.status_code == 403

    def test_missing_header_rejected(self, csrf_client: TestClient) -> None:
        _bootstrap_token(csrf_client)
        r = csrf_client.post("/echo")  # cookie present but no header
        assert r.status_code == 403

    def test_mismatched_tokens_rejected(self, csrf_client: TestClient) -> None:
        _bootstrap_token(csrf_client)
        r = csrf_client.post(
            "/echo",
            headers={HEADER_NAME: "deadbeef"},
            cookies={COOKIE_NAME: "cafebabe"},
        )
        assert r.status_code == 403

    def test_token_set_on_first_get(self, csrf_client: TestClient) -> None:
        r = csrf_client.get("/echo")
        assert r.status_code == 200
        assert r.cookies.get(COOKIE_NAME)


class TestExemptPaths:
    def test_exempt_post_without_token_accepted(self, csrf_client: TestClient) -> None:
        # /api/health is in EXEMPT_PATHS; must skip the cookie/header check entirely.
        r = csrf_client.post("/api/health", headers={HEADER_NAME: "x"})
        assert r.status_code == 200


class TestToggle:
    def test_disabled_allows_mutating_call_without_token(self, disabled_client: TestClient) -> None:
        r = disabled_client.post("/echo")
        assert r.status_code == 200

    def test_disabled_does_not_set_cookie_on_get(self, disabled_client: TestClient) -> None:
        r = disabled_client.get("/echo")
        assert r.status_code == 200
        assert r.cookies.get(COOKIE_NAME) is None


class TestWebSocket:
    def test_websocket_scope_bypasses_csrf(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A websocket handshake reaches the endpoint without a cookie/header check.

        Mirrors how the live TerminalView WS connects: the middleware early-returns
        for websocket scope, so a double-submit check never fires over WS.
        """
        from starlette.routing import WebSocketRoute
        from starlette.websockets import WebSocket

        reached = {"ws": False}

        async def ws_endpoint(websocket: WebSocket) -> None:
            reached["ws"] = True
            await websocket.accept()
            await websocket.close()

        app = Starlette(
            routes=[WebSocketRoute("/ws", ws_endpoint)],
            middleware=[Middleware(CSRFMiddleware)],
        )
        monkeypatch.delenv(CSRF_TOGGLE, raising=False)
        client = TestClient(app)

        with client.websocket_connect("/ws"):
            pass  # accept happens server-side inside ws_endpoint
        assert reached["ws"] is True
