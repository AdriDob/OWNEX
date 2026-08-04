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
            "/api/execution/tracker",
            "/api/stats",
        ]
        for path in protected:
            resp = client.get(path)
            assert resp.status_code == 401, f"{path} should require auth, got {resp.status_code}"

    def test_system_health_is_public(self, client):
        """Health endpoints are public by design (monitoring without auth)."""
        resp = client.get("/api/system/health")
        assert resp.status_code != 401, "Health endpoint must stay publicly reachable"

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
    """CSRF middleware tests — tested via TestClient against the real app.

    CSRF must be tested with an authenticated client because AuthMiddleware
    (registered before CSRFMiddleware) rejects unauthenticated requests before
    the CSRF middleware can process them.  All state-changing GET/POST requests
    go through an authed_client that has a valid session token.
    """

    @pytest.fixture
    def csrf_env(self, monkeypatch):
        """Enable CSRF for this test class (conftest disables it globally)."""
        monkeypatch.delenv("CATEYE_CSRF_DISABLED", raising=False)
        monkeypatch.setenv("CATEYE_DESKTOP", "1")

    @pytest.fixture
    def live_client(self, csrf_env):
        """Fresh TestClient (per-test, no cookie bleed between tests)."""
        from fastapi.testclient import TestClient

        from api.main import app
        from cores.license.validator import generate_license

        c = TestClient(app)
        lic = generate_license(expiry_days=365)
        c.post("/api/license/activate", json={"key": lic})
        return c

    @pytest.fixture
    def authed_client(self, live_client):
        """Authenticated test client with a valid session token."""
        resp = live_client.post("/api/auth/login", json={"device_id": "csrf-test"})
        assert resp.status_code == 200
        token = resp.json()["data"]["token"]
        live_client.headers = {"Authorization": f"Bearer {token}"}
        return live_client

    def test_csrf_cookie_set_on_get(self, authed_client):
        """GET request should set csrf-token cookie."""
        resp = authed_client.get("/api/targets")
        set_cookie = resp.headers.get("set-cookie", "")
        assert "csrf-token" in set_cookie, f"Expected csrf-token in set-cookie, got: {set_cookie}"

    def test_csrf_blocked_missing_header(self, authed_client):
        """POST without X-CSRF-Token header should be blocked."""
        # First GET to obtain CSRF cookie
        resp = authed_client.get("/api/targets")
        # Clear the auto-stored cookie so the POST has no CSRF header
        authed_client.cookies.clear()
        resp = authed_client.post("/api/targets", json={})
        assert resp.status_code == 403
        assert "CSRF" in resp.text

    def test_csrf_valid_token_passes(self, authed_client):
        """POST with matching cookie + header should pass CSRF."""
        # Get CSRF token from a GET
        resp = authed_client.get("/api/targets")
        import re

        match = re.search(r"csrf-token=([^;]+)", resp.headers.get("set-cookie", ""))
        assert match, "No CSRF cookie in set-cookie"
        token = match.group(1)

        # POST with matching cookie + header (TestClient auto-sends stored cookies)
        resp = authed_client.post(
            "/api/targets",
            json={"name": "test", "domain": "test.com", "program": "test"},
            headers={"X-CSRF-Token": token},
        )
        # 422 = validation error (CSRF passed, reached endpoint handler)
        assert resp.status_code in (200, 422, 400), f"Expected CSRF to pass, got {resp.status_code}"

    def test_csrf_token_mismatch_blocked(self, authed_client):
        """POST with mismatched cookie and header should be blocked."""
        resp = authed_client.get("/api/targets")
        import re

        match = re.search(r"csrf-token=([^;]+)", resp.headers.get("set-cookie", ""))
        assert match, "No CSRF cookie in set-cookie"
        token = match.group(1)

        different = "x" * 64
        # Clear auto-stored cookies so we can override
        authed_client.cookies.clear()
        resp = authed_client.post(
            "/api/targets",
            json={},
            cookies={"csrf-token": token},
            headers={"X-CSRF-Token": different},
        )
        assert resp.status_code == 403
        assert "CSRF" in resp.text

    def test_csrf_exempt_paths_skip_check(self, live_client):
        """Exempt paths should skip CSRF check entirely."""
        resp = live_client.post("/api/auth/login", json={"device_id": "test"})
        assert resp.status_code == 200

    def test_csrf_safe_methods_skip_check(self, authed_client):
        """Safe methods (OPTIONS) should skip CSRF check."""
        resp = authed_client.options("/api/targets")
        assert resp.status_code != 403

    def test_csrf_put_method_blocked(self, authed_client):
        """PUT without X-CSRF-Token should be blocked."""
        resp = authed_client.get("/api/targets")
        authed_client.cookies.clear()
        resp = authed_client.put("/api/targets", json={})
        assert resp.status_code == 403
        assert "CSRF" in resp.text

    def test_csrf_delete_method_blocked(self, authed_client):
        """DELETE without X-CSRF-Token should be blocked."""
        resp = authed_client.get("/api/targets")
        authed_client.cookies.clear()
        resp = authed_client.delete("/api/targets")
        assert resp.status_code == 403
        assert "CSRF" in resp.text

    def test_csrf_patch_method_blocked(self, authed_client):
        """PATCH without X-CSRF-Token should be blocked."""
        resp = authed_client.get("/api/targets")
        authed_client.cookies.clear()
        resp = authed_client.patch("/api/targets", json={})
        assert resp.status_code == 403
        assert "CSRF" in resp.text

    def test_csrf_disabled_env_var(self, csrf_env, monkeypatch, live_client):
        """CATEYE_CSRF_DISABLED bypasses CSRF check entirely."""
        monkeypatch.setenv("CATEYE_CSRF_DISABLED", "1")
        resp = live_client.post("/api/auth/login", json={"device_id": "test"})
        assert resp.status_code == 200

    def test_csrf_cookie_not_reset_on_second_get(self, authed_client):
        """Second GET should not set a new csrf-token cookie."""
        resp1 = authed_client.get("/api/targets")
        cookie1 = resp1.headers.get("set-cookie", "")
        assert "csrf-token" in cookie1
        resp2 = authed_client.get("/api/targets")
        cookie2 = resp2.headers.get("set-cookie", "")
        # The token should not change — second GET has no Set-Cookie
        assert "csrf-token" not in cookie2 or cookie2 == cookie1

    def test_csrf_empty_cookie_blocked(self, authed_client):
        """Empty csrf cookie with header should be blocked."""
        resp = authed_client.get("/api/targets")
        import re

        match = re.search(r"csrf-token=([^;]+)", resp.headers.get("set-cookie", ""))
        assert match, "No CSRF cookie in set-cookie"
        token = match.group(1)
        # Override cookie with empty value
        authed_client.cookies.clear()
        resp = authed_client.post(
            "/api/targets",
            json={},
            cookies={"csrf-token": ""},
            headers={"X-CSRF-Token": token},
        )
        assert resp.status_code == 403
        assert "CSRF" in resp.text


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

    def test_rate_limit_decrements_on_multiple_requests(self, client):
        """X-RateLimit-Remaining should decrease after consecutive requests."""
        token = _login(client)
        headers = {"Authorization": f"Bearer {token}"}
        r1 = client.get("/api/system/health", headers=headers)
        r2 = client.get("/api/system/health", headers=headers)
        remaining1 = int(r1.headers.get("X-RateLimit-Remaining", 0))
        remaining2 = int(r2.headers.get("X-RateLimit-Remaining", 0))
        assert remaining2 <= remaining1, "Remaining should not increase between requests"

    def test_rate_limit_public_path_not_limited(self, client):
        """Public paths (health, version, docs) should not get rate-limited."""
        resp = client.get("/api/health")
        assert "X-RateLimit-Remaining" not in resp.headers

        resp = client.get("/api/version")
        assert "X-RateLimit-Remaining" not in resp.headers

    def test_rate_limit_exempt_paths_skip_limit(self, client):
        """Paths in NO_LIMIT_PREFIXES should not have rate limit headers."""
        from api.middleware.rate_limit_middleware import NO_LIMIT_PREFIXES

        for prefix in NO_LIMIT_PREFIXES:
            resp = client.get(prefix)
            assert "X-RateLimit-Remaining" not in resp.headers, f"{prefix} should not be limited"
