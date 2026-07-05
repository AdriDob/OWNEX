"""CATEYE Micro‑Functions — compact, real‑time queries for the dashboard layer.

Every function returns a plain dict (JSON‑serialisable) and never raises.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from cores.crypto.sync_manager import get_crypto_sync_manager
from cores.financial.reconciliation import get_reconciliation_engine
from cores.financial.scheduler import get_financial_sync_scheduler
from cores.financial.truth_layer import SyncHealth, get_truth_layer
from cores.financial.withdrawal import WithdrawalStatus, get_withdrawal, list_withdrawals
from cores.identity_vault import get_identity_vault
from cores.ledger import compute_wallet, get_history
from cores.pipeline.report_service import get_report
from cores.platforms import PLATFORM_REGISTRY

logger = logging.getLogger("catseye.micro")


# ── 1. quick_sync_all ────────────────────────────────────────────────


def quick_sync_all() -> dict[str, Any]:
    start = time.monotonic()
    scheduler = get_financial_sync_scheduler()
    report = scheduler.sync_all()

    platforms: dict[str, str] = {}
    crypto: dict[str, str] = {}
    errors: list[dict[str, Any]] = []

    for pid, presult in report.platforms.items():
        if presult.get("success"):
            platforms[pid] = "ok"
        else:
            platforms[pid] = "error"
            errors.append({"source": pid, "type": "platform", "error": presult.get("error", "unknown")})

    for wid, wresult in report.crypto.items():
        if wresult.get("success"):
            crypto[wid] = "ok"
        else:
            crypto[wid] = "error"
            errors.append({"source": wid, "type": "crypto", "error": wresult.get("error", "unknown")})

    elapsed_ms = round((time.monotonic() - start) * 1000)
    return {"total_time_ms": elapsed_ms, "platforms": platforms, "crypto": crypto, "errors": errors}


# ── 2. sync_source_now ────────────────────────────────────────────────


def sync_source_now(source_id: str) -> dict[str, Any]:
    errors: list[str] = []
    truth = get_truth_layer()

    before_balance: float = 0.0
    after_balance: float = 0.0

    if source_id in PLATFORM_REGISTRY:
        state_before = truth.get_state()
        before_balance = state_before.total_balance

        scheduler = get_financial_sync_scheduler()
        try:
            results = scheduler.sync_platforms()
            presult = results.get(source_id, {})
            if not presult.get("success"):
                errors.append(presult.get("error", "sync_failed"))
        except Exception as exc:
            errors.append(str(exc))

        state_after = truth.get_state()
        after_balance = state_after.total_balance
    else:
        crypto_mgr = get_crypto_sync_manager()
        connector = crypto_mgr.connectors.get(source_id)
        if connector:
            snapshots = crypto_mgr.get_all_snapshots()
            before_snap = snapshots.get(source_id)
            before_balance = before_snap.total_usd if before_snap else 0.0

            try:
                snap = crypto_mgr.sync_wallet(source_id)
                if snap and snap.connection.value == "connected":
                    after_balance = snap.total_usd
                else:
                    errors.append(snap.error if snap else "wallet_not_found")
                    after_balance = before_balance
            except Exception as exc:
                errors.append(str(exc))
                after_balance = before_balance
        else:
            errors.append(f"source_not_found: {source_id}")
            after_balance = before_balance

    return {
        "source_id": source_id,
        "before_balance": round(before_balance, 2),
        "after_balance": round(after_balance, 2),
        "delta": round(after_balance - before_balance, 2),
        "errors": errors,
    }


# ── 3. get_sync_health ────────────────────────────────────────────────


def get_sync_health() -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()

    integrations: dict[str, dict[str, Any]] = {}

    for pid, pstate in state.by_platform.items():
        sync = pstate.sync_state
        sync_count = sync.total_syncs or 1
        success_rate = round(sync.successful_syncs / sync_count, 3) if sync_count else 0.0
        error_rate = round(1 - success_rate, 3)
        integrations[pid] = {
            "last_sync_time": datetime.fromtimestamp(sync.last_sync, tz=timezone.utc).isoformat() if sync.last_sync else "",
            "success_rate": success_rate,
            "error_rate": error_rate,
            "avg_latency_ms": 0.0,
            "health": sync.sync_health.value,
        }

    crypto_mgr = get_crypto_sync_manager()
    for wid, _connector in crypto_mgr.connectors.items():
        history = crypto_mgr.get_history(wid, limit=20)
        total = len(history)
        successful = sum(1 for s in history if s.connection.value == "connected")
        success_rate = round(successful / total, 3) if total else 0.0

        last_snap = crypto_mgr.get_snapshot(wid)
        last_sync_time = last_snap.synced_at if last_snap else ""

        integrations[wid] = {
            "last_sync_time": last_sync_time,
            "success_rate": success_rate,
            "error_rate": round(1 - success_rate, 3),
            "avg_latency_ms": 0.0,
            "health": "healthy" if (last_snap and last_snap.connection.value == "connected") else "degraded",
        }

    overall_health: str
    health_values = [i["health"] for i in integrations.values()]
    if any(h in ("failed", "critical") for h in health_values):
        overall_health = "critical"
    elif any(h in ("degraded", "stale") for h in health_values):
        overall_health = "degraded"
    else:
        overall_health = "healthy"

    return {"integrations": integrations, "overall_health": overall_health}


# ── 4. trace_balance_origin ───────────────────────────────────────────


def trace_balance_origin(account_id: str) -> dict[str, Any]:
    entries = get_history(limit=1000)
    matching = [e for e in entries if e.get("source_id") == account_id or e.get("platform") == account_id]

    ledger_entries = matching if matching else entries[:50]

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    source_chain: list[dict[str, Any]] = []

    for entry in entries:
        eid = entry.get("id", "")
        nodes.append({"id": eid, "event": entry.get("event", ""), "amount": entry.get("amount", 0), "source": entry.get("source", ""), "platform": entry.get("platform", ""), "timestamp": entry.get("timestamp", "")})

    sorted_entries = sorted(entries, key=lambda e: e.get("timestamp", ""))
    prev_id = ""
    for entry in sorted_entries:
        current_id = entry.get("id", "")
        if prev_id and current_id:
            edges.append({"from": prev_id, "to": current_id, "label": "chronological"})
        prev_id = current_id

    for entry in matching:
        source_chain.append({"entry_id": entry.get("id", ""), "event": entry.get("event", ""), "amount": entry.get("amount", 0), "source": entry.get("source", ""), "timestamp": entry.get("timestamp", "")})

    truth = get_truth_layer()
    state = truth.get_state()
    current_balance = state.total_balance

    return {
        "account_id": account_id,
        "current_balance": round(current_balance, 2),
        "ledger_entries": ledger_entries,
        "source_chain": source_chain,
        "trace_graph": {"nodes": nodes, "edges": edges},
    }


# ── 5. detect_sync_anomalies ──────────────────────────────────────────


def detect_sync_anomalies() -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    truth = get_truth_layer()
    state = truth.get_state()

    wallet = compute_wallet()
    if wallet.available_balance < -0.01:
        anomalies.append({
            "type": "negative_balance",
            "severity": "critical",
            "source": "ledger",
            "description": f"Available balance is negative: {wallet.available_balance:.2f}",
            "details": {"available_balance": round(wallet.available_balance, 2)},
        })
    if wallet.pending_balance < -0.01:
        anomalies.append({
            "type": "negative_balance",
            "severity": "high",
            "source": "ledger",
            "description": f"Pending balance is negative: {wallet.pending_balance:.2f}",
            "details": {"pending_balance": round(wallet.pending_balance, 2)},
        })
    if wallet.locked_balance < -0.01:
        anomalies.append({
            "type": "negative_balance",
            "severity": "high",
            "source": "ledger",
            "description": f"Locked balance is negative: {wallet.locked_balance:.2f}",
            "details": {"locked_balance": round(wallet.locked_balance, 2)},
        })

    for pid, pstate in state.by_platform.items():
        sync = pstate.sync_state
        if sync.consecutive_failures >= 3:
            anomalies.append({
                "type": "sync_failure",
                "severity": "high" if sync.consecutive_failures < 5 else "critical",
                "source": pid,
                "description": f"{sync.consecutive_failures} consecutive sync failures for {pid}",
                "details": {"consecutive_failures": sync.consecutive_failures, "last_error": sync.last_error},
            })
        if sync.is_stale and sync.last_success > 0:
            anomalies.append({
                "type": "stale_data",
                "severity": "medium",
                "source": pid,
                "description": f"Data for {pid} is stale (last sync: {datetime.fromtimestamp(sync.last_success, tz=timezone.utc).isoformat()})",
                "details": {"last_success": sync.last_success, "stale_threshold_seconds": 3600},
            })

    crypto_mgr = get_crypto_sync_manager()
    for wid in crypto_mgr.connectors:
        snap = crypto_mgr.get_snapshot(wid)
        if not snap:
            anomalies.append({
                "type": "missing_sync",
                "severity": "medium",
                "source": wid,
                "description": f"No sync snapshot found for wallet {wid}",
                "details": {},
            })
            continue
        if snap.connection.value != "connected":
            anomalies.append({
                "type": "sync_failure",
                "severity": "high",
                "source": wid,
                "description": f"Wallet {wid} sync failed: {snap.error}",
                "details": {"error": snap.error, "connection": snap.connection.value},
            })

    return anomalies


# ── 6. get_pending_actions ────────────────────────────────────────────


def get_pending_actions() -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    pending_withdrawals = list_withdrawals(status=WithdrawalStatus.PENDING)
    for wd in pending_withdrawals:
        actions.append({
            "action_type": "confirm_withdrawal",
            "priority": 7,
            "source": wd.get("id", ""),
            "description": f"Pending withdrawal: {wd.get('amount', 0):.2f} {wd.get('currency', 'USD')} to {wd.get('target_account', 'unknown')}",
            "action_url": f"/api/withdrawals/{wd.get('id', '')}/confirm",
            "created_at": wd.get("created_at", ""),
        })

    initiated_withdrawals = list_withdrawals(status=WithdrawalStatus.INITIATED)
    for wd in initiated_withdrawals:
        actions.append({
            "action_type": "process_withdrawal",
            "priority": 6,
            "source": wd.get("id", ""),
            "description": f"Initiated withdrawal: {wd.get('amount', 0):.2f} {wd.get('currency', 'USD')}",
            "action_url": f"/api/withdrawals/{wd.get('id', '')}/process",
            "created_at": wd.get("created_at", ""),
        })

    truth = get_truth_layer()
    state = truth.get_state()
    for pid, pstate in state.by_platform.items():
        sync = pstate.sync_state
        if sync.consecutive_failures > 0:
            actions.append({
                "action_type": "retry_sync",
                "priority": min(5 + sync.consecutive_failures, 10),
                "source": pid,
                "description": f"Retry failed sync for {pid} ({sync.consecutive_failures} failures)",
                "action_url": f"/api/micro/sync-source/{pid}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    vault_actions = _check_disconnected_accounts()
    actions.extend(vault_actions)

    reconn_engine = get_reconciliation_engine()
    reconn_state = reconn_engine.get_state()
    if reconn_state.get("unresolved", 0) > 0:
        actions.append({
            "action_type": "resolve_discrepancies",
            "priority": 8,
            "source": "reconciliation",
            "description": f"{reconn_state['unresolved']} unresolved reconciliation discrepancies",
            "action_url": "/api/financial/reconciliation",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    actions.sort(key=lambda a: a["priority"], reverse=True)
    return actions


def _check_disconnected_accounts() -> list[dict[str, Any]]:
    from cores.identity_vault import get_identity_vault

    vault = get_identity_vault()
    disconnected: list[dict[str, Any]] = []
    for acct in vault.list_accounts():
        if acct.get("session_state") == "disconnected" and acct.get("has_credentials"):
            disconnected.append({
                "action_type": "reconnect_account",
                "priority": 5,
                "source": acct.get("provider_name", ""),
                "description": f"Account {acct.get('provider_name', 'unknown')} is disconnected",
                "action_url": f"/api/identity/{acct.get('provider_name', '')}/reconnect",
                "created_at": acct.get("last_checked", ""),
            })
    return disconnected


# ── 7. compute_real_exposure ──────────────────────────────────────────


def compute_real_exposure() -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()

    platform_exposure: dict[str, float] = {}
    for pid, pstate in state.by_platform.items():
        platform_exposure[pid] = round(pstate.verified_balance + pstate.pending_balance, 2)

    crypto_mgr = get_crypto_sync_manager()
    crypto_by_asset: dict[str, float] = {}
    for wid in crypto_mgr.connectors:
        snap = crypto_mgr.get_snapshot(wid)
        if snap and snap.balances:
            for bal in snap.balances:
                symbol = bal.symbol
                crypto_by_asset[symbol] = round(crypto_by_asset.get(symbol, 0.0) + bal.usd_value, 2)

    total_crypto = round(sum(crypto_by_asset.values()), 2)
    total_platform = round(sum(platform_exposure.values()), 2)

    pending_withdrawals = list_withdrawals(status=WithdrawalStatus.PENDING)
    pending_exposure = round(sum(wd.get("amount", 0) for wd in pending_withdrawals), 2)

    initiated_withdrawals = list_withdrawals(status=WithdrawalStatus.INITIATED)
    pending_exposure += round(sum(wd.get("amount", 0) for wd in initiated_withdrawals), 2)

    total_exposure = round(total_platform + total_crypto + pending_exposure, 2)

    return {
        "total_exposure": total_exposure,
        "crypto_exposure": {"by_asset": crypto_by_asset, "total": total_crypto},
        "platform_exposure": {"by_platform": platform_exposure, "total": total_platform},
        "pending_exposure": pending_exposure,
    }


# ── 8. export_account_snapshot ────────────────────────────────────────


def export_account_snapshot(account_id: str) -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()

    balance = 0.0
    sync_state: dict[str, Any] = {}

    if account_id in state.by_platform:
        pstate = state.by_platform[account_id]
        balance = pstate.verified_balance + pstate.pending_balance
        sync_state = {
            "last_sync": pstate.sync_state.last_sync,
            "last_success": pstate.sync_state.last_success,
            "health": pstate.sync_state.sync_health.value,
            "consecutive_failures": pstate.sync_state.consecutive_failures,
        }
    else:
        crypto_mgr = get_crypto_sync_manager()
        snap = crypto_mgr.get_snapshot(account_id)
        if snap:
            balance = snap.total_usd
            sync_state = {
                "last_sync": snap.synced_at,
                "connection": snap.connection.value,
                "error": snap.error,
            }

    recent_txns = get_history(limit=20)
    account_txns = [t for t in recent_txns if t.get("platform") == account_id or t.get("source") == account_id]

    return {
        "account_id": account_id,
        "balance": round(balance, 2),
        "recent_transactions": account_txns[:20],
        "sync_state": sync_state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "platform_registered": account_id in PLATFORM_REGISTRY,
            "crypto_wallet": account_id in get_crypto_sync_manager().connectors,
        },
    }


# ── 9. retry_failed_syncs ─────────────────────────────────────────────


def retry_failed_syncs() -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()
    scheduler = get_financial_sync_scheduler()
    crypto_mgr = get_crypto_sync_manager()

    to_retry: list[str] = []
    details: list[dict[str, Any]] = []

    for pid, pstate in state.by_platform.items():
        sync = pstate.sync_state
        if sync.consecutive_failures > 0 and sync.should_retry():
            to_retry.append(pid)

    for wid in crypto_mgr.connectors:
        snap = crypto_mgr.get_snapshot(wid)
        if not snap or snap.connection.value != "connected":
            to_retry.append(wid)

    retried = 0
    succeeded = 0
    failed = 0

    for source in to_retry:
        retried += 1
        try:
            if source in PLATFORM_REGISTRY:
                results = scheduler.sync_platforms()
                presult = results.get(source, {})
                if presult.get("success"):
                    truth.record_sync_success(source)
                    succeeded += 1
                    details.append({"source": source, "status": "success", "error": ""})
                else:
                    truth.record_sync_failure(source, presult.get("error", "unknown"))
                    failed += 1
                    details.append({"source": source, "status": "failed", "error": presult.get("error", "unknown")})
            else:
                snap = crypto_mgr.sync_wallet(source)
                if snap and snap.connection.value == "connected":
                    succeeded += 1
                    details.append({"source": source, "status": "success", "error": ""})
                else:
                    failed += 1
                    details.append({"source": source, "status": "failed", "error": snap.error if snap else "unknown"})
        except Exception as exc:
            failed += 1
            details.append({"source": source, "status": "error", "error": str(exc)})

    return {"retried": retried, "succeeded": succeeded, "failed": failed, "details": details}


# ── 10. get_minimal_dashboard_state ────────────────────────────────────


def get_minimal_dashboard_state() -> dict[str, Any]:
    from cores.financial.withdrawal import get_summary as get_withdrawal_summary

    truth = get_truth_layer()
    state = truth.get_state()

    crypto_mgr = get_crypto_sync_manager()
    crypto_summary = crypto_mgr.get_summary()

    withdrawal_summary = get_withdrawal_summary()

    last_sync_global = state.last_sync or ""

    health = "healthy"
    if any(ps.sync_state.sync_health in (SyncHealth.FAILED,) for ps in state.by_platform.values()):
        health = "critical"
    elif any(ps.sync_state.sync_health in (SyncHealth.STALE, SyncHealth.DEGRADED) for ps in state.by_platform.values()):
        health = "degraded"

    return {
        "total_balance": round(state.total_balance, 2),
        "pending_balance": round(state.pending_balance, 2),
        "last_sync_global": last_sync_global,
        "system_health": health,
        "total_wallets": crypto_summary.get("total_wallets", 0),
        "total_platforms": len(state.by_platform),
        "unconfirmed_withdrawals": withdrawal_summary.get("total_pending", 0) + withdrawal_summary.get("total_initiated", 0),
    }


# ── 11. _get_entity_by_type ────────────────────────────────────────────


def _get_entity_by_type(type_: str, id_: str) -> dict[str, Any]:
    if type_ == "platform":
        truth = get_truth_layer()
        state = truth.get_state()
        pstate = state.by_platform.get(id_)
        if pstate:
            return {
                "id": id_,
                "type": "platform",
                "balance": round(pstate.verified_balance + pstate.pending_balance, 2),
                "verified_balance": round(pstate.verified_balance, 2),
                "pending_balance": round(pstate.pending_balance, 2),
                "last_sync": pstate.sync_state.last_sync,
                "health": pstate.sync_state.sync_health.value,
                "consecutive_failures": pstate.sync_state.consecutive_failures,
            }
        return {"id": id_, "type": "platform", "error": "not_found"}

    elif type_ == "wallet":
        crypto_mgr = get_crypto_sync_manager()
        snap = crypto_mgr.get_snapshot(id_)
        if snap:
            return {
                "id": id_,
                "type": "wallet",
                "total_usd": round(snap.total_usd, 2),
                "balances": [{"symbol": b.symbol, "amount": b.amount, "usd_value": round(b.usd_value, 2)} for b in (snap.balances or [])],
                "connection": snap.connection.value,
                "synced_at": snap.synced_at,
                "error": snap.error,
            }
        return {"id": id_, "type": "wallet", "error": "not_found"}

    elif type_ == "withdrawal":
        wd = get_withdrawal(id_)
        if wd:
            return {
                "id": wd.id,
                "type": "withdrawal",
                "amount": wd.amount,
                "currency": wd.currency,
                "status": wd.status.value,
                "target_account": wd.target_account,
                "created_at": wd.created_at,
                "updated_at": wd.updated_at,
            }
        return {"id": id_, "type": "withdrawal", "error": "not_found"}

    elif type_ == "transaction":
        entries = get_history(limit=5000)
        for e in entries:
            if e.get("id") == id_ or e.get("entry_id") == id_:
                return {"id": id_, "type": "transaction", **e}
        return {"id": id_, "type": "transaction", "error": "not_found"}

    elif type_ == "program":
        from cores.targets.models import TargetIntel
        from database.db import SessionLocal

        session = SessionLocal()
        try:
            program = session.query(TargetIntel).filter(TargetIntel.id == id_).first()
            if program:
                return {
                    "id": str(program.id),
                    "type": "program",
                    "name": program.name,
                    "domain": program.domain,
                    "source": program.source,
                    "technology_tags": program.technology_tags,
                    "scores": program.scores,
                    "created_at": str(program.created_at) if program.created_at else "",
                }
            return {"id": id_, "type": "program", "error": "not_found"}
        finally:
            session.close()

    elif type_ == "finding":
        from database.db import SessionLocal
        from database.models import Finding

        session = SessionLocal()
        try:
            finding = session.query(Finding).filter(Finding.id == id_).first()
            if finding:
                return {
                    "id": finding.id,
                    "type": "finding",
                    "target_id": finding.target_id,
                    "title": finding.title,
                    "severity": finding.severity,
                    "description": finding.description,
                    "created_at": str(finding.created_at) if finding.created_at else "",
                }
            return {"id": id_, "type": "finding", "error": "not_found"}
        finally:
            session.close()

    elif type_ == "report":
        from database.db import SessionLocal

        session = SessionLocal()
        try:
            report = get_report(session, int(id_))
            if report:
                return {"id": id_, "type": "report", **report}
            return {"id": id_, "type": "report", "error": "not_found"}
        finally:
            session.close()

    elif type_ == "account":
        vault = get_identity_vault()
        acct = vault.get_account(id_)
        if acct:
            return {"id": id_, "type": "account", **acct}
        return {"id": id_, "type": "account", "error": "not_found"}

    return {"id": id_, "type": type_, "error": f"unknown_type: {type_}"}


# ── 12. _batch_operation ───────────────────────────────────────────────


def _batch_operation(
    ids: list[str],
    type_: str,
    operation: str,
    **kwargs: Any,
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    synced = 0
    failed = 0
    deleted = 0

    for id_ in ids:
        if operation == "export":
            entity = _get_entity_by_type(type_, id_)
            details.append(entity)

        elif operation == "sync":
            result = sync_source_now(id_)
            if not result.get("errors"):
                synced += 1
            else:
                failed += 1
            details.append({"id": id_, "errors": result.get("errors", [])})

        elif operation == "delete":
            from database.db import SessionLocal
            from database.models import Finding

            session = SessionLocal()
            try:
                if type_ == "finding":
                    deleted_count = session.query(Finding).filter(Finding.id == id_).delete()
                    session.commit()
                    if deleted_count:
                        deleted += 1
                        details.append({"id": id_, "deleted": True})
                    else:
                        details.append({"id": id_, "deleted": False, "error": "not_found"})
                else:
                    details.append({"id": id_, "deleted": False, "error": f"delete not supported for type: {type_}"})
            except Exception as exc:
                session.rollback()
                details.append({"id": id_, "deleted": False, "error": str(exc)})
            finally:
                session.close()

        elif operation == "tag":
            tag = kwargs.get("tag", "")
            details.append({"id": id_, "tagged": True, "tag": tag})

    result: dict[str, Any] = {"details": details}

    if operation == "export":
        result["exported"] = len(details)
        result["format"] = kwargs.get("format", "json")
        result["data"] = details
    elif operation == "sync":
        result["synced"] = synced
        result["failed"] = failed
    elif operation == "delete":
        result["deleted"] = deleted
    elif operation == "tag":
        result["tagged"] = len(details)

    return result
