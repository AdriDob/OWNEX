"""Tests for auth middleware and rate limiting."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from api.main import app
    from cores.license.validator import generate_license
    c = TestClient(app)
    # Activate license
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    return c


@pytest.fixture(autouse=True)
def reset_limiter():
    from cores.gateway.rate_limit import reset_rate_limiter
    reset_rate_limiter()


def _login(c, device_id: str = "test-device") -> str:
    resp = c.post("/api/auth/login", json={"device_id": device_id})
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


class TestAuthMiddleware:
    def test_public_health_no_auth(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_public_auth_login_no_auth(self, client):
        resp = client.post("/api/auth/login", json={"device_id": "test"})
        assert resp.status_code == 200

    def test_protected_no_token_returns_401(self, client):
        resp = client.get("/api/targets")
        assert resp.status_code == 401

    def test_protected_invalid_token_returns_401(self, client):
        resp = client.get("/api/targets", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_protected_valid_token_succeeds(self, client):
        token = _login(client)
        resp = client.get("/api/targets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_protected_expired_token_returns_401(self, client):
        resp = client.get("/api/targets", headers={"Authorization": "Bearer eyJleHAiOjB9.signature"})
        assert resp.status_code == 401

    def test_all_routers_require_auth(self, client):
        protected = [
            "/api/targets",
            "/api/endpoints",
            "/api/findings",
            "/api/evidence",
            "/api/opportunities",
            "/api/overview",
            "/api/system/health",
            "/api/execution/tracker",
            "/api/stats",
        ]
        for path in protected:
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should require auth, got {resp.status_code}"

    def test_missing_auth_header_format(self, client):
        resp = client.get("/api/targets", headers={"Authorization": "NotBearer something"})
        assert resp.status_code == 401

    # ── Desktop auth hardening: frontend assets must never require auth ──

    def test_frontend_root_does_not_require_auth(self, client):
        """The SPA entry point (/) must load without auth."""
        resp = client.get("/")
        assert resp.status_code != 401, "SPA root must not return 401"

    def test_frontend_assets_do_not_require_auth(self, client):
        """Static assets like /assets/* must load without auth."""
        resp = client.get("/assets/some-file.js")
        assert resp.status_code != 401, "Static assets must not return 401"

    def test_spa_routes_do_not_require_auth(self, client):
        """SPA routes like /daily, /settings must not 401."""
        for route in ("/daily", "/settings", "/intelligence", "/radar"):
            resp = client.get(route)
            assert resp.status_code != 401, f"SPA route {route} must not return 401"

    def test_favicon_does_not_require_auth(self, client):
        resp = client.get("/favicon.ico")
        assert resp.status_code != 401

    # ── Desktop session auto-creation ──

    def test_desktop_session_creation(self):
        """The _create_desktop_session function must produce a valid token."""
        from fastapi.testclient import TestClient

        from api.main import app
        from desktop.main_desktop import _create_desktop_session
        from desktop.settings import get_settings

        settings = get_settings()
        # Save the token if any (singleton may have one from other tests)
        old_token = settings.get("session_token")
        settings.set("session_token", None)
        _create_desktop_session(8000)
        token = settings.get("session_token")
        assert token is not None, "desktop session must create a token"
        # Restore old token
        if old_token:
            settings.set("session_token", old_token)

        # The token must work against private API
        c = TestClient(app)
        resp = c.get("/api/targets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, f"desktop token must authenticate, got {resp.status_code}"

    def test_desktop_session_not_expired(self):
        """Freshly created session must not be expired."""
        from fastapi.testclient import TestClient

        from api.main import app
        from desktop.main_desktop import _create_desktop_session
        from desktop.settings import get_settings

        settings = get_settings()
        old_token = settings.get("session_token")
        settings.set("session_token", None)
        _create_desktop_session(8000)
        token = settings.get("session_token")
        if old_token:
            settings.set("session_token", old_token)
        c = TestClient(app)
        resp = c.get("/api/targets", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_invalid_paths_still_404_not_401(self, client):
        """Unknown non-API paths should 404, not 401."""
        for path in ("/nonexistent", "/images/missing.png"):
            resp = client.get(path)
            assert resp.status_code != 401, f"{path} must not return 401 (got {resp.status_code})"

    def test_all_api_routes_still_require_auth(self, client):
        """Every /api/* endpoint (except public) must require auth."""
        protected = [
            "/api/targets",
            "/api/endpoints",
            "/api/findings",
            "/api/evidence",
            "/api/opportunities",
            "/api/overview",
            "/api/system/health",
            "/api/execution/tracker",
            "/api/stats",
            "/api/daily/briefing",
            "/api/operations/tasks",
            "/api/assistant/insights",
        ]
        for path in protected:
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should require auth, got {resp.status_code}"

    def test_static_file_paths_under_api_still_protected(self, client):
        """Even non-existent /api sub-paths must require auth (no info leak)."""
        resp = client.get("/api/secrets")
        assert resp.status_code != 200, "/api/secrets must not be accessible without auth"


class TestCSRF:
    """CSRF middleware tests — dispatch tested directly."""

    @pytest.fixture(autouse=True)
    def _csrf_env(self, monkeypatch):
        monkeypatch.setenv("CATEYE_DESKTOP", "1")

    def _make_request(self, method: str = "GET", path: str = "/test",
                      cookie: str | None = None, header: str | None = None) -> Request:
        from starlette.requests import Request
        headers = []
        if cookie:
            headers.append((b"cookie", f"csrf-token={cookie}".encode()))
        if header:
            headers.append((b"x-csrf-token", header.encode()))
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers,
            "query_string": b"",
            "scheme": "http",
            "client": ("127.0.0.1", 8000),
            "server": ("test", 8000),
            "root_path": "",
            "asgi": {"version": "3.0"},
        }
        return Request(scope)

    @pytest.mark.asyncio
    async def test_csrf_cookie_set_on_get(self):
        from starlette.responses import Response

        from api.middleware.csrf_middleware import COOKIE_NAME, CSRFMiddleware

        mw = CSRFMiddleware(app=None)
        request = self._make_request("GET", "/test")

        async def call_next(r):
            return Response("ok")

        response = await mw.dispatch(request, call_next)
        cookie_header = response.headers.get("set-cookie", "")
        assert COOKIE_NAME in cookie_header

    @pytest.mark.asyncio
    async def test_csrf_blocked_missing_header(self):
        import secrets

        from starlette.responses import Response

        from api.middleware.csrf_middleware import CSRFMiddleware

        mw = CSRFMiddleware(app=None)
        token = secrets.token_hex(32)
        request = self._make_request("POST", "/test", cookie=token)

        async def call_next(r):
            return Response("ok")

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_csrf_valid_token_passes(self):
        import secrets

        from starlette.responses import Response

        from api.middleware.csrf_middleware import CSRFMiddleware

        mw = CSRFMiddleware(app=None)
        token = secrets.token_hex(32)
        request = self._make_request("POST", "/test", cookie=token, header=token)

        async def call_next(r):
            return Response("ok")

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_csrf_token_mismatch_blocked(self):
        from starlette.responses import Response

        from api.middleware.csrf_middleware import CSRFMiddleware

        mw = CSRFMiddleware(app=None)
        request = self._make_request("POST", "/test", cookie="valid-token", header="different-token")

        async def call_next(r):
            return Response("ok")

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_csrf_exempt_paths_skip_check(self):
        from api.middleware.csrf_middleware import CSRFMiddleware

        mw = CSRFMiddleware(app=None)
        request = self._make_request("POST", "/api/health")

        async def call_next(r):
            from starlette.responses import Response
            return Response("ok")

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_csrf_safe_methods_skip_check(self):
        from starlette.responses import Response

        from api.middleware.csrf_middleware import CSRFMiddleware

        mw = CSRFMiddleware(app=None)
        request = self._make_request("OPTIONS", "/test")

        async def call_next(r):
            return Response("ok")

        response = await mw.dispatch(request, call_next)
        assert response.status_code == 200


class TestRateLimit:
    def test_rate_limiter_exhaustion(self):
        from cores.gateway.rate_limit import TokenBucket
        bucket = TokenBucket(rate=1000.0, burst=10)
        for _ in range(10):
            assert bucket.consume("test")
        assert not bucket.consume("test")
        assert bucket.remaining("test") < 1

    def test_rate_limiter_refill(self):
        import time

        from cores.gateway.rate_limit import TokenBucket
        bucket = TokenBucket(rate=10.0, burst=5)
        for _ in range(5):
            bucket.consume("test")
        assert not bucket.consume("test")
        time.sleep(0.6)
        assert bucket.consume("test")

    def test_rate_limiter_remaining(self):
        from cores.gateway.rate_limit import TokenBucket
        bucket = TokenBucket(rate=1000.0, burst=5)
        for _ in range(3):
            bucket.consume("test")
        remaining = bucket.remaining("test")
        assert 1.0 <= remaining <= 5.0

    def test_rate_limiter_reset(self):
        from cores.gateway.rate_limit import TokenBucket
        bucket = TokenBucket(rate=1000.0, burst=10)
        for _ in range(10):
            bucket.consume("test")
        assert not bucket.consume("test")
        bucket.reset("test")
        assert bucket.consume("test")

    def test_rate_limiter_multiple_keys(self):
        from cores.gateway.rate_limit import TokenBucket
        bucket = TokenBucket(rate=1000.0, burst=5)
        for _ in range(5):
            bucket.consume("a")
            bucket.consume("b")
        assert not bucket.consume("a")
        assert not bucket.consume("b")

    def test_rate_limiter_custom_rules(self):
        from cores.gateway.rate_limit import TokenBucket
        bucket = TokenBucket(rate=1.0, burst=5)
        bucket.add_rule(r"/api/auth/login", rate=1000.0, burst=3)
        for _ in range(3):
            assert bucket.consume("/api/auth/login:user")
        assert not bucket.consume("/api/auth/login:user")

    def test_rate_limit_headers_on_health(self, client):
        resp = client.get("/api/health")
        assert "X-RateLimit-Remaining" not in resp.headers

    def test_normal_request_has_remaining_header(self, client):
        token = _login(client)
        resp = client.get("/api/system/health", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "X-RateLimit-Remaining" in resp.headers
