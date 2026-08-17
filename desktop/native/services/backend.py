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
import threading
import time

import httpx

logger = logging.getLogger("ownex.native.backend")

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
HEALTH_PATH = "/api/health"
STARTUP_TIMEOUT_S = 45.0
HEALTH_TIMEOUT_S = 1.5

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


def _start_server_thread() -> threading.Thread:
    thread = threading.Thread(target=_serve, name="ownex-backend", daemon=True)
    thread.start()
    return thread


def _serve() -> None:
    try:
        import uvicorn

        from api.main import app

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
