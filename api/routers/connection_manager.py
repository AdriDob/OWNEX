"""Connection Manager API — unified external account connections.

Single canonical surface for Level-2 external platform connections.
Reuses ``cores.identity_vault`` as the credential SSOT and exposes explicit
connection states required by OWNEX v10. Never returns secrets.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from cores.brokers.iol_client import IOLAuthError, sync_iol_account
from cores.connections.catalog import AI_TOOLS, API_SYNC_PROVIDERS, INFRA, INVESTMENT_AR, ProviderSetup
from cores.connections.snapshots import load_snapshot, save_snapshot
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
    "iol": "password_to_jwt",
}


def _explicit_catalog() -> dict[str, ProviderSetup]:
    return {**INVESTMENT_AR, **AI_TOOLS, **INFRA}


_EXPLICIT = _explicit_catalog()


def _catalog_providers() -> dict[str, dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    for platform in SOURCE_PLATFORM_MAP.values():
        entry = providers.setdefault(platform, {"platform": platform, "source_count": 0, "domain": "opportunity"})
        entry["source_count"] += 1
    for provider in get_identity_vault().SUPPORTED_PROVIDERS:
        providers.setdefault(provider, {"platform": provider, "source_count": 0, "domain": "opportunity"})
    for name, setup in _EXPLICIT.items():
        entry = providers.setdefault(name, {"platform": name, "source_count": 0})
        entry["domain"] = setup.domain
        entry["setup"] = setup
    return providers


def _setup_for(provider: str, meta: dict[str, Any]) -> ProviderSetup | None:
    setup = meta.get("setup")
    if isinstance(setup, ProviderSetup):
        return setup
    return _EXPLICIT.get(provider)


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


def _parse_sync_meta(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw
    return raw


def _account_payload(provider: str, account: dict[str, Any] | None, meta: dict[str, Any]) -> dict[str, Any]:
    state = _connection_state(account)
    auth_mechanism = _AUTH_MECHANISMS.get(provider, "unknown")
    setup = _setup_for(provider, meta)
    sync_mode = setup.sync_mode if setup else "manual_export"
    has_snapshot = load_snapshot(provider) is not None
    actions = ["connect"]
    if account and account.get("has_credentials"):
        actions.append("disconnect")
    if sync_mode != "none":
        actions.append("sync")
    return {
        "provider": provider,
        "state": state,
        "auth_mechanism": auth_mechanism,
        "connect_supported": state != "UNSUPPORTED",
        "source_count": meta.get("source_count", 0),
        "domain": meta.get("domain", "opportunity"),
        "email": account.get("email", "") if account else "",
        "has_credentials": bool(account.get("has_credentials")) if account else False,
        "session_state": account.get("session_state") if account else None,
        "health_status": account.get("health_status") if account else None,
        "last_checked": account.get("last_checked") if account else None,
        "last_sync_at": account.get("last_sync_at") if account else None,
        "last_sync_meta": _parse_sync_meta(account.get("last_sync_meta")) if account else None,
        "has_snapshot": has_snapshot,
        "actions": actions,
        "setup": setup.as_dict() if setup else None,
    }


@router.get("/accounts")
def list_accounts() -> dict[str, Any]:
    """List all known external platform connections with explicit states."""
    vault = get_identity_vault()
    stored = {a["provider_name"]: a for a in vault.list_accounts()}
    providers = _catalog_providers()

    accounts = [_account_payload(provider, stored.get(provider), meta) for provider, meta in sorted(providers.items())]
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
    meta = _catalog_providers().get(provider, {"source_count": 0, "domain": "opportunity"})
    return _account_payload(provider, account, meta)


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
    meta = _catalog_providers().get(provider.strip(), {"source_count": 0, "domain": "opportunity"})
    logger.info("Connection stored for provider=%s", provider)
    return _account_payload(provider.strip(), account, meta)


@router.post("/accounts/{provider}/disconnect")
def disconnect_account(provider: str) -> dict[str, Any]:
    vault = get_identity_vault()
    vault.remove_credentials(provider)
    account = vault.get_account(provider)
    meta = _catalog_providers().get(provider, {"source_count": 0, "domain": "opportunity"})
    return _account_payload(provider, account, meta)


@router.get("/accounts/{provider}/status")
def account_status(provider: str) -> dict[str, Any]:
    vault = get_identity_vault()
    account = vault.get_account(provider)
    if not account:
        raise HTTPException(status_code=404, detail="No connection stored for provider")
    health = vault.check_session_health(provider)
    payload = _account_payload(provider, account, _catalog_providers().get(provider, {"source_count": 0, "domain": "opportunity"}))
    payload["session_health"] = health
    return payload


@router.post("/accounts/{provider}/sync")
def sync_account(provider: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sync real data for a provider.

    - ``api`` providers with an implemented adapter (e.g. IOL) pull live data
      using stored credentials.
    - ``manual_export`` providers accept an optional ``snapshot`` payload the
      user exported from the platform; it is stored for downstream use.
    - Always stamps ``last_sync_at`` on success. Never returns secrets.
    """
    data = data or {}
    vault = get_identity_vault()
    if not vault.get_account(provider):
        raise HTTPException(status_code=404, detail="Conectá el provider antes de sincronizar")
    meta = _catalog_providers().get(provider, {"source_count": 0, "domain": "opportunity"})
    setup = _setup_for(provider, meta)
    sync_mode = setup.sync_mode if setup else "manual_export"

    if sync_mode == "none":
        raise HTTPException(status_code=400, detail="Este provider no soporta sync de datos")

    snapshot_payload: dict[str, Any] | None = data.get("snapshot")
    note = str(data.get("note", ""))[:500]
    sync_meta: dict[str, Any] = {"mode": sync_mode}

    if provider in API_SYNC_PROVIDERS:
        creds = vault.get_credentials(provider)
        email = creds.get("email") or ""
        password = creds.get("password") or ""
        if not email or not password:
            raise HTTPException(
                status_code=400,
                detail="Faltan credenciales (email + contraseña) para sincronizar por API",
            )
        try:
            live = sync_iol_account(email, password)
        except IOLAuthError as exc:
            raise HTTPException(status_code=401, detail=f"IOL rechazó las credenciales: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            status = 401 if exc.response.status_code in (401, 403) else 502
            raise HTTPException(status_code=status, detail=f"IOL respondió {exc.response.status_code}") from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Error consultando IOL: {exc}") from exc
        envelope = save_snapshot(provider, live, source="api")
        sync_meta.update({"source": "api", "keys": sorted(live.keys()), "partial_errors": live.get("partial_errors")})
    else:
        if snapshot_payload is None:
            raise HTTPException(
                status_code=400,
                detail="Este provider requiere un snapshot manual (exportá los datos desde la plataforma)",
            )
        if not isinstance(snapshot_payload, dict):
            raise HTTPException(status_code=400, detail="snapshot debe ser un objeto JSON")
        envelope = save_snapshot(provider, snapshot_payload, source="manual")
        sync_meta.update({"source": "manual", "keys": sorted(snapshot_payload.keys())})

    if note:
        sync_meta["note"] = note
    vault.record_sync(provider, sync_meta)
    vault.update_session_state(provider, "connected")
    vault.update_health(provider, "healthy")

    account = vault.get_account(provider)
    payload = _account_payload(provider, account, meta)
    payload["sync_result"] = {
        "synced_at": envelope["synced_at"],
        "source": envelope["source"],
        "snapshot_keys": sync_meta.get("keys", []),
    }
    return payload


@router.get("/accounts/{provider}/sync/latest")
def latest_snapshot(provider: str) -> dict[str, Any]:
    """Return the last synced snapshot for a provider (no secrets)."""
    snapshot = load_snapshot(provider)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No hay snapshot sincronizado para este provider")
    return snapshot
