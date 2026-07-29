from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("ownex.revenue.api")
router = APIRouter(prefix="/api/revenue", tags=["revenue"])


@router.get("/health")
async def revenue_health() -> dict[str, Any]:
    try:
        from core.revenue.engine import RevenueEngine

        engine = RevenueEngine()
        return engine.health()
    except Exception as e:
        logger.exception("Revenue health check failed")
        return {"status": "error", "error": str(e)}


@router.get("/methods")
async def payment_methods() -> dict[str, Any]:
    try:
        from core.revenue.engine import RevenueEngine

        engine = RevenueEngine()
        return {"methods": engine.available_methods()}
    except Exception as e:
        return {"error": str(e)}


@router.get("/summary")
async def revenue_summary() -> dict[str, Any]:
    try:
        from core.revenue.engine import RevenueEngine

        engine = RevenueEngine()
        return {"summary": engine.summary(), "stats": engine.get_stats().to_dict()}
    except Exception as e:
        return {"error": str(e)}


@router.post("/payment")
async def process_payment(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.revenue.engine import RevenueEngine

        engine = RevenueEngine()
        record_id = payload.get("record_id", "")
        amount = float(payload.get("amount_usd", 0))
        method = payload.get("method", "wise")
        platform = payload.get("platform", "unknown")
        payment = engine.process_payment(record_id, amount, method, platform)
        return {"success": True, "payment": payment.to_dict()}
    except Exception as e:
        logger.exception("Payment processing failed")
        return {"success": False, "error": str(e)}


@router.get("/usd-to-ars")
async def usd_to_ars(amount: float = 100, rate: float = 1000) -> dict[str, Any]:
    from core.revenue.converter import usd_to_ars

    return {"usd": amount, "ars": usd_to_ars(amount, rate), "rate": rate}
