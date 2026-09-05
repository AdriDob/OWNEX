"""Predictive Target Prioritization — empirical, on-device, zero-ML-deps.

Leans on verified payout/finding history (RevenueTracker is the SSOT for
outcomes) to produce a 7-day forecast ranking targets by:

    predicted EV / hour = P(accepted) × reward / human_hours

Every probability is either empirical (from real outcomes, clamped to avoid
overconfidence on tiny samples) or explicitly labelled UNKNOWN. Never invented.
"""

from __future__ import annotations

import logging
import os
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.learning.predictive")

# Clamp bounds for empirical acceptance (avoid overconfidence on 1-2 samples).
MIN_ACCEPTANCE, MAX_ACCEPTANCE = 0.05, 0.95
# Minimum samples before an empirical rate is considered "learned".
MIN_SAMPLES_FOR_CONFIDENCE = 3
# Days included in the recent-payout recency signal.
RECENCY_WINDOW_DAYS = 90
# Default daily human capacity (hours) for the forecast.
DEFAULT_DAILY_HOURS = 4.0


@dataclass
class PredictiveTargetRank:
    """A target ranked by predicted EV/hour from empirical history."""

    target_id: str
    target_name: str
    platform: str | None = None
    program: str | None = None
    reward_estimate: float = 0.0
    human_hours: float = 4.0
    acceptance_probability: float = 0.5  # empirical or UNKNOWN
    acceptance_source: str = "unknown"  # empirical | unknown
    sample_count: int = 0
    predicted_ev: float = 0.0
    predicted_ev_per_hour: float = 0.0
    velocity_days: float | None = None
    recency_bonus: float = 1.0
    confidence: str = "low"
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "platform": self.platform,
            "program": self.program,
            "reward_estimate": round(self.reward_estimate, 2),
            "human_hours": round(self.human_hours, 2),
            "acceptance_probability": round(self.acceptance_probability, 3),
            "acceptance_source": self.acceptance_source,
            "sample_count": self.sample_count,
            "predicted_ev": round(self.predicted_ev, 2),
            "predicted_ev_per_hour": round(self.predicted_ev_per_hour, 2),
            "velocity_days": self.velocity_days,
            "recency_bonus": round(self.recency_bonus, 3),
            "confidence": self.confidence,
            "reasoning": self.reasoning,
        }


