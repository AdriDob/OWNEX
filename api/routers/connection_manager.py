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
from fastapi import APIRouter, File, HTTPException, UploadFile

from cores.brokers.binance_client import BinanceReadOnlyError, sync_binance_account
from cores.brokers.iol_client import IOLAuthError, sync_iol_account
from cores.brokers.ppi_client import PPIAuthError, sync_ppi_account
from cores.connections import financial_normalizer, importer
from cores.connections.catalog import AI_TOOLS, API_SYNC_PROVIDERS, INFRA, INVESTMENT_AR, ProviderSetup
from cores.connections.snapshots import load_snapshot, save_snapshot
from cores.connections.sync_history import get_history, record_event
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
    "ppi": "api_key_headers",
    "binance": "api_key_secret",
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
        meta_extra = creds
        if provider == "iol":
            email = creds.get("email") or ""
            password = creds.get("password") or ""
            if not email or not password:
                raise HTTPException(
                    status_code=400,
                    detail="Faltan credenciales (email + contraseña) para sincronizar por API",
                )
            refresh_token = ""
            if hasattr(vault, "get_secret"):
                refresh_token = vault.get_secret(provider, "refresh_token") or ""
            try:
                live = sync_iol_account(email, password, refresh_token=refresh_token or None)
            except IOLAuthError as exc:
                raise HTTPException(status_code=401, detail=f"IOL rechazó las credenciales: {exc}") from exc
            except httpx.HTTPStatusError as exc:
                status = 401 if exc.response.status_code in (401, 403) else 502
                raise HTTPException(status_code=status, detail=f"IOL respondió {exc.response.status_code}") from exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Error consultando IOL: {exc}") from exc
        elif provider == "ppi":
            api_key = creds.get("token") or ""
            api_secret = creds.get("password") or ""
            authorized_client = str(meta_extra.get("authorized_client") or "")
            client_key = str(meta_extra.get("client_key") or "")
            base_url = str(meta_extra.get("base_url") or "") or None
            if not all([api_key, api_secret, authorized_client, client_key]):
                raise HTTPException(
                    status_code=400,
                    detail="Faltan credenciales PPI (ApiKey, ApiSecret, AuthorizedClient, ClientKey)",
                )
            try:
                live = sync_ppi_account(api_key, api_secret, authorized_client, client_key, base_url)
            except PPIAuthError as exc:
                raise HTTPException(status_code=401, detail=f"PPI rechazó las credenciales: {exc}") from exc
            except httpx.HTTPStatusError as exc:
                status = 401 if exc.response.status_code in (401, 403) else 502
                raise HTTPException(status_code=status, detail=f"PPI respondió {exc.response.status_code}") from exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Error consultando PPI: {exc}") from exc
        elif provider == "binance":
            api_key = creds.get("token") or ""
            api_secret = creds.get("password") or ""
            if not api_key or not api_secret:
                raise HTTPException(
                    status_code=400,
                    detail="Faltan credenciales Binance (API Key + Secret, solo lectura)",
                )
            try:
                live = sync_binance_account(api_key, api_secret)
            except BinanceReadOnlyError as exc:
                raise HTTPException(status_code=401, detail=f"Binance rechazó la consulta: {exc}") from exc
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Error consultando Binance: {exc}") from exc
        else:  # pragma: no cover - API_SYNC_PROVIDERS guard
            raise HTTPException(status_code=400, detail="Sync por API no implementado para este provider")

        # Persist rotated OAuth secrets securely; never let them reach snapshots
        auth_blob = live.pop("_auth", None) if isinstance(live, dict) else None
        if auth_blob and hasattr(vault, "set_secret"):
            new_rt = auth_blob.get("refresh_token")
            if new_rt:
                vault.set_secret(provider, "refresh_token", str(new_rt))
        envelope = save_snapshot(provider, live, source="api")
        sync_meta.update({"source": "api", "keys": sorted(live.keys()), "partial_errors": live.get("partial_errors")})
        try:
            financial_normalizer.normalize_provider(provider, live)
        except Exception:
            logger.warning("Normalization failed for %s", provider, exc_info=True)
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
        try:
            financial_normalizer.normalize_provider(provider, snapshot_payload)
        except Exception:
            logger.warning("Normalization failed for %s", provider, exc_info=True)

    if note:
        sync_meta["note"] = note
    vault.record_sync(provider, sync_meta)
    vault.update_session_state(provider, "connected")
    vault.update_health(provider, "healthy")
    record_event(
        provider,
        {
            "kind": "sync",
            "mode": sync_mode,
            "source": sync_meta.get("source", sync_mode),
            "synced_at": envelope["synced_at"],
            "partial_errors": sync_meta.get("partial_errors"),
        },
    )

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


