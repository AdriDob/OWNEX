"""Payment Compatibility API — expose the OWNEX payment network.

Deterministic verdicts: given a payment method, currency and required
region, the engine reports which OWNEX accounts can collect the payout
and whether the full receive + off-ramp chain is viable.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.payment_compat.engine import (
    PaymentRequirement,
    account_to_dict,
    get_account_or_none,
    get_payment_engine,
)

logger = logging.getLogger("ownex.api.payment_compat")

router = APIRouter(prefix="/api/payment-compat", tags=["payment_compat"])


class EvaluateRequest(BaseModel):
    method: str = Field(
        default="crypto", description="Payout method (ach, wire, sepa, cbu, cvu, paypal, crypto, p2p...)"
    )
    currency: str = Field(default="USDC", description="Currency of the payout")
    region: str = Field(default="global", description="Jurisdiction required (usa, argentina, eu, global)")
    amount: float = Field(default=0.0, description="Expected payout amount in USD")
    required_documentation: str = Field(
        default="", description="Documentation the platform demands (kyc, llc, us_residency...)"
    )
    platform: str = Field(default="", description="Platform paying the bounty")
    require_configured: bool = Field(
        default=False,
        description="MONEY VALIDATION: only rails the user configured count (P_REWARD on real rails)",
    )


class EvaluateChainRequest(EvaluateRequest):
    final_currency: str = Field(default="ARS", description="Currency OWNEX needs to end with")


@router.get("")
async def payment_network_status() -> dict[str, Any]:
    """Overview of the OWNEX payment network."""
    engine = get_payment_engine()
    accounts = engine._network
    return {
        "summary": engine.network_summary(),
        "configured_accounts": engine.get_configured_accounts(),
        "accounts": [{**account_to_dict(a), "status": engine.account_status(a.id)} for a in accounts],
    }


@router.get("/network")
async def payment_network_grouped() -> dict[str, Any]:
    """Catalog grouped by layer and function."""
    engine = get_payment_engine()
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for account in engine._network:
        layer = account.layer.value
        function = account.function.value
        grouped.setdefault(layer, {}).setdefault(function, []).append(account_to_dict(account))
    return {"grouped": grouped}


@router.get("/account/{account_id}")
async def payment_account_detail(account_id: str) -> dict[str, Any]:
    """Detail of a single account."""
    account = get_account_or_none(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return {**account_to_dict(account), "status": get_payment_engine().account_status(account_id)}


class ConfiguredAccountsRequest(BaseModel):
    account_ids: list[str] = Field(default_factory=list, description="Catalog account ids the user really owns")


@router.get("/configured")
async def payment_configured() -> dict[str, Any]:
    """Rails the user marked as theirs (MONEY VALIDATION: P_REWARD source)."""
    engine = get_payment_engine()
    return {"configured_accounts": engine.get_configured_accounts(), "statuses": engine.list_account_statuses()}


@router.post("/configured")
async def payment_set_configured(request: ConfiguredAccountsRequest) -> dict[str, Any]:
    """Mark catalog accounts as owned rails. Unknown ids -> 404 (never assumed)."""
    unknown = [a for a in request.account_ids if get_account_or_none(a) is None]
    if unknown:
        raise HTTPException(status_code=404, detail=f"Unknown accounts (not in catalog): {', '.join(unknown)}")
    engine = get_payment_engine()
    engine.set_configured_accounts(list(request.account_ids))
    return {"configured_accounts": engine.get_configured_accounts()}


@router.post("/evaluate")
async def payment_evaluate(request: EvaluateRequest) -> dict[str, Any]:
    """Decide whether OWNEX can collect a payout for the given requirement."""
    engine = get_payment_engine()
    verdict = engine.evaluate(
        PaymentRequirement(
            method=request.method,
            currency=request.currency,
            region=request.region,
            amount=request.amount,
            required_documentation=request.required_documentation,
            platform=request.platform,
        ),
        require_configured=request.require_configured,
    )
    return _verdict_dict(verdict)


@router.post("/evaluate/chain")
async def payment_evaluate_chain(request: EvaluateChainRequest) -> dict[str, Any]:
    """Decide whether OWNEX can receive AND convert to the final currency."""
    engine = get_payment_engine()
    verdict = engine.evaluate_chain(
        PaymentRequirement(
            method=request.method,
            currency=request.currency,
            region=request.region,
            amount=request.amount,
            required_documentation=request.required_documentation,
            platform=request.platform,
        ),
        final_currency=request.final_currency,
    )
    return _verdict_dict(verdict)


def _verdict_dict(verdict: Any) -> dict[str, Any]:
    def _match_dict(m: Any) -> dict[str, Any]:
        return {
            "account_id": m.account_id,
            "account_name": m.account_name,
            "layer": m.layer,
            "function": m.function,
            "reason": m.reason,
            "score": m.score,
            "configured": bool(getattr(m, "configured", False)),
        }

    return {
        "compatible": verdict.compatible,
        "viable": verdict.viable,
        "score": verdict.score,
        "configured_matches": int(getattr(verdict, "configured_matches", 0)),
        "requirement": verdict.requirement,
        "matches": [_match_dict(m) for m in verdict.matches],
        "off_ramp": [_match_dict(m) for m in verdict.off_ramp],
        "missing": verdict.missing,
        "honest_notes": verdict.honest_notes,
    }
