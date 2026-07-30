"""Connections API — payout accounts, withdrawals, and platform registration."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from cores.financial.payout_recommender import (
    get_best_methods_for_argentina,
    get_platform_payout,
    list_all_payout_infos,
)
from cores.identity_vault import get_identity_vault
from database.db import SessionLocal
from database.models import CATEYEConfig

logger = logging.getLogger("cateye.connections.api")

router = APIRouter(prefix="/api/connections", tags=["connections"])

PAYOUT_KEY = "connections.payout_accounts"
WITHDRAWAL_KEY = "connections.withdrawals"
PLATFORM_REG_KEY = "connections.registered_platforms"


def _get_config_value(key: str, default: Any = None) -> Any:
    session = SessionLocal()
    try:
        row = session.query(CATEYEConfig).filter(CATEYEConfig.key == key).first()
        if row:
            return json.loads(row.value)
        return default
    except Exception:
        return default
    finally:
        session.close()


def _set_config_value(key: str, value: Any) -> None:
    session = SessionLocal()
    try:
        row = session.query(CATEYEConfig).filter(CATEYEConfig.key == key).first()
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        if row:
            row.value = serialized
        else:
            session.add(CATEYEConfig(key=key, value=serialized))
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Failed to save config %s: %s", key, exc)
    finally:
        session.close()


# ── Payout Accounts ──────────────────────────────────────────────


@router.get("/payout-accounts")
def list_payout_accounts():
    """List saved payout/bank accounts (no secrets)."""
    accounts = _get_config_value(PAYOUT_KEY, [])
    return {"accounts": accounts}


@router.post("/payout-accounts")
def create_payout_account(data: dict[str, Any]):
    """Register a new payout account or withdrawal address."""
    required = ["label", "type", "address"]
    for field in required:
        if field not in data or not data[field]:
            raise HTTPException(status_code=400, detail=f"'{field}' is required")

    accounts = _get_config_value(PAYOUT_KEY, [])
    new_id = max((a.get("id", 0) for a in accounts), default=0) + 1

    entry = {
        "id": new_id,
        "label": data["label"],
        "type": data["type"],
        "address": data["address"],
        "network": data.get("network", ""),
        "currency": data.get("currency", "USD"),
        "bank_name": data.get("bank_name", ""),
        "last_four": data.get("last_four", ""),
        "is_default": data.get("is_default", len(accounts) == 0),
        "connected": True,
        "withdrawable": data.get("withdrawable", 0),
        "created_at": datetime.now(UTC).isoformat(),
    }
    accounts.append(entry)
    _set_config_value(PAYOUT_KEY, accounts)
    logger.info("Payout account registered: %s (%s)", entry["label"], entry["type"])
    return {"status": "ok", "account": entry}


@router.delete("/payout-accounts/{account_id}")
def remove_payout_account(account_id: int):
    accounts = _get_config_value(PAYOUT_KEY, [])
    filtered = [a for a in accounts if a.get("id") != account_id]
    if len(filtered) == len(accounts):
        raise HTTPException(status_code=404, detail="Account not found")
    _set_config_value(PAYOUT_KEY, filtered)
    return {"status": "ok", "removed_id": account_id}


# ── Withdrawals ──────────────────────────────────────────────────


@router.get("/withdrawals")
def list_withdrawals():
    """List withdrawal history."""
    withdrawals = _get_config_value(WITHDRAWAL_KEY, [])
    return {"withdrawals": withdrawals}


@router.post("/withdrawals")
def request_withdrawal(data: dict[str, Any]):
    """Create a new withdrawal request."""
    account_id = data.get("account_id")
    amount = data.get("amount")
    if not account_id or not amount:
        raise HTTPException(status_code=400, detail="account_id and amount required")

    withdrawals = _get_config_value(WITHDRAWAL_KEY, [])
    accounts = _get_config_value(PAYOUT_KEY, [])
    account = next((a for a in accounts if a.get("id") == account_id), None)
    if not account:
        raise HTTPException(status_code=400, detail="Payout account not found")

    new_id = max((w.get("id", 0) for w in withdrawals), default=0) + 1
    entry = {
        "id": new_id,
        "account_id": account_id,
        "amount": amount,
        "currency": data.get("currency", account.get("currency", "USD")),
        "destination": account.get("label", account.get("address", "")),
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }
    withdrawals.append(entry)
    _set_config_value(WITHDRAWAL_KEY, withdrawals)
    logger.info("Withdrawal requested: %s → %s", amount, entry["destination"])
    return {"status": "ok", "withdrawal": entry}


# ── Registered Platforms ─────────────────────────────────────────


@router.get("/platforms")
def list_registered_platforms():
    """List user-registered platforms (not just vault-stored)."""
    registered = _get_config_value(PLATFORM_REG_KEY, [])
    vault = get_identity_vault()
    vault_accounts = vault.list_accounts()
    vault_map = {a["provider_name"]: a for a in vault_accounts}

    merged = []
    seen = set()
    for p in registered:
        seen.add(p.get("provider", "").lower())
        v = vault_map.get(p["provider"].lower(), {})
        merged.append({**p, **v, "connected": v.get("has_credentials", False)})

    for v in vault_accounts:
        if v["provider_name"].lower() not in seen:
            merged.append({
                "provider": v["provider_name"],
                "connected": v.get("has_credentials", False),
                "email": v.get("email", ""),
                "username": v.get("username", ""),
                "earnings": 0,
                "pending": 0,
                "last_sync": v.get("last_checked", ""),
            })

    return {"platforms": merged}


@router.post("/platforms")
def register_platform(data: dict[str, Any]):
    """Register a new platform connection with guided info."""
    required = ["provider"]
    for field in required:
        if field not in data or not data[field]:
            raise HTTPException(status_code=400, detail=f"'{field}' is required")

    registered = _get_config_value(PLATFORM_REG_KEY, [])
    provider = data["provider"].lower()

    existing = next((p for p in registered if p["provider"].lower() == provider), None)
    if existing:
        existing["email"] = data.get("email", existing.get("email", ""))
        existing["username"] = data.get("username", existing.get("username", ""))
    else:
        registered.append({
            "provider": provider,
            "email": data.get("email", ""),
            "username": data.get("username", ""),
            "registered_at": datetime.now(UTC).isoformat(),
        })

    _set_config_value(PLATFORM_REG_KEY, registered)

    vault = get_identity_vault()
    if data.get("token") or data.get("password"):
        vault.store_credentials(
            provider=provider,
            email=data.get("email", ""),
            token=data.get("token", ""),
            password=data.get("password", ""),
        )
        vault.update_session_state(provider, "connected")
        vault.update_health(provider, "ok")

    logger.info("Platform registered: %s (%s)", provider, data.get("email", ""))
    return {"status": "ok", "provider": provider}


# ── Payout Recommendations for Argentina ──────────────────────────


@router.get("/payout-recommendations")
def payout_recommendations():
    """Best payout methods for Argentina, ranked by convenience."""
    return {
        "methods": get_best_methods_for_argentina(),
        "country": "Argentina",
        "currency": "ARS",
        "note": "Recomendaciones basadas en residencia en Argentina. KYC con DNI es suficiente para la mayoría.",
    }


@router.get("/payout-recommendations/{platform_id}")
def platform_payout_recommendation(platform_id: str):
    """Best payout methods for a specific platform from Argentina."""
    info = get_platform_payout(platform_id.lower())
    if not info:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform_id}")

    method_ids = info.recommended
    all_methods = get_best_methods_for_argentina()
    all_map = {m["id"]: m for m in all_methods}

    recommended = [all_map[mid] for mid in method_ids if mid in all_map]

    return {
        "platform_id": info.platform_id,
        "platform_name": info.platform_name,
        "kyc_required": info.kyc_required,
        "notes": info.notes,
        "recommended_methods": recommended,
        "all_available": [m for m in info.methods],
    }


@router.get("/payout-platforms")
def list_payout_platforms():
    """List all platforms with their payout info."""
    return {"platforms": list_all_payout_infos()}