@router.get("/accounts/{provider}/sync/history")
def sync_history(provider: str, limit: int = 50) -> dict[str, Any]:
    """Return recent sync/import events for a provider (no secrets)."""
    return {"provider": provider, "events": get_history(provider, limit)}


@router.post("/accounts/{provider}/import/preview")
async def import_preview(provider: str, file: UploadFile = File(...)) -> dict[str, Any]:
    """Preview a manual import file (CSV/JSON/XLSX) without persisting."""
    _require_provider(provider)
    content, filename = await _read_upload(file)
    try:
        return importer.preview_import(provider, filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/accounts/{provider}/import/confirm")
async def import_confirm(provider: str, file: UploadFile = File(...), mapping: str | None = None) -> dict[str, Any]:
    """Confirm and persist a manual import batch (deduplicated)."""
    _require_provider(provider)
    content, filename = await _read_upload(file)
    parsed_mapping = None
    if mapping:
        try:
            parsed_mapping = json.loads(mapping)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="mapping debe ser JSON válido") from exc
    try:
        result = importer.confirm_import(provider, filename, content, parsed_mapping)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Merge imported records into the provider's normalized transaction log
    try:
        records = importer.load_import_records(provider, result["batch_id"])
        existing = financial_normalizer.load_normalized(provider) or {
            "provider": provider,
            "positions": [],
            "transactions": [],
            "cash_by_currency": {},
        }
        new_txs = financial_normalizer.normalize_import_records(provider, records)
        existing["transactions"] = (existing.get("transactions") or []) + [t.__dict__ for t in new_txs]
        existing["transaction_count"] = len(existing["transactions"])
        existing["normalized_at"] = datetime.now(UTC).isoformat()
        financial_normalizer.save_normalized(provider, existing)
    except Exception:
        logger.warning("Import normalization failed for %s", provider, exc_info=True)
    vault = get_identity_vault()
    if vault.get_account(provider):
        vault.record_sync(provider, {"mode": "file_import", "batch_id": result["batch_id"], "imported": result["imported"]})
    record_event(
        provider,
        {"kind": "import", "batch_id": result["batch_id"], "imported": result["imported"], "duplicates": result["duplicates"]},
    )
    return result


@router.get("/accounts/{provider}/imports")
def list_imports(provider: str) -> dict[str, Any]:
    """List manual import batches for a provider."""
    _require_provider(provider)
    return {"provider": provider, "imports": importer.list_imports(provider)}


@router.get("/accounts/{provider}/normalized")
def normalized_provider(provider: str) -> dict[str, Any]:
    """Return normalized financial data for a provider (positions/transactions/cash)."""
    _require_provider(provider)
    data = financial_normalizer.load_normalized(provider)
    if data is None:
        raise HTTPException(status_code=404, detail="Sin datos normalizados — sincronizá primero")
    return data


@router.get("/portfolio")
def consolidated_portfolio() -> dict[str, Any]:
    """Consolidated normalized portfolio across all synced providers (per-currency, no FX mixing)."""
    return financial_normalizer.consolidated_portfolio()


@router.get("/portfolio/detail")
def portfolio_detail() -> dict[str, Any]:
    """Full external portfolio read-model: positions + providers + cash (P13)."""
    from cores.connections import portfolio_view

    return portfolio_view.portfolio_detail()


