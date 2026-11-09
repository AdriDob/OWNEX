"""Connection Manager API — unified external account connections.

Single canonical surface for Level-2 external platform connections.
Reuses ``cores.identity_vault`` as the credential SSOT and exposes explicit
connection states required by OWNEX v10. Never returns secrets.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.identity_vault import get_identity_vault
from cores.opportunity.own_work_sources import SOURCE_PLATFORM_MAP

logger = logging.getLogger("ownex.api.connection_manager")

router = APIRouter(prefix="/api/connection-manager", tags=["connection-manager"])

CONNECTION_STATES = {
    "NOT_CONNECTED",
    "CONNECTING",
    "CONNECTED",
    "EXPIRED",
    "ERROR",
    "REVOKED",
    "MANUAL_SETUP",
    "UNSUPPORTED",
}

# Only mechanisms with evidence are named; everything else stays "unknown".
_AUTH_MECHANISMS: dict[str, str] = {
    "github": "api_token",
    "hackerone": "api_token",
    "bugcrowd": "api_token",
}


def _catalog_providers() -> dict[str, dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    for platform in SOURCE_PLATFORM_MAP.values():
        entry = providers.setdefault(platform, {"platform": platform, "source_count": 0})
        entry["source_count"] += 1
    for provider in get_identity_vault().SUPPORTED_PROVIDERS:
        providers.setdefault(provider, {"platform": provider, "source_count": 0})
    return providers


def _connection_state(account: dict[str, Any] | None) -> str:
    if not account:
        return "NOT_CONNECTED"
    health = str(account.get("health_status") or "unknown").lower()
    session = str(account.get("session_state") or "").lower()
    has_credentials = bool(account.get("has_credentials"))
    if session == "expired" or health == "expired":
        return "EXPIRED"
    if session == "revoked" or health == "revoked":
        return "REVOKED"
    if health == "unhealthy":
        return "ERROR"
    if has_credentials and health == "healthy":
        return "CONNECTED"
    if has_credentials:
        return "CONNECTING"
    return "MANUAL_SETUP"


def _account_payload(provider: str, account: dict[str, Any] | None, source_count: int) -> dict[str, Any]:
    state = _connection_state(account)
    auth_mechanism = _AUTH_MECHANISMS.get(provider, "unknown")
    return {
        "provider": provider,
        "state": state,
        "auth_mechanism": auth_mechanism,
        "connect_supported": state != "UNSUPPORTED",
        "source_count": source_count,
        "email": account.get("email", "") if account else "",
        "has_credentials": bool(account.get("has_credentials")) if account else False,
        "session_state": account.get("session_state") if account else None,
        "health_status": account.get("health_status") if account else None,
        "last_checked": account.get("last_checked") if account else None,
    }


@router.get("/accounts")
def list_accounts() -> dict[str, Any]:
    """List all known external platform connections with explicit states."""
    vault = get_identity_vault()
    stored = {a["provider_name"]: a for a in vault.list_accounts()}
    providers = _catalog_providers()

    accounts = [_account_payload(provider, stored.get(provider), meta.get("source_count", 0)) for provider, meta in sorted(providers.items())]
    by_state: dict[str, int] = {}
    for account in accounts:
        by_state[account["state"]] = by_state.get(account["state"], 0) + 1

    return {
        "accounts": accounts,
        "summary": {"total": len(accounts), "by_state": by_state},
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/accounts/{provider}")
def get_account(provider: str) -> dict[str, Any]:
    vault = get_identity_vault()
    account = vault.get_account(provider)
    source_count = _catalog_providers().get(provider, {}).get("source_count", 0)
    return _account_payload(provider, account, source_count)


@router.post("/accounts/{provider}/connect")
def connect_account(provider: str, data: dict[str, Any]) -> dict[str, Any]:
    """Store credentials for a provider (manual/API-token setup)."""
    email = str(data.get("email", "")).strip()
    token = str(data.get("token", ""))
    password = str(data.get("password", ""))
    metadata = data.get("metadata")

    if not provider.strip():
        raise HTTPException(status_code=400, detail="provider is required")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    vault = get_identity_vault()
    vault.store_credentials(provider.strip(), email, token, password, metadata)
    account = vault.get_account(provider.strip())
    source_count = _catalog_providers().get(provider.strip(), {}).get("source_count", 0)
    logger.info("Connection stored for provider=%s", provider)
    return _account_payload(provider.strip(), account, source_count)


@router.post("/accounts/{provider}/disconnect")
def disconnect_account(provider: str) -> dict[str, Any]:
    vault = get_identity_vault()
    vault.remove_credentials(provider)
    account = vault.get_account(provider)
    source_count = _catalog_providers().get(provider, {}).get("source_count", 0)
    return _account_payload(provider, account, source_count)


@router.get("/accounts/{provider}/status")
def account_status(provider: str) -> dict[str, Any]:
    vault = get_identity_vault()
    account = vault.get_account(provider)
    if not account:
        raise HTTPException(status_code=404, detail="No connection stored for provider")
    health = vault.check_session_health(provider)
    payload = _account_payload(provider, account, _catalog_providers().get(provider, {}).get("source_count", 0))
    payload["session_health"] = health
    return payload
