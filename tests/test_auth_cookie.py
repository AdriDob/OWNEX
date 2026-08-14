"""Tests for the httpOnly session cookie migration (FASE 3).

Verifies that auth endpoints set the ownex-session httpOnly cookie, the
AuthMiddleware accepts the cookie as a fallback to Authorization: Bearer,
and logout clears it — without breaking the existing Bearer flow.
"""

from __future__ import annotations

import pytest

from api.middleware.auth_middleware import SESSION_COOKIE


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from api.main import app
    from cores.license.validator import generate_license

    c = TestClient(app)
    lic = generate_license(expiry_days=365)
    c.post("/api/license/activate", json={"key": lic})
    return c


@pytest.fixture(autouse=True)
def clean_state(client, monkeypatch):
    """Force local-first auth (no SMTP) and isolate per-test state."""
    monkeypatch.setattr("api.routers.auth_users.mail_configured", lambda: False)
    client.cookies.clear()
    yield
    from database.db import SessionLocal
    from database.models import User

    session = SessionLocal()
    try:
        session.query(User).filter(User.username.like("cookieuser%")).delete()
        session.commit()
    finally:
        session.close()
        client.cookies.clear()


def _register(client, username: str = "cookieuser1"):
    resp = client.post(
        "/api/auth/users/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "strongpass123",
        },
    )
    assert resp.status_code == 201
    return resp


class TestSessionCookie:
    def test_register_sets_httponly_cookie(self, client):
        resp = _register(client)
        assert SESSION_COOKIE in resp.cookies
        cookie = resp.cookies.get(SESSION_COOKIE)
        assert cookie, "cookie value must be present"

        set_cookie_headers = [h for h in resp.headers.get_list("set-cookie")]
        assert any(SESSION_COOKIE in h for h in set_cookie_headers)
        cookie_header = next(h for h in set_cookie_headers if SESSION_COOKIE in h)
        assert "HttpOnly" in cookie_header
        assert "SameSite=lax" in cookie_header
        assert cookie == resp.json()["access_token"]

    def test_login_sets_cookie(self, client):
        _register(client)
        resp = client.post(
            "/api/auth/users/login",
            json={"username": "cookieuser1", "password": "strongpass123"},
        )
        assert resp.status_code == 200
        assert SESSION_COOKIE in resp.cookies
        assert resp.cookies.get(SESSION_COOKIE) == resp.json()["access_token"]

    def test_device_login_sets_cookie(self, client):
        resp = client.post("/api/auth/login", json={"device_id": "cookie-device-1"})
        assert resp.status_code == 200
        data = resp.json()
        assert SESSION_COOKIE in resp.cookies
        assert resp.cookies.get(SESSION_COOKIE) == data["data"]["token"]

    def test_auth_via_cookie_alone(self, client):
        """A request with only the cookie (no Authorization header) is authenticated."""
        _register(client)
        token = client.cookies.get(SESSION_COOKIE)
        assert token

        me = client.get("/api/auth/users/me")
        assert me.status_code == 200
        assert me.json()["username"] == "cookieuser1"

    def test_auth_via_bearer_still_works(self, client):
        """Backwards compatibility: the Bearer flow is untouched."""
        resp = _register(client)
        token = resp.json()["access_token"]

        me = client.get("/api/auth/users/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["username"] == "cookieuser1"

    def test_401_without_token_or_cookie(self, client):
        resp = client.get("/api/auth/users/me")
        assert resp.status_code == 401

    def test_401_with_invalid_cookie(self, client):
        client.cookies.set(SESSION_COOKIE, "not-a-valid-token")
        resp = client.get("/api/auth/users/me")
        assert resp.status_code == 401

    def test_logout_clears_cookie(self, client):
        _register(client)
        token = client.cookies.get(SESSION_COOKIE)
        assert token

        logout = client.post("/api/auth/users/logout")
        assert logout.status_code == 200
        assert client.cookies.get(SESSION_COOKIE) in (None, "")

        me = client.get("/api/auth/users/me")
        assert me.status_code == 401

    def test_device_logout_without_body(self, client):
        """clearSession() sends POST /api/auth/logout with no body — must not 500."""
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200

    def test_middleware_rejects_unauthorized_api_path(self, client):
        resp = client.get("/api/version", cookies={SESSION_COOKIE: "invalid"})
        # /api/version is public; pick a protected path to assert 401
        resp = client.get("/api/activity", cookies={SESSION_COOKIE: "invalid"})
        assert resp.status_code == 401
