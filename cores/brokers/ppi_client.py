"""PPI (Portfolio Personal Inversiones) REST API client — read-only sync.

Official API v1.0. Auth: headers ApiKey/ApiSecret/AuthorizedClient/ClientKey
on POST /api/{v}/Account/LoginApi -> accessToken + refreshToken.
Docs: https://itatppi.github.io/ppi-official-api-docs/
Sandbox swagger: https://clientapisbx.portfoliopersonal.com/swagger/index.html

OWNEX only implements read endpoints (accounts, balances, positions,
movements, available balance). Order/trade endpoints are never called.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger("ownex.brokers.ppi")

API_VERSION = "1.0"
# Production host follows the documented sandbox pattern (clientapisbx ->
# clientapi); overridable per-account via metadata["base_url"].
DEFAULT_BASE_URL = "https://clientapi.portfoliopersonal.com"
SANDBOX_BASE_URL = "https://clientapisbx.portfoliopersonal.com"
_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class PPIClient:
    """Thin read-only client for the PPI REST API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL) -> None:
        self._base = base_url.rstrip("/")
        self._token = ""
        self._token_exp: datetime | None = None

    def login(self, api_key: str, api_secret: str, authorized_client: str, client_key: str) -> dict[str, Any]:
        """Exchange API credentials for a session token."""
        resp = httpx.post(
            f"{self._base}/api/{API_VERSION}/Account/LoginApi",
            headers=self._cred_headers(api_key, api_secret, authorized_client, client_key),
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        body = resp.json()
        first = body[0] if isinstance(body, list) and body else body
        token = first.get("accessToken") or first.get("access_token")
        if not token:
            raise PPIAuthError("PPI login response did not include accessToken")
        self._token = str(token)
        expires = first.get("expires")
        if isinstance(expires, (int, float)) and expires > 0:
            self._token_exp = datetime.now(UTC) + timedelta(seconds=float(expires))
        return {"access_token": self._token, "refresh_token": first.get("refreshToken"), "expires": expires}

    def get_accounts(self) -> list[dict[str, Any]]:
        return self._get("/api/{v}/Account/Accounts")

    def get_balances_and_positions(self, account_number: str) -> dict[str, Any]:
        return self._get("/api/{v}/Account/BalancesAndPositions", params={"accountNumber": account_number})

    def get_available_balance(self, account_number: str) -> list[dict[str, Any]]:
        return self._get("/api/{v}/Account/AvailableBalance", params={"accountNumber": account_number})

    def get_movements(self, account_number: str, date_from: str | None = None, date_to: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {"accountNumber": account_number}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        return self._get("/api/{v}/Account/Movements", params=params)

    def _cred_headers(self, api_key: str, api_secret: str, authorized_client: str, client_key: str) -> dict[str, str]:
        return {
            "ApiKey": api_key,
            "ApiSecret": api_secret,
            "AuthorizedClient": authorized_client,
            "ClientKey": client_key,
            "Accept": "application/json",
        }

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise PPIAuthError("PPI client is not authenticated")
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = f"{self._base}{path.format(v=API_VERSION)}"
        resp = httpx.get(url, headers=self._headers(), params=params, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()


class PPIAuthError(Exception):
    """PPI rejected the credentials or returned an unexpected payload."""


def sync_ppi_account(
    api_key: str,
    api_secret: str,
    authorized_client: str,
    client_key: str,
    base_url: str | None = None,
) -> dict[str, Any]:
    """Full read-only sync: login, accounts, balances/positions, movements."""
    client = PPIClient(base_url or DEFAULT_BASE_URL)
    login_info = client.login(api_key, api_secret, authorized_client, client_key)

    accounts = client.get_accounts() or []
    snapshot: dict[str, Any] = {
        "authenticated": True,
        "login": {"expires": login_info.get("expires")},
        "accounts": accounts,
    }
    errors: dict[str, str] = {}

    per_account: list[dict[str, Any]] = []
    for acc in accounts:
        number = acc.get("accountNumber") or acc.get("account_number") or ""
        entry: dict[str, Any] = {"account_number": number, "name": acc.get("name")}
        for key, fn in (
            ("balances_and_positions", lambda n=number: client.get_balances_and_positions(n)),
            ("available_balance", lambda n=number: client.get_available_balance(n)),
            ("movements", lambda n=number: client.get_movements(n)),
        ):
            try:
                entry[key] = fn()
            except Exception as exc:
                logger.warning("PPI %s failed for %s: %s", key, number, exc)
                errors[f"{number}.{key}"] = str(exc)
        per_account.append(entry)
    snapshot["account_details"] = per_account
    if errors:
        snapshot["partial_errors"] = errors
    return snapshot
