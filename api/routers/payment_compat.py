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


class EvaluateChainRequest(EvaluateRequest):
    final_currency: str = Field(default="ARS", description="Currency OWNEX needs to end with")


@router.get("")
async def payment_network_status() -> dict[str, Any]:
    """Overview of the OWNEX payment network."""
    engine = get_payment_engine()
    accounts = engine._network
    return {
        "summary": engine.network_summary(),
        "accounts": [account_to_dict(a) for a in accounts],
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
    return account_to_dict(account)


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
        )
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
    return {
        "compatible": verdict.compatible,
        "viable": verdict.viable,
        "score": verdict.score,
        "requirement": verdict.requirement,
        "matches": [
            {
                "account_id": m.account_id,
                "account_name": m.account_name,
                "layer": m.layer,
                "function": m.function,
                "reason": m.reason,
                "score": m.score,
            }
            for m in verdict.matches
        ],
        "off_ramp": [
            {
                "account_id": m.account_id,
                "account_name": m.account_name,
                "layer": m.layer,
                "function": m.function,
                "reason": m.reason,
                "score": m.score,
            }
            for m in verdict.off_ramp
        ],
        "missing": verdict.missing,
        "honest_notes": verdict.honest_notes,
    }