@router.get("/portfolio/transactions")
def portfolio_transactions(limit: int = 500) -> dict[str, Any]:
    """Merged normalized transactions classified for revenue-ledger separation (P13)."""
    from cores.connections import portfolio_view

    return {"transactions": portfolio_view.external_transactions(min(limit, 1000)), "count": min(limit, 1000)}


@router.get("/portfolio/income-candidates")
def portfolio_income_candidates() -> dict[str, Any]:
    """Transactions classified as income only — internal moves never count (P13)."""
    from cores.connections import portfolio_view

    items = portfolio_view.income_candidates()
    return {"candidates": items, "count": len(items)}


@router.post("/portfolio/income-candidates/import")
def portfolio_income_import(data: dict[str, Any]) -> dict[str, Any]:
    """Promote income candidates to the canonical ledger — explicit user action only.

    Dedup: each candidate is recorded with source_id derived from its content
    hash; already-imported candidates are skipped (idempotent).
    """
    import hashlib

    from cores.connections import portfolio_view
    from cores.ledger import LedgerEvent, _all_entries, record_event

    provider_filter = str(data.get("provider") or "")
    candidates = [t for t in portfolio_view.income_candidates() if not provider_filter or t.get("provider") == provider_filter]
    existing_ids = {e.source_id for e in _all_entries() if e.source == "connection_sync"}

    imported = 0
    skipped = 0
    for tx in candidates:
        canonical = json.dumps({k: tx.get(k) for k in ("provider", "symbol", "tx_type", "total", "currency", "executed_at")}, sort_keys=True, default=str)
        source_id = "inc_" + hashlib.sha256(canonical.encode()).hexdigest()[:20]
        if source_id in existing_ids:
            skipped += 1
            continue
        extra = tx.get("extra") if isinstance(tx.get("extra"), dict) else {}
        record_event(
            LedgerEvent.ADJUSTMENT_MANUAL,
            amount=float(tx.get("total") or 0),
            currency=str(tx.get("currency") or "USD"),
            description=f"Investment income ({tx.get('provider')}): {extra.get('description') or tx.get('tx_type')}",
            source="connection_sync",
            source_id=source_id,
            platform=str(tx.get("provider") or "external"),
            metadata={"kind": "investment_income", "symbol": tx.get("symbol"), "classified_kind": tx.get("kind")},
        )
        existing_ids.add(source_id)
        imported += 1
    return {"imported": imported, "skipped_duplicates": skipped, "candidates": len(candidates)}


# ── MCP agent consent + audit (P12 hardening) ───────────────────────────


@router.get("/mcp/consent")
def mcp_consent_status() -> dict[str, Any]:
    """Current consent grants for external MCP agents (Perch etc.)."""
    from cores.connections import mcp_consent

    return {"consents": mcp_consent.get_consents(), "data_classes": list(mcp_consent.DATA_CLASSES)}


@router.post("/mcp/consent")
def mcp_consent_update(data: dict[str, Any]) -> dict[str, Any]:
    """Grant or revoke a data class for external MCP agents."""
    from cores.connections import mcp_consent

    data_class = str(data.get("data_class", ""))
    granted = bool(data.get("granted", False))
    try:
        consents = mcp_consent.set_consent(data_class, granted)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"consents": consents}


@router.get("/mcp/audit")
def mcp_audit(limit: int = 100) -> dict[str, Any]:
    """Recent MCP tool-call audit entries (tool, class, provider, outcome — no payloads)."""
    from cores.connections import mcp_consent

    return {"entries": mcp_consent.get_audit(limit)}


def _require_provider(provider: str) -> None:
    meta = _catalog_providers().get(provider)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' no está en el catálogo")


async def _read_upload(file: UploadFile) -> tuple[bytes, str]:
    """Extract bytes+filename from an uploaded file."""
    filename = file.filename or "import.csv"
    content = await file.read()
    if isinstance(content, str):
        content = content.encode()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    return bytes(content), str(filename)
