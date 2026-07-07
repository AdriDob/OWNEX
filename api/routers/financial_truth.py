"""Financial Truth API — single source of truth endpoints.

Every response includes provenance, confidence, and category for every value.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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

logger = logging.getLogger("cateye.api.financial_truth")

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
