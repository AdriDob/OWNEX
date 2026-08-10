"""Tests for the rate-limit middleware (SELF-4).

Coverage:
  - _resolve_identity: Bearer token -> sub, invalid token -> IP fallback
  - NO_LIMIT_PREFIXES bypass (health/version/docs/openapi)
  - token-bucket enforcement (burst exhaustion -> 429) with separate identity keys
  - X-RateLimit-Remaining header on success
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import Request
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from api.middleware.rate_limit_middleware import (
    NO_LIMIT_PREFIXES,
    RateLimitMiddleware,
    _resolve_identity,
)
from cores.gateway.rate_limit import TokenBucket


def _ok(request):  # type: ignore[no-untyped-def]
    return PlainTextResponse("ok")


def _app() -> Starlette:
    # Catch-all route so every exempt path + /api/data resolves to 200.
    return Starlette(
        routes=[Route("/{path:path}", _ok, methods=["GET", "POST", "HEAD", "OPTIONS"])],
        middleware=[Middleware(RateLimitMiddleware)],
    )


def _strict_bucket() -> TokenBucket:
    """rate=1, burst=2 for /api/data so the third request is rejected."""
    return TokenBucket(rate=1.0, burst=2)


@pytest.fixture(autouse=True)
def _patch_limiter():
    with patch(
        "api.middleware.rate_limit_middleware.get_rate_limiter",
        return_value=_strict_bucket(),
    ):
        yield


class TestResolveIdentity:
    def test_no_auth_returns_client_ip(self) -> None:
        request = Request(
            {
                "type": "http",
                "client": ("1.2.3.4", 5000),
                "headers": [],
            }
        )
        assert _resolve_identity(request) == "1.2.3.4"

    def test_bearer_token_returns_sub(self) -> None:
        request = Request(
            {
                "type": "http",
                "client": ("1.2.3.4", 5000),
                "headers": [(b"authorization", b"Bearer validtoken")],
            }
        )
        with patch(
            "api.middleware.rate_limit_middleware.verify_token",
            return_value={"sub": "user_42"},
        ):
            assert _resolve_identity(request) == "user_42"

    def test_invalid_token_falls_back_to_ip(self) -> None:
        request = Request(
            {
                "type": "http",
                "client": ("9.9.9.9", 5000),
                "headers": [(b"authorization", b"Bearer badtoken")],
            }
        )
        with patch(
            "api.middleware.rate_limit_middleware.verify_token",
            return_value=None,
        ):
            assert _resolve_identity(request) == "9.9.9.9"


class TestExemptPaths:
    @pytest.mark.parametrize("path", sorted(NO_LIMIT_PREFIXES))
    def test_exempt_paths_never_429(self, path: str) -> None:
        app = _app()
        client = TestClient(app)
        # Hit the exempt path many times; none should be a 429.
        for _ in range(50):
            r = client.get(path)
            assert r.status_code == 200


class TestEnforcement:
    def test_burst_then_429(self) -> None:
        client = TestClient(_app())
        # burst=2 -> 200, 200, then 429.
        assert client.get("/api/data").status_code == 200
        assert client.get("/api/data").status_code == 200
        assert client.get("/api/data").status_code == 429

    def test_remaining_header_leak_on_429(self) -> None:
        client = TestClient(_app())
        assert client.get("/api/data").status_code == 200
        assert client.get("/api/data").status_code == 200
        r3 = client.get("/api/data")
        assert r3.status_code == 429
        assert r3.headers["X-RateLimit-Remaining"] == "0"

    def test_remaining_header_on_success(self) -> None:
        client = TestClient(_app())
        r = client.get("/api/data")
        assert r.status_code == 200
        assert "X-RateLimit-Remaining" in r.headers

    def test_token_identity_isolated_per_user(self) -> None:
        client = TestClient(_app())
        hdrs = {"Authorization": "Bearer u1token"}
        with patch(
            "api.middleware.rate_limit_middleware.verify_token",
            return_value={"sub": "u1"},
        ):
            assert client.get("/api/data", headers=hdrs).status_code == 200
            assert client.get("/api/data", headers=hdrs).status_code == 200
            assert client.get("/api/data", headers=hdrs).status_code == 429  # u1 exhausted
        hdrs2 = {"Authorization": "Bearer u2token"}
        with patch(
            "api.middleware.rate_limit_middleware.verify_token",
            return_value={"sub": "u2"},
        ):
            # Fresh identity key -> bucket untouched -> 200.
            assert client.get("/api/data", headers=hdrs2).status_code == 200
