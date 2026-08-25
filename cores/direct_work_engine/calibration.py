"""Prediction calibration loop — Income Multiplier Fase D (spec §13).

Closes the loop: OWNEX predicts $X/hour for a platform, reality delivers
$Y/hour, and the prediction error is PERSISTED so future recommendations
shrink instead of repeating a stale curated number forever.

Storage: append-only JSONL at ``data/learning/calibration.jsonl`` (one
line per resolved outcome) — survives restarts, diffable, no DB
migration needed.

Multiplier semantics: platform_factor = median(real / predicted),
clamped to [0.5, 2.0]. Applied by callers as EV × factor. With fewer
than MIN_SAMPLES the factor is neutral 1.0 and confidence="low" —
never invented.
"""

from __future__ import annotations

import json
import logging
import os
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger("ownex.revenue.calibration")

CALIBRATION_FILENAME = "calibration.jsonl"
MIN_SAMPLES = 3
FACTOR_CLAMP = (0.5, 2.0)


def _default_store() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR", "data")
    return Path(base) / "learning" / CALIBRATION_FILENAME


@dataclass(frozen=True, slots=True)
class PredictionRecord:
    platform: str
    predicted_hourly: float
    actual_hourly: float | None  # None while pending
    predicted_income_usd: float | None = None
    actual_income_usd: float | None = None
    opportunity_id: str | None = None
    error_pct: float | None = None  # (real-pred)/pred * 100, negative = overpromise
    recorded_at: str = ""


class CalibrationEngine:
    """Append-only prediction ledger + per-platform correction factors."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self.store_path = Path(store_path) if store_path else _default_store()

    # ── Write ──

    def record(
        self,
        *,
        platform: str,
        predicted_hourly: float,
        actual_hourly: float | None = None,
        predicted_income_usd: float | None = None,
        actual_income_usd: float | None = None,
        opportunity_id: str | None = None,
    ) -> PredictionRecord:
        """Persist one prediction (actual=None) or its resolution."""
        error_pct = None
        if actual_hourly is not None and predicted_hourly:
            error_pct = round((actual_hourly - predicted_hourly) / predicted_hourly * 100, 1)

        rec = PredictionRecord(
            platform=str(platform).strip().lower(),
            predicted_hourly=round(float(predicted_hourly), 2),
            actual_hourly=round(float(actual_hourly), 2) if actual_hourly is not None else None,
            predicted_income_usd=predicted_income_usd,
            actual_income_usd=actual_income_usd,
            opportunity_id=opportunity_id,
            error_pct=error_pct,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    # ── Read ──

    def _load(self) -> list[PredictionRecord]:
        if not self.store_path.exists():
            return []
        records: list[PredictionRecord] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    d = json.loads(line)
                    records.append(PredictionRecord(**d))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("calibration: línea corrupta ignorada")
        except OSError as exc:
            logger.warning("calibration: store ilegible: %s", exc)
        return records

    def resolved_for_platform(self, platform: str) -> list[PredictionRecord]:
        """Resolved = has BOTH prediction and reality."""
        key = str(platform).strip().lower()
        return [r for r in self._load() if r.platform == key and r.predicted_hourly > 0 and r.actual_hourly is not None]

    # ── Correction factor ──

    def platform_factor(self, platform: str) -> tuple[float, str]:
        """Median(real/predicted) clamped — multiply EV by this.

        Returns (factor, confidence): neutral 1.0/"insufficient_data"
        until MIN_SAMPLES resolved outcomes exist for the platform.
        """
        resolved = self.resolved_for_platform(platform)
        ratios = [
            r.actual_hourly / r.predicted_hourly
            for r in resolved
            if r.predicted_hourly > 0 and r.actual_hourly is not None
        ]
        if len(ratios) < MIN_SAMPLES:
            return 1.0, "insufficient_data"
        factor = statistics.median(ratios)
        clamped = max(FACTOR_CLAMP[0], min(FACTOR_CLAMP[1], factor))
        confidence = "high" if len(ratios) >= MIN_SAMPLES * 3 else "medium"
        return round(clamped, 2), confidence

    def worst_overpromises(self, limit: int = 5) -> list[PredictionRecord]:
        """Platforms whose predictions failed hardest — dashboard feed."""
        out: list[PredictionRecord] = []
        seen: set[str] = set()
        for rec in sorted(
            (r for r in self._load() if r.error_pct is not None),
            key=lambda r: float(r.error_pct or 0.0),
        ):
            if rec.platform in seen:
                continue
            seen.add(rec.platform)
            out.append(rec)
            if len(out) >= limit:
                break
        return out


_singleton: CalibrationEngine | None = None


def get_calibration_engine() -> CalibrationEngine:
    global _singleton
    if _singleton is None:
        _singleton = CalibrationEngine()
    return _singleton
