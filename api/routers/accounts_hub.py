from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from cores.crypto.sync_manager import get_crypto_sync_manager
from cores.financial.truth_layer import get_truth_layer
from cores.financial.withdrawal import get_summary as get_withdrawal_summary
from cores.identity_vault import get_identity_vault

logger = logging.getLogger("ownex.api.accounts_hub")

router = APIRouter(prefix="/api/accounts-hub", tags=["accounts_hub"])


@router.get("/status")
def accounts_hub_status() -> dict[str, Any]:
    vault = get_identity_vault()
    accounts = vault.list_accounts()
    truth = get_truth_layer()
    state = truth.get_state()
    crypto_mgr = get_crypto_sync_manager()
    crypto_summary = crypto_mgr.get_summary()
    wd_summary = get_withdrawal_summary()

    platform_accounts = []
    for acct in accounts:
        provider = acct.get("provider_name", "")
        health = vault.check_session_health(provider)
        platform_accounts.append(
            {
                "id": provider,
                "type": "platform",
                "label": provider.replace("_", " ").title(),
                "connected": health.get("connected", False),
                "health": health.get("reason", "unknown"),
                "has_credentials": acct.get("has_credentials", False),
                "last_checked": acct.get("last_checked", ""),
            }
        )

    crypto_wallets = []
    for wid, conn in crypto_mgr.connectors.items():
        snap = crypto_mgr.get_snapshot(wid)
        crypto_wallets.append(
            {
                "id": wid,
                "type": "crypto",
                "label": conn.chain.value,
                "connected": snap.connection.value if snap else "unknown",
                "total_usd": snap.total_usd if snap else 0,
                "last_sync": snap.synced_at if snap else "",
            }
        )

    return {
        "accounts": platform_accounts + crypto_wallets,
        "summary": {
            "total_platforms": len(platform_accounts),
            "connected_platforms": sum(1 for a in platform_accounts if a["connected"]),
            "total_wallets": len(crypto_wallets),
            "crypto_total_usd": crypto_summary.get("total_usd", 0),
            "verified_balance": round(state.verified_balance, 2),
            "pending_balance": round(state.pending_balance, 2),
            "withdrawn_total": wd_summary.get("total_completed", 0),
        },
    }


@router.get("/sync-history")
def sync_history() -> list[dict[str, Any]]:
    crypto_mgr = get_crypto_sync_manager()
    history: list[dict[str, Any]] = []
    for wid in crypto_mgr.connectors:
        for snap in crypto_mgr.get_history(wid, limit=5):
            history.append(
                {
                    "source": wid,
                    "type": "crypto",
                    "timestamp": snap.synced_at,
                    "status": snap.connection.value,
                    "total_usd": snap.total_usd,
                    "error": snap.error,
                    "balance_count": len(snap.balances),
                    "tx_count": len(snap.transactions),
                }
            )
    truth = get_truth_layer()
    for pid, _ps in truth.get_state().by_platform.items():
        sync_state = truth.get_platform_sync(pid)
        history.append(
            {
                "source": pid,
                "type": "platform",
                "timestamp": sync_state.last_sync,
                "status": sync_state.sync_health.value,
                "consecutive_failures": sync_state.consecutive_failures,
                "total_syncs": sync_state.total_syncs,
            }
        )
    history.sort(key=lambda h: h.get("timestamp", ""), reverse=True)
    return history[:100]
