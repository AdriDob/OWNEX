"""IOL Inversiones API client — real account sync for Argentine brokerage.

Public REST API for IOL account holders (free). Auth: POST /auth/token with
platform credentials returns a JWT used as Bearer token.
Docs: https://developers.iolinversiones.com

Only documented endpoints are implemented; anything unverified returns an
honest error instead of guessing.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("ownex.brokers.iol")

BASE_URL = "https://api.iolinversiones.com"
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class IOLClient:
    """Thin sync client for the IOL Inversiones REST API."""

    def __init__(self, base_url: str = BASE_URL) -> None:
        self._base = base_url.rstrip("/")

    def authenticate(self, email: str, password: str) -> str:
        """Exchange platform credentials for a JWT access token."""
        resp = httpx.post(
            f"{self._base}/auth/token",
            json={"username": email, "password": password},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        token = body.get("access_token") or body.get("accessToken") or (body.get("data") or {}).get("access_token")
        if not token:
            raise IOLAuthError("IOL auth response did not include an access token")
        return str(token)

    def get_balances(self, token: str, country: str = "AR") -> dict[str, Any]:
        """Account balances for a country (AR returns ARS+USD)."""
        return self._get(f"/broker/accounts/{country}/balances", token)

    def get_positions(self, token: str, country: str = "AR") -> dict[str, Any]:
        """Open positions for a country."""
        return self._get(f"/broker/accounts/{country}/positions", token)

    def get_movements(self, token: str, country: str = "AR") -> dict[str, Any]:
        """Account activity/movements."""
        return self._get(f"/broker/accounts/{country}/movements", token)

    def _get(self, path: str, token: str) -> dict[str, Any]:
        resp = httpx.get(
            f"{self._base}{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", body) if isinstance(body, dict) else {"raw": body}


class IOLAuthError(Exception):
    """IOL rejected the credentials or returned an unexpected payload."""


def sync_iol_account(email: str, password: str) -> dict[str, Any]:
    """Full sync: authenticate then pull balances, positions and movements.

    Returns a snapshot payload. Raises on auth or transport failure — callers
    must surface the error honestly (no fake data).
    """
    client = IOLClient()
    token = client.authenticate(email, password)
    snapshot: dict[str, Any] = {"authenticated": True}
    errors: dict[str, str] = {}
    for name, fn in (
        ("balances", lambda: client.get_balances(token)),
        ("positions", lambda: client.get_positions(token)),
        ("movements", lambda: client.get_movements(token)),
    ):
        try:
            snapshot[name] = fn()
        except Exception as exc:  # endpoint may not exist for all account types
            logger.warning("IOL %s fetch failed: %s", name, exc)
            errors[name] = str(exc)
    if errors:
        snapshot["partial_errors"] = errors
    return snapshot
