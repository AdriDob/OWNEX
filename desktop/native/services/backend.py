"""Backend bootstrap — in-process API server (uvicorn) on 127.0.0.1:8000.

The native shell is a thin client over the backend HTTP interface
(desktop.native.services.api_client). When the backend is not already
reachable (dev daemon via `run.py --daemon`), this module starts it
in-process as a daemon thread so the bundle is self-contained: pipeline,
scheduler and scrapers run inside the same process and the Mission Control
views consume real data over HTTP.
"""

from __future__ import annotations

import logging
import mimetypes
import os
import threading
import time
import webbrowser
from pathlib import Path

import httpx

logger = logging.getLogger("ownex.native.backend")

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
HEALTH_PATH = "/api/health"
STARTUP_TIMEOUT_S = 45.0
HEALTH_TIMEOUT_S = 1.5
NO_BROWSER_ENV = "OWNEX_NO_BROWSER"

_backend_thread: threading.Thread | None = None


def backend_alive(base_url: str = DEFAULT_BASE_URL) -> bool:
    """True when a backend responds 200 on /api/health at base_url."""
    try:
        response = httpx.get(f"{base_url}{HEALTH_PATH}", timeout=HEALTH_TIMEOUT_S)
        return response.status_code == 200
    except Exception:
        return False


def ensure_backend_running(base_url: str = DEFAULT_BASE_URL) -> bool:
    """Return True when a backend is (or became) reachable at base_url.

    Non-fatal: when the in-process server fails to boot (missing packages,
    port conflict, crashed engine), the shell keeps running and the views
    fall back to the local data layer.
    """
    global _backend_thread
    if backend_alive(base_url):
        return True
    if _backend_thread is not None and _backend_thread.is_alive():
        return backend_alive(base_url)
    _backend_thread = _start_server_thread()
    return _wait_alive(base_url, timeout=STARTUP_TIMEOUT_S)


def start_backend_async(base_url: str = DEFAULT_BASE_URL) -> None:
    """Fire-and-forget bootstrap: never blocks the UI thread."""
    threading.Thread(
        target=ensure_backend_running,
        args=(base_url,),
        name="ownex-backend-bootstrap",
        daemon=True,
    ).start()


def mount_spa(app, dist_dir: Path | None = None) -> bool:
    """Serve the Vue SPA (frontend/dist) from the in-process backend.

    Registered AFTER api routers import-time, so API routes win; the
    catch-all only serves unmatched paths (assets + index.html fallback).
    Non-fatal: without dist the shell keeps working as an API-only client.
    """
    from fastapi.responses import FileResponse, JSONResponse

    try:
        if dist_dir is None:
            from cores.platform.system import get_frontend_dist_dir

            dist_dir = get_frontend_dist_dir()
        if not dist_dir.is_dir():
            logger.warning("SPA dist not found at %s", dist_dir)
            return False
        index_path = dist_dir / "index.html"
        resolved_dist = dist_dir.resolve()
        mimetypes.add_type("application/javascript", ".js")
        mimetypes.add_type("text/css", ".css")
        mimetypes.add_type("image/svg+xml", ".svg")

        @app.get("/")
        async def serve_root():
            if index_path.is_file():
                return FileResponse(str(index_path))
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path:
                file_path = dist_dir / full_path
                if file_path.is_file() and file_path.resolve().is_relative_to(resolved_dist):
                    return FileResponse(str(file_path))
            if index_path.is_file():
                return FileResponse(str(index_path))
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        logger.info("SPA mounted from %s", dist_dir)
        return True
    except Exception as exc:
        logger.warning("SPA mount failed: %s", exc)
        return False


def open_ui_when_ready(base_url: str = DEFAULT_BASE_URL) -> bool:
    """Wait for backend health, then open the web UI in the default browser.

    Skipped when OWNEX_NO_BROWSER is set. Never raises.
    """
    if os.environ.get(NO_BROWSER_ENV):
        logger.info("browser auto-open disabled via %s", NO_BROWSER_ENV)
        return False
    if not _wait_alive(base_url, timeout=STARTUP_TIMEOUT_S):
        logger.warning("backend not healthy; browser not opened")
        return False
    url = f"{base_url}/"
    opened = webbrowser.open(url)
    logger.info("web UI %s: %s", "opened" if opened else "failed to open", url)
    return opened


def open_ui_async(base_url: str = DEFAULT_BASE_URL) -> None:
    """Fire-and-forget browser auto-open: never blocks the UI thread."""
    threading.Thread(
        target=open_ui_when_ready,
        args=(base_url,),
        name="ownex-ui-opener",
        daemon=True,
    ).start()


def _start_server_thread() -> threading.Thread:
    thread = threading.Thread(target=_serve, name="ownex-backend", daemon=True)
    thread.start()
    return thread


def _serve() -> None:
    try:
        import uvicorn

        from api.main import app

        mount_spa(app)
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="warning",
            access_log=False,
        )
        uvicorn.Server(config).run()
    except Exception as exc:
        logger.error("in-process backend failed to start: %s", exc)


def _wait_alive(base_url: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if backend_alive(base_url):
            return True
        time.sleep(1.0)
    return backend_alive(base_url)
