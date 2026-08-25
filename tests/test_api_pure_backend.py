"""Port 8000 = API ONLY (owner directive, 2026-08-25).

Historical incident: a long-lived ``run.py`` process from pre-1.0 code
still served the Vue dist on 127.0.0.1:8000. The packaged Tauri window
loaded the UI from that origin, producing font 404s-as-HTML,
ws://127.0.0.1:8000/api/ws failures and boot-storm 429s ("Error in api /
Rate limit exceeded").

Contract: the backend never serves frontend assets. The UI ships inside
the Tauri bundle (frontendDist) or runs via Vite dev server — never via
FastAPI.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_app_has_no_html_serving_routes() -> None:
    """Runtime truth: no Mount, no catch-all returning HTML at '/'."""
    import api.main as api_main  # noqa: PLC0415

    forbidden_types = ("Mount",)
    for route in api_main.app.routes:
        name = type(route).__name__
        path = getattr(route, "path", "")
        assert name not in forbidden_types, f"static mount detected: {path}"
        assert path not in ("/", "/{path:path}"), f"catch-all route at '{path}'"


def test_runpy_never_serves_frontend_again() -> None:
    """Source guard on the historical offender."""
    src = (REPO / "run.py").read_text(encoding="utf-8")
    assert "StaticFiles" not in src, "run.py must not mount static files"
    assert "index.html" not in src, "run.py must not serve the SPA"
    assert "frontend/dist" not in src, "run.py must not reference the dist build"
