"""CORS contracts for the packaged Tauri bundle (P0 remediation, FASE 1).

The Windows bundle serves the SPA from origin ``http://tauri.localhost``
(WebView2) while the API lives on ``http://127.0.0.1:<dynamic>``. Two
contracts must hold simultaneously:

1. The packaged branch of :func:`api.main.configure_cors` must allow the
   Tauri origins WITH credentials (the frontend sends
   ``credentials: 'include'`` on every call — see ``lib/api.ts``).
2. ``AuthMiddleware`` must let browser preflights (OPTIONS) reach the
   CORSMiddleware instead of answering 401 first — preflight requests
   never carry an Authorization header by spec.

Regression guard: the health probe used to succeed without credentials
while every authenticated call was blocked, producing a false "READY".
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

TAURI_ORIGIN_HTTPS = "https://tauri.localhost"
TAURI_ORIGIN_HTTP = "http://tauri.localhost"
TAURI_ORIGIN_SCHEME = "tauri://localhost"


# ---------------------------------------------------------------------------
# Contract 1 — packaged/desktop branch allows Tauri origins with credentials
# ---------------------------------------------------------------------------


@pytest.fixture()
def desktop_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[FastAPI]:
    """Fresh app wired through the REAL configure_cors with desktop=True."""
    from api import main as api_main
    from cores.env import config as env_config

    monkeypatch.setattr(env_config, "_CONFIG_INSTANCE", None)
    monkeypatch.setenv("OWNEX_DESKTOP", "1")
    cfg = env_config.get_config()
    assert cfg.desktop is True, "OWNEX_DESKTOP=1 must force desktop config"

    app = FastAPI()

    @app.get("/api/health")
    def _health() -> dict[str, str]:  # pragma: no cover - trivial
        return {"status": "ok"}

    @app.post("/api/echo")
    def _echo() -> dict[str, bool]:  # pragma: no cover - trivial
        return {"ok": True}

    api_main.configure_cors(app)
    yield app
    monkeypatch.setattr(env_config, "_CONFIG_INSTANCE", None)
    monkeypatch.delenv("OWNEX_DESKTOP", raising=False)


class TestDesktopCorsContract:
    @pytest.mark.parametrize("origin", [TAURI_ORIGIN_HTTP, TAURI_ORIGIN_HTTPS, TAURI_ORIGIN_SCHEME])
    def test_preflight_allowed_with_credentials(self, desktop_app: FastAPI, origin: str) -> None:
        client = TestClient(desktop_app)
        res = client.options(
            "/api/echo",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert res.status_code == 200, res.text
        # Echo the exact origin — wildcard '*' is invalid with credentials.
        assert res.headers.get("access-control-allow-origin") == origin
        assert res.headers.get("access-control-allow-credentials") == "true"
        requested = res.headers.get("access-control-allow-headers", "").lower()
        assert "authorization" in requested
        assert "content-type" in requested

    def test_get_echoes_origin_and_allows_credentials(self, desktop_app: FastAPI) -> None:
        client = TestClient(desktop_app)
        res = client.get("/api/health", headers={"Origin": TAURI_ORIGIN_HTTP})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == TAURI_ORIGIN_HTTP
        assert res.headers.get("access-control-allow-credentials") == "true"

    def test_unknown_origin_not_reflected(self, desktop_app: FastAPI) -> None:
        client = TestClient(desktop_app)
        res = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert res.headers.get("access-control-allow-origin") != "https://evil.example"


def test_dev_branch_keeps_wildcard_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dev/server mode stays permissive-but-credentialless (documented behavior)."""
    from api import main as api_main
    from cores.env import config as env_config

    monkeypatch.setattr(env_config, "_CONFIG_INSTANCE", None)
    monkeypatch.delenv("OWNEX_DESKTOP", raising=False)
    monkeypatch.delenv("CATEYE_DESKTOP", raising=False)
    assert env_config.get_config().desktop is False

    client = TestClient(api_main.app)
    res = client.get("/api/health", headers={"Origin": TAURI_ORIGIN_HTTP})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "*"
    assert "access-control-allow-credentials" not in res.headers
    monkeypatch.setattr(env_config, "_CONFIG_INSTANCE", None)


# ---------------------------------------------------------------------------
# Contract 2 — preflight OPTIONS must bypass auth (401 would kill CORS)
# ---------------------------------------------------------------------------


class TestPreflightBypassesAuth:
    def test_auth_middleware_passes_options_through(self) -> None:
        """OPTIONS reaches call_next even unauthenticated on a protected path."""
        from api.middleware.auth_middleware import AuthMiddleware

        reached: list[str] = []

        async def call_next(request):  # type: ignore[no-untyped-def]
            reached.append(request.method)
            from starlette.responses import PlainTextResponse

            return PlainTextResponse("ok")

        middleware = AuthMiddleware(app=None)  # type: ignore[arg-type]

        import asyncio

        from starlette.requests import Request

        scope = {
            "type": "http",
            "method": "OPTIONS",
            "path": "/api/targets",
            "headers": [(b"origin", TAURI_ORIGIN_HTTP.encode())],
            "query_string": b"",
        }
        response = asyncio.run(middleware.dispatch(Request(scope), call_next))
        assert reached == ["OPTIONS"], "preflight must reach inner middlewares/CORS"
        assert response.status_code == 200

    def test_sidecar_launcher_forces_desktop_flag(self) -> None:
        """start_backend.py must set OWNEX_DESKTOP so the restrictive branch engages."""
        entry = (
            __import__("pathlib").Path(__file__).resolve().parent.parent / "src-tauri" / "binaries" / "start_backend.py"
        )
        source = entry.read_text(encoding="utf-8")
        assert 'os.environ["OWNEX_DESKTOP"]' in source, (
            "sidecar launcher must force OWNEX_DESKTOP so packaged CORS branch (Tauri origins + credentials) is active"
        )

    def test_configure_cors_is_single_source(self) -> None:
        """api.main wires CORS exclusively through configure_cors."""
        from pathlib import Path

        main_source = (Path(__file__).parent.parent / "api" / "main.py").read_text(encoding="utf-8")
        assert "configure_cors(app)" in main_source
        # Exactly one wiring site: module import + the call inside
        # configure_cors(). Any extra occurrence means duplicated CORS config.
        assert main_source.count("CORSMiddleware") == 2, "CORS must be wired only inside configure_cors()"
