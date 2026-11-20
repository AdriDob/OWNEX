from fastapi import APIRouter, HTTPException

from core.manage.ledger import PaymentStatus, get_revenue_ledger
from database.db import SessionLocal

router = APIRouter(prefix="/api/manage", tags=["Management"])
ledger = get_revenue_ledger()


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
async def confirm_payment(record_id: str):
    """Mark a pending payment as received."""
    success = ledger.mark_as_received(record_id)
    if not success:
        raise HTTPException(status_code=404, detail="Payment record not found")
    return {"status": "success", "message": "Payment marked as received"}


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
