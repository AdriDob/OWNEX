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


# ── Acceptance Calibration (HIGH_CONFIDENCE_90) ────────────────────

ACCEPTANCE_CALIBRATION_FILENAME = "acceptance_calibration.jsonl"
ACCEPTANCE_MIN_SAMPLES = 3

# Wilson score interval constants
WILSON_Z = 1.96  # 95% CI


@dataclass(frozen=True, slots=True)
class AcceptanceCalibrationRecord:
    """One resolved acceptance prediction vs reality."""

    platform: str
    predicted_p_accept: float
    actual_accepted: bool
    program: str = ""
    niche: str = ""
    vuln_class: str = ""
    evidence_quality: float = 0.0
    recorded_at: str = ""


class AcceptanceCalibrationEngine:
    """Append-only acceptance calibration ledger + per-platform Wilson CI."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        base = Path(store_path) if store_path else _default_store()
        self.store_path = (
            base / ACCEPTANCE_CALIBRATION_FILENAME if base.is_dir() or not str(base).endswith(".jsonl") else base
        )

    def record(
        self,
        *,
        platform: str,
        program: str = "",
        niche: str = "",
        vuln_class: str = "",
        predicted_p_accept: float,
        actual_accepted: bool,
        evidence_quality: float = 0.0,
    ) -> AcceptanceCalibrationRecord:
        """Persist one resolved acceptance prediction."""
        rec = AcceptanceCalibrationRecord(
            platform=str(platform).strip().lower(),
            program=str(program).strip().lower() if program else "",
            niche=niche,
            vuln_class=str(vuln_class).strip().lower() if vuln_class else "",
            predicted_p_accept=round(float(predicted_p_accept), 4),
            actual_accepted=actual_accepted,
            evidence_quality=max(0.0, min(1.0, evidence_quality)),
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    def _load(self) -> list[AcceptanceCalibrationRecord]:
        if not self.store_path.exists():
            return []
        records: list[AcceptanceCalibrationRecord] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(AcceptanceCalibrationRecord(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("acceptance_calibration: corrupt line ignored")
        except OSError as exc:
            logger.warning("acceptance_calibration: store unreadable: %s", exc)
        return records

    def resolved_for_segment(
        self,
        platform: str = "",
        program: str = "",
        niche: str = "",
        vuln_class: str = "",
    ) -> list[AcceptanceCalibrationRecord]:
        """Resolved = has BOTH prediction and reality."""
        recs = self._load()
        if platform:
            recs = [r for r in recs if r.platform == platform.strip().lower()]
        if program:
            recs = [r for r in recs if r.program == program.strip().lower()]
        if niche:
            recs = [r for r in recs if r.niche == niche]
        if vuln_class:
            recs = [r for r in recs if r.vuln_class == vuln_class.strip().lower()]
        return [r for r in recs if r.predicted_p_accept > 0]

    def calibration_factor(
        self,
        platform: str = "",
        program: str = "",
        niche: str = "",
        vuln_class: str = "",
    ) -> tuple[float, str]:
        """Median(real/predicted) for acceptance probability — clamp [0.5, 2.0].

        Returns (factor, confidence): neutral 1.0/"insufficient_data"
        until MIN_SAMPLES resolved outcomes exist for the segment.
        """
        resolved = self.resolved_for_segment(platform, program, niche)
        ratios = [
            (1.0 if r.actual_accepted else 0.0) / r.predicted_p_accept for r in resolved if r.predicted_p_accept > 0
        ]
        if len(ratios) < ACCEPTANCE_MIN_SAMPLES:
            return 1.0, "insufficient_data"
        factor = statistics.median(ratios)
        clamped = max(0.5, min(2.0, factor))
        confidence = "high" if len(ratios) >= ACCEPTANCE_MIN_SAMPLES * 3 else "medium"
        return round(clamped, 2), confidence

    def wilson_ci(
        self,
        platform: str = "",
        program: str = "",
        niche: str = "",
        vuln_class: str = "",
    ) -> tuple[float, float, float, str]:
        """Wilson score interval for acceptance rate in a segment.

        Returns (rate, lower_bound, upper_bound, confidence_label).
        """
        resolved = self.resolved_for_segment(platform, program, niche)
        n = len(resolved)
        if n == 0:
            return 0.0, 0.0, 0.0, "insufficient_data"
        accepted = sum(1 for r in resolved if r.actual_accepted)
        rate = accepted / n

        # Wilson score interval
        z = 1.96  # 95% CI
        denominator = 1 + WILSON_Z * WILSON_Z / n
        center = rate + WILSON_Z * WILSON_Z / (2 * n)
        half_width = WILSON_Z * ((rate * (1 - rate) / n + WILSON_Z * WILSON_Z / (4 * n * n)) ** 0.5)
        lower = max(0.0, (center - half_width) / denominator)
        upper = min(1.0, (center + half_width) / denominator)

        label = (
            "none" if n == 0 else ("low" if n < 10 else ("medium" if n < 50 else ("high" if n < 100 else "very_high")))
        )
        return round(rate, 4), round(lower, 4), round(upper, 4), label


_singleton_acceptance: AcceptanceCalibrationEngine | None = None


def get_acceptance_calibration_engine() -> AcceptanceCalibrationEngine:
    global _singleton_acceptance
    if _singleton_acceptance is None:
        _singleton_acceptance = AcceptanceCalibrationEngine()
    return _singleton_acceptance
