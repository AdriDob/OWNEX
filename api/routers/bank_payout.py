"""Bank Payout Router — API endpoints for bank payout connector."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cores.financial.bank_payout import get_bank_payout_connector

router = APIRouter(prefix="/api/bank-payout", tags=["bank-payout"])


class PlaidLinkTokenRequest(BaseModel):
    user_id: str


class PlaidExchangeRequest(BaseModel):
    public_token: str


class PlaidSyncRequest(BaseModel):
    access_token: str
    cursor: str = ""


class CSVImportRequest(BaseModel):
    file_path: str
    account_name: str


class WebhookPayload(BaseModel):
    source: str = "plaid"
    payload: dict = {}


@router.post("/plaid/link-token")
def create_link_token(req: PlaidLinkTokenRequest):
    connector = get_bank_payout_connector()
    if not connector._plaid_provider:
        raise HTTPException(status_code=503, detail="Plaid not configured")
    result = connector._plaid_provider.create_link_token(req.user_id)
    return {"status": "ok", "link_token": result.get("link_token", "")}


@router.post("/plaid/exchange")
def exchange_public_token(req: PlaidExchangeRequest):
    connector = get_bank_payout_connector()
    if not connector._plaid_provider:
        raise HTTPException(status_code=503, detail="Plaid not configured")
    result = connector._plaid_provider.exchange_public_token(req.public_token)
    return {
        "status": "ok",
        "access_token": result.get("access_token", "")[:16] + "...",
        "item_id": result.get("item_id", ""),
    }


@router.post("/plaid/sync")
def sync_plaid_transactions(req: PlaidSyncRequest):
    connector = get_bank_payout_connector()
    if not connector._plaid_provider:
        raise HTTPException(status_code=503, detail="Plaid not configured")
    result = connector._plaid_provider.sync_transactions(req.access_token, req.cursor)
    return {
        "status": "ok",
        "added": len(result.get("added", [])),
        "modified": len(result.get("modified", [])),
        "removed": len(result.get("removed", [])),
        "next_cursor": result.get("next_cursor", ""),
        "has_more": result.get("has_more", False),
    }


@router.post("/csv/import")
def import_csv(req: CSVImportRequest):
    connector = get_bank_payout_connector()
    detected = connector.import_csv(req.file_path, req.account_name)
    return {
        "status": "ok",
        "imported": len(detected),
        "payouts": [
            {
                "transaction_id": p.transaction_id,
                "amount": p.amount,
                "currency": p.currency,
                "date": p.date,
                "description": p.description,
                "platform": p.platform,
                "confidence": p.confidence,
            }
            for p in detected
        ],
    }


@router.get("/status")
def connector_status():
    connector = get_bank_payout_connector()
    return connector.get_status()


@router.post("/webhook")
def receive_webhook(data: WebhookPayload):
    connector = get_bank_payout_connector()
    if data.source == "plaid":
        entries = connector.handle_plaid_webhook(data.payload)
    else:
        entries = connector.handle_custom_webhook(data.payload)
    return {
        "status": "ok",
        "events_processed": len(entries),
        "payouts": [
            {
                "transaction_id": p.transaction_id,
                "amount": p.amount,
                "platform": p.platform,
            }
            for p in entries
        ],
    }


@router.get("/detected")
def list_detected_payouts():
    connector = get_bank_payout_connector()
    return {
        "status": "ok",
        "payouts": connector.get_detected_payouts(),
        "total": len(connector._detected_payouts),
    }
