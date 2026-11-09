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

    def authenticate(self, email: str, password: str) -> dict[str, Any]:
        """OAuth2 password grant -> {access_token, refresh_token, expires_in, expires_at}."""
        resp = httpx.post(
            f"{self._base}/auth/token",
            json={"grant_type": "password", "username": email, "password": password},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, dict):
            data = body if isinstance(body, dict) else {}
        token = data.get("access_token") or data.get("accessToken")
        if not token:
            raise IOLAuthError("IOL auth response did not include an access token")
        return {
            "access_token": str(token),
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
            "expires_at": data.get("expires_at"),
            "token_type": data.get("token_type", "bearer"),
        }

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        """OAuth2 refresh_token grant — renew an expired access token."""
        resp = httpx.post(
            f"{self._base}/auth/token",
            json={"grant_type": "refresh_token", "refresh_token": refresh_token},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") if isinstance(body, dict) else body
        token = (data or {}).get("access_token")
        if not token:
            raise IOLAuthError("IOL refresh response did not include an access token")
        return data

    def get_balances(self, token: str, country: str = "AR") -> dict[str, Any]:
        """Account balances for a country (AR returns ARS+USD)."""
        return self._get(f"/broker/accounts/{country}/balances", token)

    def get_positions(self, token: str, country: str = "AR", valuation_currency: str | None = None) -> dict[str, Any]:
        """Open positions; valuation_currency ARS/USD/MEP/CCL for AR accounts."""
        params = {"valuation_currency": valuation_currency} if valuation_currency else None
        return self._get(f"/broker/accounts/{country}/positions", token, params=params)

    def get_movements(self, token: str, country: str = "AR") -> dict[str, Any]:
        """Account activity/movements."""
        return self._get(f"/broker/accounts/{country}/movements", token)

    def _get(self, path: str, token: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        resp = httpx.get(
            f"{self._base}{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            params=params,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", body) if isinstance(body, dict) else {"raw": body}


class IOLAuthError(Exception):
    """IOL rejected the credentials or returned an unexpected payload."""


def sync_iol_account(email: str, password: str) -> dict[str, Any]:
    """Full sync: OAuth2 password grant then pull balances, positions and movements.

    Returns a snapshot payload. Raises on auth or transport failure — callers
    must surface the error honestly (no fake data).
    """
    client = IOLClient()
    auth = client.authenticate(email, password)
    token = auth["access_token"]
    snapshot: dict[str, Any] = {
        "authenticated": True,
        "token_expires_at": auth.get("expires_at"),
        "token_expires_in": auth.get("expires_in"),
    }
    errors: dict[str, str] = {}
    for name, fn in (
        ("balances", lambda: client.get_balances(token)),
        ("positions", lambda: client.get_positions(token, valuation_currency="USD")),
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
