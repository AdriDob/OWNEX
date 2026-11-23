from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.manage.ledger import PaymentStatus, get_revenue_ledger
from database.db import SessionLocal

router = APIRouter(prefix="/api/manage", tags=["Management"])
ledger = get_revenue_ledger()


class ConfirmPaymentRequest(BaseModel):
    evidence: str | None = None  # transaction id, receipt URL, or confirmation reference


@router.get("/balance")
async def get_balance():
    """Get real balance and pending pipeline."""
    session = SessionLocal()
    try:
        from sqlalchemy import func

        from core.manage.ledger import RevenueRecord

        received = session.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.status == PaymentStatus.RECEIVED).scalar() or 0.0

        pending = session.query(func.sum(RevenueRecord.amount)).filter(RevenueRecord.status == PaymentStatus.PENDING).scalar() or 0.0

        return {"real_balance": received, "pending_pipeline": pending, "total_expected": received + pending}
    finally:
        session.close()


@router.post("/payment/{record_id}/confirm")
async def confirm_payment(record_id: str, body: ConfirmPaymentRequest | None = None):
    """Mark a pending payment as received. Evidence is required — a payment
    without proof never becomes verified revenue."""
    evidence = body.evidence if body else None
    session = SessionLocal()
    try:
        from core.manage.ledger import RevenueRecord

        exists = session.query(RevenueRecord.id).filter(RevenueRecord.id == record_id).first() is not None
    finally:
        session.close()
    if not exists:
        raise HTTPException(status_code=404, detail="Payment record not found")
    if not evidence:
        raise HTTPException(status_code=400, detail="Evidence required to confirm a payment (transaction id, receipt, or reference)")
    if not ledger.mark_as_received(record_id, evidence=evidence):
        raise HTTPException(status_code=400, detail="Payment could not be confirmed")
    return {"status": "success", "message": "Payment marked as received"}


@router.get("/mrr")
async def get_mrr():
    """Monthly Recurring Revenue from ACTIVE contracts + income breakdown."""
    return {"mrr_usd": ledger.get_mrr(), "income_breakdown_usd": ledger.get_income_breakdown()}


@router.get("/pipeline")
async def get_pipeline():
    """List all pending payments."""
    session = SessionLocal()
    try:
        from core.manage.ledger import PaymentStatus, RevenueRecord

        records = session.query(RevenueRecord).filter(RevenueRecord.status == PaymentStatus.PENDING).all()
        return [
            {"id": r.id, "source_id": r.source_id, "amount": r.amount, "currency": r.currency, "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in records
        ]
    finally:
        session.close()
