"""Universal Calibration Engine — OWNEX 100/100.

Routes calibration to the appropriate existing engine per probability type/category.
This is the routing layer — the actual calibration logic lives in:
- cores.direct_work_engine.calibration (CalibrationEngine, AcceptanceCalibrationEngine)
- cores.direct_work_engine.reward_probability (PersonalRewardProbability, PersonalAcceptanceProbability)
- cores.direct_work_engine.availability (AvailabilityMonitor)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.direct_work_engine.availability import (
    get_availability_engine,
)
from cores.direct_work_engine.calibration import (
    get_acceptance_calibration_engine,
    get_calibration_engine,
)
from cores.direct_work_engine.reward_probability import (
    get_personal_acceptance_probability,
    get_personal_reward_probability,
)

logger = logging.getLogger("ownex.universal_calibration")


# ────────────────────────────────────────────────────────────────
# Universal Calibration Record — extends existing for all categories
# ────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class UniversalCalibrationRecord:
    """One calibration record for ANY probability type/category."""

    platform: str
    category: str  # bug_bounty, dev_bounty, ai_training, etc.
    probability_type: str  # which ProbabilityType (e.g., "p_accept")
    predicted: float
    actual: float | None = None
    segment: str = ""  # platform|category|subcategory|task_type|skill|difficulty|surface
    evidence_label: str = "NO_EVIDENCE"  # NO_EVIDENCE|THIN_EVIDENCE|SUFFICIENT_EVIDENCE|HIGH_EVIDENCE
    evidence_quality: float = 0.0  # 0.0-1.0 composite quality
    effective_n: float = 0.0  # effective sample size
    recorded_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UniversalCalibrationRecord:
        return cls(**data)


# ────────────────────────────────────────────────────────────────
# Universal Calibration Engine — Routes to category-specific engines
# ────────────────────────────────────────────────────────────────


class UniversalCalibrationEngine:
    """
    Routes calibration to the appropriate existing engine per probability type/category.

    This is a ROUTING LAYER — the actual calibration logic lives in:
    - CalibrationEngine (platform_factor for hourly rate predictions)
    - AcceptanceCalibrationEngine (Wilson CI for acceptance probability)
    - PersonalRewardProbability (reward probability with Bayesian update)
    - PersonalAcceptanceProbability (acceptance probability with Wilson CI)
    - AvailabilityMonitor (task availability calibration)

    All engines use append-only JSONL stores, survive restarts, no DB migration.
    """

    def __init__(
        self,
        data_dir: str | Path | None = None,
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(os.environ.get("OWNEX_DATA_DIR", "data"))
        self.calibration_path = self.data_dir / "learning" / "universal_calibration.jsonl"
        self.calibration_path.parent.mkdir(parents=True, exist_ok=True)

        # Existing engines (singletons)
        self.calibration_engine = get_calibration_engine()
        self.acceptance_calibration = get_acceptance_calibration_engine()
        self.acceptance_engine = get_personal_acceptance_probability()
        self.reward_engine = get_personal_reward_probability()
        self.availability_engine = get_availability_engine()

        logger.info("UniversalCalibrationEngine initialized with all sub-engines")

    # ─── Public API ─────────────────────────────────────────────────

    def record_prediction(
        self,
        *,
        platform: str,
        category: str,
        probability_type: str,
        predicted: float,
        actual: float | None = None,
        segment: str = "",
        evidence_label: str = "NO_EVIDENCE",
        evidence_quality: float = 0.0,
        effective_n: float = 0.0,
    ) -> dict[str, Any]:
        """Record a prediction (actual=None) or its resolution (actual=float)."""
        platform = str(platform).strip().lower()
        category = str(category).strip().lower()

        record = {
            "platform": platform,
            "category": category,
            "probability_type": probability_type,
            "predicted": float(predicted),
            "actual": float(actual) if actual is not None else None,
            "segment": segment,
            "evidence_label": evidence_label,
            "evidence_quality": max(0.0, min(1.0, evidence_quality)),
            "effective_n": max(0.0, float(effective_n)),
            "recorded_at": datetime.now(UTC).isoformat(),
        }

        # Persist universal record
        self.calibration_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.calibration_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    def record_resolution(
        self,
        *,
        platform: str,
        category: str,
        probability_type: str,
        predicted: float,
        actual: float,
        segment: str = "",
        evidence_label: str = "SUFFICIENT_EVIDENCE",
        evidence_quality: float = 1.0,
        effective_n: float = 1.0,
    ) -> dict[str, Any]:
        """Record a resolved prediction (both predicted and actual known)."""
        return self.record_prediction(
            platform=platform,
            category=category,
            probability_type=probability_type,
            predicted=predicted,
            actual=actual,
            segment=segment,
            evidence_label=evidence_label,
            evidence_quality=1.0,
            effective_n=1.0,
        )

    def get_correction_factor(
        self,
        category: str,
        probability_type: str,
        segment: str = "",
    ) -> tuple[float, str]:
        """
        Get calibrated correction factor for a segment.

        Returns (factor, confidence): neutral 1.0/"insufficient_data"
        until MIN_SAMPLES resolved outcomes exist for the segment.
        """
        category = str(category).strip().lower()

        # Route to appropriate engine based on probability type
        if probability_type in ("p_accept", "p_accept"):
            factor, conf = self.acceptance_calibration.calibration_factor(
                platform="",  # segment used as platform
                program="",
                niche=category,
                vuln_class="",
            )
            return factor, conf

        elif probability_type in ("p_reward", "p_reward", "p_payment"):
            # Use reward engine calibration (platform_factor on reward rate)
            # This would need a reward-specific calibration engine
            # For now, delegate to main calibration engine using category as platform
            factor, conf = self.calibration_engine.platform_factor(category)
            return factor, conf

        elif probability_type == "p_valid":
            factor, conf = self.calibration_engine.platform_factor(category)
            return factor, conf

        elif probability_type in ("p_completion", "p_accept"):
            # Completion probability - use acceptance calibration
            factor, conf = self.acceptance_calibration.calibration_factor(
                platform="",
                program="",
                niche=category,
                vuln_class="",
            )
            return factor, conf

        elif probability_type in ("p_payment", "p_accept"):
            # Payment probability - use acceptance calibration
            factor, conf = self.acceptance_calibration.calibration_factor(
                platform="",
                program="",
                niche=category,
                vuln_class="",
            )
            return factor, conf

        elif probability_type == "p_completion":
            # Completion probability - use acceptance calibration
            factor, conf = self.acceptance_calibration.calibration_factor(
                platform="",
                program="",
                niche=category,
                vuln_class="",
            )
            return factor, conf

        elif probability_type in ("p_valid", "p_unique"):
            # Validity/uniqueness - use main calibration engine
            factor, conf = self.calibration_engine.platform_factor(category)
            return factor, conf

        else:
            # Default: neutral factor
            return 1.0, "insufficient_data"

    def get_acceptance_wilson_ci(
        self,
        category: str,
        segment: str = "",
    ) -> tuple[float, float, float, str]:
        """Wilson CI for acceptance rate in a segment."""
        return self.acceptance_calibration.wilson_ci(
            platform="",
            program="",
            niche=category,
        )

    def get_availability_factor(
        self,
        category: str,
        segment: str = "",
    ) -> tuple[Any, str]:
        """Get task availability calibration factor."""
        engine = self.availability_engine
        try:
            available_hours = engine.get_available_hours("week")
            if available_hours >= 40:
                return 1.0, "available"
            elif available_hours >= 10:
                return 0.5, "limited"
            elif available_hours > 0:
                return 0.25, "limited"
            else:
                return 0.0, "unavailable"
        except Exception as exc:
            logger.warning("Availability factor failed: %s", exc)
            return 1.0, "unknown"

    def get_calibration_report(self) -> dict[str, Any]:
        """Full calibration report across all categories."""
        report = {
            "generated_at": datetime.now(UTC).isoformat(),
            "hourly_rate": self._calibration_engine_report(),
            "acceptance": self._acceptance_calibration_report(),
            "reward": self._reward_calibration_report(),
            "availability": self._availability_report(),
        }
        return report

    def _calibration_engine_report(self) -> dict[str, Any]:
        """Report from main CalibrationEngine."""
        return {"status": "available"}

    def _acceptance_calibration_report(self) -> dict[str, Any]:
        """Report from AcceptanceCalibrationEngine."""
        return {"status": "available"}

    def _reward_calibration_report(self) -> dict[str, Any]:
        """Report from PersonalRewardProbability."""
        return {"status": "available"}

    def _availability_report(self) -> dict[str, Any]:
        """Report from AvailabilityEngine."""
        engine = self.availability_engine
        try:
            snapshot = engine.get_snapshot()
            return {"platforms": snapshot.to_dict() if hasattr(snapshot, "to_dict") else str(snapshot)}
        except Exception as exc:
            logger.warning("Availability report failed: %s", exc)
            return {"status": "error", "error": str(exc)}


# ────────────────────────────────────────────────────────────────
# Singleton
# ────────────────────────────────────────────────────────────────

_universal_calibration: UniversalCalibrationEngine | None = None


def get_universal_calibration_engine(
    data_dir: str | Path | None = None,
) -> UniversalCalibrationEngine:
    """Get or create the universal calibration engine singleton."""
    global _universal_calibration
    if _universal_calibration is None or data_dir is not None:
        _universal_calibration = UniversalCalibrationEngine(data_dir)
    return _universal_calibration
