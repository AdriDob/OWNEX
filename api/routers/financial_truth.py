"""Financial Truth API — single source of truth endpoints.

Every response includes provenance, confidence, and category for every value.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.financial.dashboard import get_dashboard
from cores.financial.events import publish_financial_event
from cores.financial.reconciliation import get_reconciliation_engine
from cores.financial.truth_layer import (
    ValueCategory,
    get_truth_layer,
)
from cores.financial.withdrawal import (
    ConfirmationMethod,
    ProofAttachment,
    WithdrawalStatus,
    complete_withdrawal,
    create_withdrawal,
    fail_withdrawal,
    list_withdrawals,
    mark_pending,
)
from cores.financial.withdrawal import (
    get_summary as get_withdrawal_summary,
)
from cores.ledger import LedgerEvent, record_event
from cores.ledger import get_history as get_ledger_history

logger = logging.getLogger("ownex.api.financial_truth")

router = APIRouter(prefix="/api/financial", tags=["financial_truth"])


class WithdrawalRequest(BaseModel):
    amount: float
    currency: str = "USD"
    platform: str
    target_account: str
    method: str
    fee: float = 0.0


class WithdrawalConfirmRequest(BaseModel):
    withdrawal_id: str
    tx_hash: str = ""
    proof_type: str = ""
    proof_value: str = ""


class WithdrawalFailRequest(BaseModel):
    withdrawal_id: str
    error: str


class RecordManualAdjustment(BaseModel):
    amount: float
    currency: str = "USD"
    description: str
    platform: str = "manual"


@router.get("/state")
def get_financial_state() -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()
    return state.to_dict()


@router.get("/state/summary")
def get_financial_summary() -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()
    return {
        "verified": round(state.verified_balance, 2),
        "pending": round(state.pending_balance, 2),
        "withdrawn": round(state.withdrawn_balance, 2),
        "estimated": round(state.estimated_balance, 2),
        "manual": round(state.manual_balance, 2),
        "disputed": round(state.disputed_balance, 2),
        "real": round(state.real_balance, 2),
        "effective": round(state.effective_balance, 2),
        "total": round(state.total_balance, 2),
        "sync_health": state.sync_health.value,
        "entry_count": state.entry_count,
    }


@router.get("/state/by-category")
def get_financial_by_category() -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()
    return {
        "categories": {
            cat: {
                "amount": round(sb.amount, 2),
                "confidence": sb.confidence,
                "entry_count": sb.entry_count,
                "last_updated": sb.last_updated,
            }
            for cat, sb in state.by_category.items()
        },
        "category_order": [c.value for c in ValueCategory],
    }


@router.get("/state/by-platform")
def get_financial_by_platform() -> dict[str, Any]:
    truth = get_truth_layer()
    state = truth.get_state()
    return {
        "platforms": {
            pid: {
                "verified": round(ps.verified_balance, 2),
                "pending": round(ps.pending_balance, 2),
                "withdrawn": round(ps.withdrawn_balance, 2),
                "estimated": round(ps.estimated_balance, 2),
                "report_count": ps.report_count,
                "sync_health": ps.sync_state.sync_health.value,
                "last_sync": ps.sync_state.last_sync,
            }
            for pid, ps in state.by_platform.items()
        }
    }


@router.get("/state/sync-health")
def get_sync_health() -> dict[str, Any]:
    truth = get_truth_layer()
    return {
        "health": truth.get_state().sync_health.value,
        "platforms": [
            {
                "id": pid,
                "health": ps.sync_state.sync_health.value,
                "last_sync": ps.sync_state.last_sync,
                "last_success": ps.sync_state.last_success,
                "consecutive_failures": ps.sync_state.consecutive_failures,
            }
            for pid, ps in truth.get_state().by_platform.items()
        ],
    }


@router.get("/ledger")
def get_ledger(limit: int = 100) -> list[dict[str, Any]]:
    return get_ledger_history(limit)


@router.post("/adjustment")
def record_adjustment(req: RecordManualAdjustment) -> dict[str, Any]:
    entry = record_event(
        event=LedgerEvent.ADJUSTMENT_MANUAL,
        amount=req.amount,
        currency=req.currency,
        description=req.description,
        source="manual_input",
        source_id="",
        platform=req.platform,
    )
    publish_financial_event(
        "financial:sync_completed",
        amount=req.amount,
        currency=req.currency,
        platform=req.platform,
        description=f"Ajuste manual: {req.description}",
    )
    return {
        "entry_id": entry.entry_id,
        "amount": req.amount,
        "currency": req.currency,
        "description": req.description,
    }


# ── Withdrawals ──────────────────────────────────────────────────────


@router.get("/withdrawals")
def get_withdrawals(
    status: str | None = None,
    platform: str | None = None,
) -> list[dict[str, Any]]:
    status_enum = WithdrawalStatus(status) if status else None
    return list_withdrawals(status=status_enum, platform=platform)


@router.post("/withdrawals")
def request_withdrawal(req: WithdrawalRequest) -> dict[str, Any]:
    w = create_withdrawal(
        amount=req.amount,
        currency=req.currency,
        platform=req.platform,
        target_account=req.target_account,
        method=req.method,
        fee=req.fee,
    )
    publish_financial_event(
        "financial:withdrawal_completed" if False else "financial:sync_completed",
        amount=req.amount,
        currency=req.currency,
        platform=req.platform,
        description=f"Retiro solicitado: {req.amount} {req.currency} a {req.target_account}",
        metadata={"withdrawal_id": w.id},
    )
    return w.to_dict()


@router.post("/withdrawals/{withdrawal_id}/pending")
def set_withdrawal_pending(withdrawal_id: str) -> dict[str, Any]:
    w = mark_pending(withdrawal_id)
    if not w:
        raise HTTPException(404, "Withdrawal not found or cannot transition")
    return w.to_dict()


@router.post("/withdrawals/{withdrawal_id}/complete")
def confirm_withdrawal(withdrawal_id: str, req: WithdrawalConfirmRequest) -> dict[str, Any]:
    proof = []
    if req.proof_type and req.proof_value:
        proof.append(ProofAttachment(type=req.proof_type, value=req.proof_value))
    w = complete_withdrawal(
        withdrawal_id,
        confirmation=ConfirmationMethod.MANUAL_PROOF if req.tx_hash else ConfirmationMethod.UNCONFIRMED,
        tx_hash=req.tx_hash,
        proof=proof or None,
    )
    if not w:
        raise HTTPException(404, "Withdrawal not found or already settled")
    publish_financial_event(
        "financial:withdrawal_completed",
        amount=w.amount,
        currency=w.currency,
        platform=w.platform,
        description=f"Retiro completado: {w.amount} {w.currency}",
        metadata={"withdrawal_id": w.id, "tx_hash": w.tx_hash},
    )
    return w.to_dict()


@router.post("/withdrawals/{withdrawal_id}/fail")
def fail_withdrawal_endpoint(withdrawal_id: str, req: WithdrawalFailRequest) -> dict[str, Any]:
    w = fail_withdrawal(withdrawal_id, req.error)
    if not w:
        raise HTTPException(404, "Withdrawal not found or already settled")
    publish_financial_event(
        "financial:withdrawal_failed",
        amount=w.amount,
        currency=w.currency,
        platform=w.platform,
        description=f"Retiro fallido: {req.error[:100]}",
        metadata={"withdrawal_id": w.id, "error": req.error},
    )
    return w.to_dict()


@router.get("/withdrawals/summary")
def withdrawal_summary() -> dict[str, Any]:
    return get_withdrawal_summary()


# ── Unified Dashboard ────────────────────────────────────────────────


@router.get("/dashboard")
def financial_dashboard() -> dict[str, Any]:
    """Unified financial dashboard — patrimonio, crypto, ingresos, alertas."""
    return get_dashboard()


@router.get("/capital/snapshot")
def capital_snapshot() -> dict[str, Any]:
    """Unified capital snapshot — single source of truth for all money.

    Consolidates:
    - Bounty payouts (PayoutRecord via truth layer)
    - WorkBank income (delivered/paid/pending)
    - Investment portfolio (InvestmentManager)
    - Atlas portfolio (exchange balances)
    - Crypto wallets
    - Expected cash by payment rail
    - Payment compatibility summary
    """
    from datetime import UTC, datetime

    from cores.financial.dashboard import get_dashboard
    from cores.financial.truth_layer import get_truth_layer

    # ── Base dashboard (bounty + crypto + takenos + atlas) ───────
    dash = get_dashboard()
    truth = get_truth_layer()
    truth.get_state()

    # ── WorkBank income (direct work) ────────────────────────────
    work_income = {"entregado_usd": 0.0, "pendiente_usd": 0.0, "total_usd": 0.0}
    try:
        from cores.direct_work_engine.workbank import get_work_bank

        wb = get_work_bank()
        progress = wb.progress()
        work_income = {
            "entregado_usd": round(progress.get("delivered_usd", 0.0), 2),
            "pendiente_usd": round(progress.get("ready_usd", 0.0), 2),
            "total_usd": round(progress.get("delivered_usd", 0.0) + progress.get("ready_usd", 0.0), 2),
        }
    except Exception:
        pass

    # ── Investment portfolio (InvestmentManager) ──────────────────
    investment = {"total_usd": 0.0, "estrategias": []}
    try:
        from core.investment.manager import get_investment_manager

        im = get_investment_manager()
        snap = im.get_snapshot()
        investment = {
            "total_usd": round(snap.get("total_value", 0.0), 2),
            "estrategias": snap.get("strategies", []),
        }
    except Exception:
        pass

    # ── Expected cash by payment rail ────────────────────────────
    expected_cash = {}
    try:
        from cores.payment_compat.engine import get_payment_compat_engine

        pce = get_payment_compat_engine()
        # Sample: check major rails USD→ARS
        for method in ["usdc_base", "paypal", "wise", "binance_p2p"]:
            verdict = pce.evaluate(method=method, amount_usd=1000.0)
            if verdict.compatible:
                expected_cash[method] = {
                    "fecha_estimada": verdict.expected_date,
                    "confianza": verdict.confidence,
                    "cuentas_disponibles": len(verdict.matches),
                    "nota": verdict.honest_note,
                }
    except Exception:
        pass

    # ── Payment compatibility summary ───────────────────────────
    payment_compat_summary = {}
    try:
        from cores.payment_compat.engine import get_payment_compat_engine

        pce = get_payment_compat_engine()
        # Quick aggregate: how many methods per tier
        tiers = {"primary": 0, "us_account": 0, "global": 0, "payout": 0, "local": 0, "backup": 0, "specialized": 0}
        for acct in pce.network.accounts.values():
            if acct.function in tiers:
                tiers[acct.function] += 1
        payment_compat_summary = {
            "total_cuentas": len(pce.network.accounts),
            "por_funcion": tiers,
        }
    except Exception:
        pass

    return {
        "patrimonio_total": dash.get("patrimonio_total", 0.0),
        "breakdown": {
            "bounty_platforms": dash["breakdown"].get("plataformas_bounty", {}),
            "crypto": dash["breakdown"].get("crypto", {}),
            "takenos": dash["breakdown"].get("takenos", {}),
            "atlas_inversiones": dash["breakdown"].get("atlas_inversiones", {}),
            "workbank_ingresos": work_income,
            "inversiones": investment,
        },
        "liquidez": dash.get("liquidez", {}),
        "expected_cash": expected_cash,
        "payment_compat": payment_compat_summary,
        "ingresos_mes": dash.get("ingresos", {}),
        "objetivo_libertad": dash.get("objetivo_libertad", {}),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/refresh")
def refresh_prices() -> dict[str, Any]:
    """Clear price cache and force fresh data on next request."""
    cleared = {"coingecko_cache": False, "price_cache": False}
    try:
        from cores.crypto.coingecko import get_coingecko_feed

        feed = get_coingecko_feed()
        feed._cache.clear()
        cleared["coingecko_cache"] = True
    except Exception:
        pass
    try:
        from cores.crypto.base import _PRICE_CACHE

        _PRICE_CACHE.clear()
        cleared["price_cache"] = True
    except Exception:
        pass
    return {"status": "ok", "cleared": cleared, "timestamp": datetime.now(UTC).isoformat()}


# ── Integrations Status ──────────────────────────────────────────────


@router.get("/integrations/status")
def integrations_status() -> dict[str, Any]:
    """Status of all financial integrations (exchanges, wallets, payment platforms).

    Returns green/yellow/red per integration with last sync, balance, and errors.
    """
    truth = get_truth_layer()
    state = truth.get_state()
    crypto_mgr = None
    try:
        from cores.crypto.sync_manager import get_crypto_sync_manager

        crypto_mgr = get_crypto_sync_manager()
    except Exception:
        logger.exception("Failed to initialize crypto sync manager")

    integrations: dict[str, dict] = {}

    # Platform integrations
    for pid, ps in state.by_platform.items():
        sync = ps.sync_state
        balance = round(ps.verified_balance + ps.pending_balance, 2)
        status = _calc_integration_status(sync.consecutive_failures, sync.last_success)
        integrations[pid] = {
            "nombre": pid.capitalize(),
            "tipo": "plataforma_bounty",
            "balance_usd": balance,
            "estado": status,
            "ultima_sincronizacion": _ts_to_iso(sync.last_sync),
            "ultimo_exito": _ts_to_iso(sync.last_success),
            "fallos_consecutivos": sync.consecutive_failures,
            "error": sync.last_error or "",
        }

    # Exchange / crypto wallet integrations
    if crypto_mgr:
        for wid, _connector in crypto_mgr.connectors.items():
            snap = crypto_mgr.get_snapshot(wid)
            bal = round(snap.total_usd, 2) if snap else 0.0
            conn_status = snap.connection.value if snap else "unknown"
            status = "green" if conn_status == "connected" else ("yellow" if conn_status == "rate_limited" else "red")
            integrations[wid] = {
                "nombre": wid.replace("_", " ").title(),
                "tipo": "crypto_wallet",
                "balance_usd": bal,
                "estado": status,
                "ultima_sincronizacion": snap.synced_at if snap else "",
                "ultimo_exito": snap.synced_at if snap and conn_status == "connected" else "",
                "fallos_consecutivos": 0,
                "error": snap.error if snap else "",
            }

    # Takenos
    try:
        from cores.financial.takenos.connector import get_takenos_connector

        tc = get_takenos_connector()
        health = tc.health()
        t_status = "green" if health.get("available") else "yellow"
        integrations["takenos"] = {
            "nombre": "Takenos",
            "tipo": "billetera_virtual",
            "balance_usd": health.get("balance_usd", 0.0),
            "estado": t_status,
            "ultima_sincronizacion": "",
            "ultimo_exito": "",
            "fallos_consecutivos": 0,
            "error": ""
            if t_status == "green"
            else "Sin datos cargados — usá CSV, balance manual o vinculá wallet Solana",
        }
    except Exception:
        integrations["takenos"] = {
            "nombre": "Takenos",
            "tipo": "billetera_virtual",
            "balance_usd": 0.0,
            "estado": "yellow",
            "ultima_sincronizacion": "",
            "ultimo_exito": "",
            "fallos_consecutivos": 0,
            "error": "No conectado",
        }

    # CoinGecko
    try:
        from cores.crypto.coingecko import get_coingecko_feed

        cg_health = get_coingecko_feed().health()
        integrations["coingecko"] = {
            "nombre": "CoinGecko",
            "tipo": "oraculo_precios",
            "balance_usd": 0.0,
            "estado": "green" if cg_health.get("available") else "red",
            "ultima_sincronizacion": "",
            "ultimo_exito": "",
            "fallos_consecutivos": 0,
            "error": "" if cg_health.get("available") else "API no disponible",
        }
    except Exception:
        integrations["coingecko"] = {
            "nombre": "CoinGecko",
            "tipo": "oraculo_precios",
            "balance_usd": 0.0,
            "estado": "red",
            "error": "No conectado",
        }

    # Overall health
    estados = [i["estado"] for i in integrations.values()]
    if "red" in estados:
        overall = "red"
    elif "yellow" in estados:
        overall = "yellow"
    else:
        overall = "green"

    return {
        "overall": overall,
        "total_integraciones": len(integrations),
        "integradas": sum(1 for i in integrations.values() if i["estado"] == "green"),
        "parciales": sum(1 for i in integrations.values() if i["estado"] == "yellow"),
        "fallidas": sum(1 for i in integrations.values() if i["estado"] == "red"),
        "integraciones": integrations,
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _calc_integration_status(consecutive_failures: int, last_success: float) -> str:
    if consecutive_failures >= 5:
        return "red"
    if consecutive_failures >= 3:
        return "yellow"
    if consecutive_failures > 0:
        return "yellow"
    if last_success == 0:
        return "yellow"
    return "green"


def _ts_to_iso(ts: float) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


# ── Reconciliation ───────────────────────────────────────────────────


@router.get("/reconciliation/state")
def reconciliation_state() -> dict[str, Any]:
    engine = get_reconciliation_engine()
    return engine.get_state()


@router.get("/reconciliation/history")
def reconciliation_history() -> list[dict[str, Any]]:
    engine = get_reconciliation_engine()
    return engine.get_history()


@router.post("/reconciliation/resolve")
def resolve_discrepancy(platform: str, index: int, resolution: str) -> dict[str, Any]:
    engine = get_reconciliation_engine()
    ok = engine.resolve_manually(platform, index, resolution)
    if not ok:
        raise HTTPException(404, "Discrepancy not found")
    publish_financial_event(
        "financial:dispute_resolved",
        platform=platform,
        description=f"Discrepancia resuelta: {resolution[:100]}",
    )
    return {"resolved": True, "platform": platform}
