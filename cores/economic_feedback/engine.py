"""Personal Economic Learning Engine — the closed loop.

OPPORTUNITY → PREDICTION → ACTION → OUTCOME → NET CASH/HUMAN HOUR → COMPARE → RECALIBRATE → REALLOCATE

The "one thing missing": OWNEX stops guessing what LOOKS best and learns what IS best
FOR YOU from your own money. Uses only verified outcomes (ledger PAID + human hours),
never invents. Wiring:

- Collect: LearningRecords (paid/net/fees/hours) + WorkBank human_minutes + ledger PAID
- Learn: per-channel p_cash_real, net_per_hour_real, prediction error, friction
- Recalibrate: update P(CASH) from PAID/attempted, not from headline reward
- Reallocate: rank by REALIZED NET CASH / HUMAN HOUR, suggest where to put next hour

Single source for economics.py, allocation.py, mission overview and daily loop.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.economic_feedback")

# ── Data ───────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ChannelEconomics:
    channel: str  # platform or workspace id
    attempted: int = 0
    accepted: int = 0
    paid: int = 0
    earned_gross: float = 0.0
    net_cash: float = 0.0
    fees: float = 0.0
    human_hours: float | None = None
    p_cash_real: float | None = None  # paid / attempted (None = UNKNOWN)
    acceptance_real: float | None = None  # accepted / attempted
    net_per_hour: float | None = None  # net_cash / human_hours
    avg_time_to_cash_days: float | None = None
    prediction_error_amount: float | None = None  # avg(predicted - actual) when available
    prediction_error_prob: float | None = None  # avg(predicted_prob - real_p)
    repeatability: str = "UNKNOWN"  # REPEATABLE / THIN / UNKNOWN
    verdict: str = "UNKNOWN"  # SCALE / KEEP / PAUSE / UNKNOWN
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "attempted": self.attempted,
            "accepted": self.accepted,
            "paid": self.paid,
            "earned_gross": round(self.earned_gross, 2),
            "net_cash": round(self.net_cash, 2),
            "fees": round(self.fees, 2),
            "human_hours": round(self.human_hours, 2) if self.human_hours is not None else None,
            "p_cash_real": round(self.p_cash_real, 3) if self.p_cash_real is not None else None,
            "acceptance_real": round(self.acceptance_real, 3) if self.acceptance_real is not None else None,
            "net_per_hour": round(self.net_per_hour, 2) if self.net_per_hour is not None else None,
            "avg_time_to_cash_days": round(self.avg_time_to_cash_days, 1)
            if self.avg_time_to_cash_days is not None
            else None,
            "prediction_error_amount": round(self.prediction_error_amount, 2)
            if self.prediction_error_amount is not None
            else None,
            "prediction_error_prob": round(self.prediction_error_prob, 3)
            if self.prediction_error_prob is not None
            else None,
            "repeatability": self.repeatability,
            "verdict": self.verdict,
            "note": self.note,
        }


@dataclass(slots=True)
class FeedbackSnapshot:
    generated_at: str
    total_outcomes: int
    total_paid: int
    total_net: float
    total_hours: float | None
    global_net_per_hour: float | None
    channels: list[ChannelEconomics] = field(default_factory=list)
    ranked: list[str] = field(default_factory=list)  # channel ids sorted by net_per_hour desc
    reallocation: dict[str, Any] = field(default_factory=dict)
    lesson: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_outcomes": self.total_outcomes,
            "total_paid": self.total_paid,
            "total_net": round(self.total_net, 2),
            "total_hours": round(self.total_hours, 2) if self.total_hours is not None else None,
            "global_net_per_hour": round(self.global_net_per_hour, 2) if self.global_net_per_hour is not None else None,
            "channels": [c.to_dict() for c in self.channels],
            "ranked": self.ranked,
            "reallocation": self.reallocation,
            "lesson": self.lesson,
        }


def _data_dir() -> Path:
    return Path(os.environ.get("OWNEX_DATA_DIR", "data"))


def _snapshot_path() -> Path:
    return _data_dir() / "economic_feedback" / "snapshot.json"


def _history_path() -> Path:
    return _data_dir() / "economic_feedback" / "history.jsonl"


# ── Collect ────────────────────────────────────────────────────────────


def _collect_learning_records() -> list[Any]:
    """All verified LearningRecords from the RevenueTracker (PAID + accepted counted, pending ignored)."""
    try:
        from cores.direct_work_engine.feedback import build_history_from_revenue_tracker
        from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

        tracker = get_revenue_tracker()
        if tracker is None:
            return []
        return build_history_from_revenue_tracker(tracker) or []
    except Exception as exc:
        logger.debug("economic_feedback collect LearningRecords failed: %s", exc)
        return []


def _human_hours_by_platform() -> dict[str, float]:
    """Human hours per platform from WorkBank (human_minutes_actual, summed)."""
    try:
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()
        by: dict[str, float] = {}
        for item in getattr(wb, "_items", {}).values():
            mins = getattr(item, "human_minutes_actual", None)
            if mins is None or float(mins) <= 0:
                continue
            plat = str(getattr(item, "platform", "") or "").lower()
            if not plat:
                continue
            by[plat] = by.get(plat, 0.0) + float(mins) / 60.0
        return by
    except Exception:
        return {}


def _attempts_by_platform(records: list[Any]) -> dict[str, int]:
    c: dict[str, int] = {}
    for r in records:
        p = str(getattr(r, "platform", "") or "").lower()
        if p:
            c[p] = c.get(p, 0) + 1
    return c


# ── Learn ──────────────────────────────────────────────────────────────


def compute_channel_economics() -> list[ChannelEconomics]:
    """Per-channel economics from verified outcomes + human hours. UNKNOWN when no history."""
    records = _collect_learning_records()
    if not records:
        return []
    hours_by_plat = _human_hours_by_platform()
    # Group by platform (channel)
    by_plat: dict[str, list[Any]] = {}
    for r in records:
        p = str(getattr(r, "platform", "") or "unknown").lower()
        by_plat.setdefault(p, []).append(r)

    out: list[ChannelEconomics] = []
    for plat, recs in by_plat.items():
        ch = ChannelEconomics(channel=plat)
        ch.attempted = len(recs)
        ch.accepted = sum(1 for r in recs if bool(getattr(r, "accepted", False)))
        ch.paid = sum(1 for r in recs if bool(getattr(r, "paid", False)))
        ch.earned_gross = round(sum(float(getattr(r, "amount", 0) or 0) for r in recs), 2)
        # net_amount is PAID-only cash after fees
        ch.net_cash = round(sum(float(getattr(r, "net_amount", 0) or 0) for r in recs if getattr(r, "paid", False)), 2)
        ch.fees = round(sum(float(getattr(r, "fees", 0) or 0) for r in recs), 2)
        ch.human_hours = round(hours_by_plat.get(plat, 0.0), 2) if plat in hours_by_plat else None
        # Real probabilities (only when attempted>0)
        if ch.attempted > 0:
            ch.acceptance_real = round(ch.accepted / ch.attempted, 3)
            ch.p_cash_real = round(ch.paid / ch.attempted, 3)
        # Net per hour (only when we have both net and hours)
        if ch.net_cash and ch.human_hours and ch.human_hours > 0:
            ch.net_per_hour = round(ch.net_cash / ch.human_hours, 2)
        # Time to cash
        ttc = [
            float(getattr(r, "time_to_payout_days", 0) or 0)
            for r in recs
            if getattr(r, "time_to_payout_days", None) is not None and getattr(r, "paid", False)
        ]
        if ttc:
            ch.avg_time_to_cash_days = round(sum(ttc) / len(ttc), 1)
        # Prediction errors (when snapshot existed)
        pred_amounts = [
            (float(getattr(r, "predicted_amount", 0) or 0), float(getattr(r, "net_amount", 0) or 0))
            for r in recs
            if getattr(r, "predicted_amount", None) is not None and getattr(r, "paid", False)
        ]
        if pred_amounts:
            ch.prediction_error_amount = round(sum(p - a for p, a in pred_amounts) / len(pred_amounts), 2)
        pred_probs = [
            (float(getattr(r, "predicted_probability", 0) or 0), ch.p_cash_real or 0)
            for r in recs
            if getattr(r, "predicted_probability", None) is not None
        ]
        if pred_probs:
            ch.prediction_error_prob = round(sum(p - real for p, real in pred_probs) / len(pred_probs), 3)
        # Repeatability verdict
        if ch.paid >= 3 and (ch.p_cash_real or 0) >= 0.3:
            ch.repeatability = "REPEATABLE"
        elif ch.attempted >= 3:
            ch.repeatability = (
                "THIN" if ch.paid == 0 else "REPEATABLE" if (ch.p_cash_real or 0) >= 0.5 else "NON_REPEATABLE"
            )
        else:
            ch.repeatability = "UNKNOWN"
        # Action verdict
        if ch.paid == 0 and ch.attempted >= 5:
            ch.verdict = "PAUSE"
            ch.note = f"{ch.attempted} intentos, 0 PAID → pausar, horas a canal con net/h mayor"
        elif ch.net_per_hour is not None and ch.net_per_hour >= 25:
            ch.verdict = "SCALE"
            ch.note = f"${ch.net_per_hour}/h realizado — escalar"
        elif ch.net_per_hour is not None and ch.net_per_hour < 8 and ch.attempted >= 3:
            ch.verdict = "PAUSE"
            ch.note = f"${ch.net_per_hour}/h < $8/h → no compensa, pausar"
        elif ch.paid > 0:
            ch.verdict = "KEEP"
            ch.note = f"{ch.paid} PAID, ${ch.net_cash} neto"
        else:
            ch.verdict = "UNKNOWN"
            ch.note = "Sin PAID suficiente — UNKNOWN, no se inventa"
        # Friction hint from prediction error
        if ch.prediction_error_prob is not None and ch.prediction_error_prob > 0.3:
            ch.note += f" · teoría sobre-estimó P por {ch.prediction_error_prob:.0%} (bajar prioridad)"
        out.append(ch)
    # Sort by net_per_hour desc, then paid desc, UNKNOWN bottom
    out.sort(key=lambda c: (-(c.net_per_hour if c.net_per_hour is not None else -1), -c.paid, -c.attempted))
    return out


def build_snapshot() -> FeedbackSnapshot:
    """Full feedback snapshot: global + per-channel + reallocation suggestion."""
    channels = compute_channel_economics()
    total_outcomes = sum(c.attempted for c in channels)
    total_paid = sum(c.paid for c in channels)
    total_net = round(sum(c.net_cash for c in channels), 2)
    total_hours: float | None = None
    try:
        # Sum human hours across all channels (only where measured)
        vals = [c.human_hours for c in channels if c.human_hours is not None]
        total_hours = round(sum(vals), 2) if vals else None
    except Exception:
        total_hours = None
    global_nph = round(total_net / total_hours, 2) if total_hours and total_hours > 0 else None
    ranked = [c.channel for c in channels if c.verdict in ("SCALE", "KEEP")]
    # Reallocation: where to put the next hour
    reallocation: dict[str, Any] = {}
    if channels:
        best = next((c for c in channels if c.verdict == "SCALE"), None) or (channels[0] if channels[0].paid else None)
        worst = next((c for c in channels if c.verdict == "PAUSE"), None)
        if best:
            reallocation["next_hour"] = best.channel
            reallocation["because"] = best.note
            reallocation["net_per_hour"] = best.net_per_hour
            reallocation["p_cash_real"] = best.p_cash_real
        if worst:
            reallocation["pause"] = worst.channel
            reallocation["pause_because"] = worst.note
        if not best and not worst:
            reallocation["next_hour"] = None
            reallocation["because"] = "Sin PAID suficiente — cold-start parejo hasta primer PAID"
    lesson = ""
    if total_paid == 0:
        lesson = "Sin PAID aún — tu P(CASH) real es UNKNOWN. El primer PAID desbloquea la recalibración. Hasta entonces: 1 claim Algora + assessments."
    elif global_nph is not None:
        lesson = f"Tu economía realizada: ${global_nph}/h neto ({total_paid} PAID, ${total_net} neto, {total_hours}h). El ranking usa tu plata, no promesas."
    elif channels:
        top = channels[0]
        lesson = f"Canal líder por net/h: {top.channel} → {top.note}. Ranking por dinero-real, no por headline."
    return FeedbackSnapshot(
        generated_at=datetime.now(UTC).isoformat(),
        total_outcomes=total_outcomes,
        total_paid=total_paid,
        total_net=total_net,
        total_hours=total_hours,
        global_net_per_hour=global_nph,
        channels=channels,
        ranked=ranked,
        reallocation=reallocation,
        lesson=lesson,
    )


def persist_snapshot(snapshot: FeedbackSnapshot | None = None) -> Path:
    """Persist snapshot + append to history (best-effort, never raises)."""
    snap = snapshot or build_snapshot()
    try:
        path = _snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snap.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        # Append history line
        hp = _history_path()
        hp.parent.mkdir(parents=True, exist_ok=True)
        with hp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snap.to_dict(), ensure_ascii=False) + "\n")
        return path
    except Exception as exc:
        logger.warning("persist_snapshot failed: %s", exc)
        return _snapshot_path()


def load_snapshot() -> dict[str, Any] | None:
    try:
        p = _snapshot_path()
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def get_recalibrated_p_cash() -> dict[str, float]:
    """P(CASH) recalibrado por canal desde outcomes reales (solo MEASURED)."""
    out: dict[str, float] = {}
    for ch in compute_channel_economics():
        if ch.p_cash_real is not None and ch.attempted >= 3:
            out[ch.channel] = ch.p_cash_real
    return out


def compare_prediction_vs_reality(
    predicted_amount: float | None, predicted_prob: float | None, channel: str
) -> dict[str, Any] | None:
    """For a new opportunity on `channel`, return real-p calibrated prediction or None if UNKNOWN."""
    recal = get_recalibrated_p_cash()
    if channel.lower() in recal:
        real_p = recal[channel.lower()]
        err = (predicted_prob - real_p) if predicted_prob is not None else None
        return {
            "channel": channel,
            "predicted_prob": predicted_prob,
            "real_p": real_p,
            "error": err,
            "source": "MEASURED",
        }
    return None
