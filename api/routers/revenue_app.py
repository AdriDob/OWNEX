from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("ownex.revenue.api")
router = APIRouter(prefix="/api/revenue", tags=["revenue"])


@router.get("/health")
async def revenue_health() -> dict[str, Any]:
    try:
        from cores.revenue.revenue_engine import RevenueEngine

        engine = RevenueEngine()
        return engine.health()
    except Exception as e:
        logger.exception("Revenue health check failed")
        return {"status": "error", "error": str(e)}


@router.get("/methods")
async def payment_methods() -> dict[str, Any]:
    try:
        from cores.revenue.revenue_engine import RevenueEngine

        engine = RevenueEngine()
        return {"methods": engine.available_methods()}
    except Exception as e:
        return {"error": str(e)}


# NOTE (ship-day 2026-09-28): este /summary se eliminó — duplicaba
# api/routers/revenue.py (mismo prefix `/api/revenue`, montado antes) y era
# inalcanzable por HTTP. Además su forma {summary,stats} NO era la que el
# front consume en IncomeHome (total_earned / pending_amount, que sí devuelve
# el ganador). Los demás endpoints de este router (/payment) siguen vivos.


@router.post("/payment")
async def process_payment(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from cores.revenue.revenue_engine import RevenueEngine

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
    from cores.revenue.converter import usd_to_ars

    return {"usd": amount, "ars": usd_to_ars(amount, rate), "rate": rate}
