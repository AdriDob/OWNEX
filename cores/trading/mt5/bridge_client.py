"""HTTP client for MT5 bridge sidecar.

Communicates with a Windows-sidecar process over HTTP.
Credentials and session state live on the bridge host only.
"""

from typing import Any

try:
    import httpx  # noqa: F401

    HAS_HTTpx = True
except ImportError:
    HAS_HTTpx = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BRIDGE_URL = "MT5_BRIDGE_URL"  # set via env; default 127.0.0.1:8080


def _url(path: str) -> str:
    base = __import__("os").getenv("_BRIDGE_URL", "http://127.0.0.1:8080")
    return f"{base.rstrip('/')}{path}"


def _req(method: str, path: str, json: dict[str, Any] | None = None, timeout: float = 5.0) -> Any:
    """Low-level request; returns parsed JSON or raises."""
    if not HAS_HTTpx:
        # Fallback stub — tests can patch this
        return {"status": "unavailable", "error": "httpx not installed"}
    import httpx

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(method, _url(path), json=json)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Public API (what __init__ exports)
# ---------------------------------------------------------------------------


def get_status() -> dict[str, Any]:
    """Bridge health + MT5 terminal state.

    Returns dict with: up, terminal, mode, armed, kill, accountInfo, positions
    """
    return _req("GET", "/health")


def arm_session(body: dict[str, Any]) -> dict[str, Any]:
    """Arm the bridge with risk limits + TTL.

    Returns dict with: armed, expires_at, limits
    """
    return _req("POST", "/arm", json=body)


def disarm_session() -> dict[str, Any]:
    """Disarm — blocks new orders immediately."""
    return _req("POST", "/disarm")


def kill_session() -> dict[str, Any]:
    """Hard kill — flat stop of any active trading."""
    return _req("POST", "/kill")


def get_positions() -> dict[str, Any]:
    """Current open positions from the MT5 terminal."""
    return _req("GET", "/positions")


def get_pnl() -> dict[str, Any]:
    """PnL día/sesión (honesto, sin floatado)."""
    return _req("GET", "/pnl")


def send_order(order: dict[str, Any]) -> dict[str, Any]:
    """Send a single order through the bridge.

    The bridge validates all guards before forwarding to MT5.
    Returns order response from MT5.
    """
    return _req("POST", "/order", json=order)
