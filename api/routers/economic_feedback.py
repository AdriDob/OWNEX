"""Economic Feedback — Personal Economic Learning Engine.

Exposes the closed loop: PREDICTION → OUTCOME → NET/H → RECALIBRATE → REALLOCATE.
Uses only verified outcomes (ledger PAID + human hours), never invents.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from cores.economic_feedback.engine import build_snapshot, compute_channel_economics, persist_snapshot

router = APIRouter(prefix="/api/economic-feedback", tags=["economic-feedback"])


@router.get("/snapshot")
async def feedback_snapshot(persist: bool = False) -> dict[str, Any]:
    """Full feedback snapshot: per-channel p_cash_real, net_per_hour, verdict, reallocation."""
    snap = build_snapshot()
    if persist:
        persist_snapshot(snap)
    return snap.to_dict()


@router.get("/channels")
async def feedback_channels() -> dict[str, Any]:
    """Per-channel economics ranked by REALIZED net/h."""
    channels = compute_channel_economics()
    return {"channels": [c.to_dict() for c in channels]}


@router.get("/recalibrated-p-cash")
async def feedback_recalibrated() -> dict[str, Any]:
    """P(CASH) recalibrado por canal desde outcomes reales (solo MEASURED)."""
    from cores.economic_feedback.engine import get_recalibrated_p_cash

    return {"p_cash_real": get_recalibrated_p_cash()}


class RecordOutcomeIn(BaseModel):
    platform: str = Field(description="Platform/channel id, e.g. algora, mercor, mercado_libre")
    accepted: bool = Field(default=False, description="Was the attempt accepted?")
    paid: bool = Field(default=False, description="Was cash received?")
    amount: float = Field(default=0.0, description="Gross amount")
    net_amount: float | None = Field(default=None, description="Net after fees (None=unknown)")
    fees: float = Field(default=0.0)
    predicted_amount: float | None = None
    predicted_probability: float | None = None
    actual_hours: float | None = Field(default=None, description="Human hours for this outcome")


@router.post("/record-outcome")
async def feedback_record_outcome(payload: RecordOutcomeIn) -> dict[str, Any]:
    """Record one verified outcome (enriches the learning loop). Best-effort."""
    try:
        from cores.direct_work_engine.feedback import LearningRecord

        # Record via direct file fallback if tracker missing
        rec = LearningRecord(
            platform=payload.platform,
            accepted=payload.accepted,
            amount=payload.amount,
            category=None,
            paid=payload.paid,
            net_amount=payload.net_amount,
            fees=payload.fees,
            predicted_amount=payload.predicted_amount,
            predicted_probability=payload.predicted_probability,
            actual_hours=payload.actual_hours,
        )
        # Persist to history JSONL so snapshot includes it even before tracker sync
        import json
        import os
        from pathlib import Path

        path = Path(os.environ.get("OWNEX_DATA_DIR", "data")) / "learning" / "acceptance_outcomes.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "platform": rec.platform,
                        "accepted": rec.accepted,
                        "paid": rec.paid,
                        "amount": rec.amount,
                        "net_amount": rec.net_amount,
                        "fees": rec.fees,
                        "predicted_amount": rec.predicted_amount,
                        "predicted_probability": rec.predicted_probability,
                        "actual_hours": rec.actual_hours,
                    }
                )
                + "\n"
            )
        return {"success": True, "recorded": rec.platform}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/recalibrate")
async def feedback_recalibrate() -> dict[str, Any]:
    """Force recalibration and persist snapshot (daily job also does this)."""
    snap = build_snapshot()
    path = persist_snapshot(snap)
    return {"success": True, "snapshot": snap.to_dict(), "persisted_at": str(path)}