class PredictivePrioritizer:
    """Empirical target prioritizer for the next 7 days."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        base = os.environ.get("OWNEX_DATA_DIR")
        self.data_dir = (
            Path(data_dir) if data_dir else (Path(base) if base else Path(__file__).resolve().parents[3] / "data")
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.forecast_file = self.data_dir / "predictive_forecast.json"
        self._saved_forecast: dict[str, Any] | None = None

    # ── Outcome history (SSOT: RevenueTracker) ─────────────────────

    def _platform_outcomes(self) -> dict[str, dict[str, Any]]:
        """Per-platform verified outcome stats from RevenueTracker.

        Only terminal statuses count as samples; pending/reviewing never do.
        Returns {platform: {accepted, rejected, samples, acceptance}}.
        """
        stats: dict[str, dict[str, Any]] = {}
        with suppress(Exception):
            from cores.revenue_tracker.revenue_tracker import PaymentStatus, get_revenue_tracker

            tracker = get_revenue_tracker()
            if not tracker:
                return stats
            for opp in tracker.opportunities.values():
                status = getattr(opp, "status", None)
                platform = str(getattr(opp, "platform", "") or "").lower()
                if not platform:
                    continue
                s = stats.setdefault(platform, {"accepted": 0, "rejected": 0, "samples": 0})
                # Terminal accepted/rejected evidence: PAID & ACCEPTED count as a
                # won outcome (money only counts in PAID; ACCEPTED is strong
                # pipeline evidence of acceptance). FAILED/CANCELLED are losses.
                if status in (PaymentStatus.PAID, PaymentStatus.ACCEPTED):
                    s["accepted"] += 1
                    s["samples"] += 1
                elif status in (PaymentStatus.FAILED, PaymentStatus.CANCELLED):
                    s["rejected"] += 1
                    s["samples"] += 1
            for s in stats.values():
                s["acceptance"] = clamp(s["accepted"] / s["samples"]) if s["samples"] else None
        return stats

    @staticmethod
    def _velocity_days() -> dict[str, float]:
        """Average days-to-payment per platform from verified history."""
        with suppress(Exception):
            from core.revenue.metrics import RevenueMetrics

            metrics = RevenueMetrics()
            return {k: float(v) for k, v in metrics.platform_speed_days().items() if v}
        return {}

    # ── Forecast ───────────────────────────────────────────────────

    def forecast(
        self,
        candidates: list[dict[str, Any]],
        daily_hours: float = DEFAULT_DAILY_HOURS,
    ) -> dict[str, Any]:
        """Rank candidate targets for the next 7 days by predicted EV/hour.

        Each candidate dict: {id, name, platform?, program?, reward?, hours?,
        severity?, last_finding_days_ago?}.

        Probabilities are empirical from RevenueTracker outcomes, clamped;
        when no history exists the rate is UNKNOWN (0.5 labelled), never assumed.
        """
        platform_outcomes = self._platform_outcomes()
        velocities = self._velocity_days()
        now = datetime.now(UTC)

        ranks: list[PredictiveTargetRank] = []
        for cand in candidates:
            pid = str(cand.get("id") or "")
            name = cand.get("name") or cand.get("title") or pid
            platform = str(cand.get("platform") or "").lower() or None
            program = cand.get("program") or None

            reward = float(cand.get("reward") or cand.get("estimated_reward") or 0) or self._default_reward(platform)
            hours = float(cand.get("hours") or cand.get("estimated_hours") or 0) or DEFAULT_DAILY_HOURS

            out = platform_outcomes.get(platform, {}) if platform else {}
            samples = int(out.get("samples", 0))
            acceptance = out.get("acceptance")
            if acceptance is not None:
                prob = acceptance
                source = "empirical"
            else:
                prob = 0.5
                source = "unknown"

            # Velocity from verified history, else UNKNOWN (None).
            velocity = velocities.get(platform) if platform else None

            # Recency bonus: programs with a finding touched recently rank higher.
            days_ago = cand.get("last_finding_days_ago")
            recency = 1.0
            if days_ago is not None:
                try:
                    rd = float(days_ago)
                    recency = 1.0 if rd <= 7 else max(0.6, 1.0 - rd / RECENCY_WINDOW_DAYS)
                except (TypeError, ValueError):
                    recency = 1.0

            predicted_ev = reward * prob * recency
            predicted_ev_per_hour = predicted_ev / max(hours, 0.5)

            confidence = "low"
            if samples >= MIN_SAMPLES_FOR_CONFIDENCE and source == "empirical":
                confidence = "medium" if samples >= 10 else "high" if samples >= 25 else "medium"

            reasoning_parts = []
            if source == "empirical":
                reasoning_parts.append(f"{samples} outcome(s) → P={prob:.2f}")
            else:
                reasoning_parts.append("sin historial verificado → P=UNKNOWN (0.5)")
            if velocity:
                reasoning_parts.append(f"pago en ~{velocity:.0f}d")
            if cand.get("last_finding_days_ago") is not None:
                reasoning_parts.append(f"actividad hace {days_ago}d")
            reasoning = " · ".join(reasoning_parts)

            ranks.append(
                PredictiveTargetRank(
                    target_id=pid,
                    target_name=str(name),
                    platform=platform,
                    program=program,
                    reward_estimate=round(reward, 2),
                    human_hours=round(hours, 2),
                    acceptance_probability=round(prob, 3),
                    acceptance_source=source,
                    sample_count=samples,
                    predicted_ev=predicted_ev,
                    predicted_ev_per_hour=predicted_ev_per_hour,
                    velocity_days=float(velocity) if velocity else None,
                    recency_bonus=round(recency, 3),
                    confidence=confidence,
                    reasoning=reasoning,
                )
            )

        ranks.sort(key=lambda r: r.predicted_ev_per_hour, reverse=True)

        # 7-day capacity forecast from the top ranks.
        forecast: dict[str, Any] = {
            "generated_at": now.isoformat(),
            "horizon_days": 7,
            "daily_hours": daily_hours,
            "ranked": [r.to_dict() for r in ranks],
            "top_pick": ranks[0].to_dict() if ranks else None,
            "capacity": {
                "available_hours_7d": round(daily_hours * 7, 1),
                "expected_value_7d": round(sum(r.predicted_ev for r in ranks[:5]), 2),
            },
        }
        self._persist(forecast, now)
        return forecast

    @staticmethod
    def _default_reward(platform: str | None) -> float:
        """Honest default reward by platform from curated platform guides."""
        table = {
            "bugcrowd": 500.0,
            "hackerone": 500.0,
            "intigriti": 400.0,
            "yeswehack": 400.0,
            "opire": 150.0,
            "issuehunt": 150.0,
            "algora": 200.0,
            "freelancer": 300.0,
            "outlier": 250.0,
            "mindrift": 200.0,
        }
        return table.get((platform or "").lower(), 200.0)

    # ── Persistence ────────────────────────────────────────────────

    def _persist(self, forecast: dict[str, Any], now: datetime) -> None:
        self._saved_forecast = forecast
        with suppress(Exception):
            history: dict[str, Any] = {}
            if self.forecast_file.exists():
                with open(self.forecast_file, encoding="utf-8") as f:
                    import json

                    history = json.load(f)
            history[now.strftime("%Y-%m-%dT%H")] = forecast
            # Keep only recent 7 days of forecasts.
            cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H")
            history = {k: v for k, v in history.items() if k >= cutoff}
            with open(self.forecast_file, "w", encoding="utf-8") as f:
                import json

                json.dump(history, f, indent=2, ensure_ascii=False)

    def latest_forecast(self) -> dict[str, Any] | None:
        if self._saved_forecast:
            return self._saved_forecast
        with suppress(Exception):
            import json

            if self.forecast_file.exists():
                with open(self.forecast_file, encoding="utf-8") as f:
                    history = json.load(f)
                if history:
                    latest_key = sorted(history)[-1]
                    self._saved_forecast = history[latest_key]
                    return self._saved_forecast
        return None


def clamp(value: float, lo: float = MIN_ACCEPTANCE, hi: float = MAX_ACCEPTANCE) -> float:
    return max(lo, min(hi, value))


# ── Singleton ──────────────────────────────────────────────────────

_prioritizer: PredictivePrioritizer | None = None


def get_predictive_prioritizer() -> PredictivePrioritizer:
    global _prioritizer
    if _prioritizer is None:
        _prioritizer = PredictivePrioritizer()
    return _prioritizer


# ── Entry points ───────────────────────────────────────────────────


def build_candidates_from_targets(
    targets: list[Any],
    outcome_map: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Convert target objects (ORM or dicts) to candidate dicts.

    ``outcome_map`` may supply per-target last_finding_days_ago / reward from
    historical DB data; if omitted, neutral values are used.
    """
    candidates: list[dict[str, Any]] = []
    for t in targets:
        attrs = t if isinstance(t, dict) else _orm_to_dict(t)
        info = (outcome_map or {}).get(str(attrs.get("id", "")), {})
        candidates.append(
            {
                "id": attrs.get("id", ""),
                "name": attrs.get("name") or attrs.get("title", ""),
                "platform": attrs.get("platform") or info.get("platform"),
                "program": info.get("program"),
                "reward": info.get("reward"),
                "hours": info.get("hours"),
                "last_finding_days_ago": info.get("last_finding_days_ago"),
            }
        )
    return candidates


def _orm_to_dict(obj: Any) -> dict[str, Any]:
    return {col: getattr(obj, col) for col in ("id", "name", "title", "platform", "domain") if hasattr(obj, col)}


def predict_targets(
    candidates: list[dict[str, Any]],
    daily_hours: float = DEFAULT_DAILY_HOURS,
) -> dict[str, Any]:
    """Public helper: predict + rank candidates for the next 7 days."""
    return get_predictive_prioritizer().forecast(candidates, daily_hours=daily_hours)
