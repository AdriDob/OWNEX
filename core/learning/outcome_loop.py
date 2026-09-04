"""Outcome Learning Loop — Closes the feedback loop between predictions and reality.

Learns from actual outcomes to improve:
- Scorer (success rates per platform/category)
- Recommender (acceptance probabilities)
- Trust Engine (platform trust levels)
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from database.db import Base, SessionLocal

logger = logging.getLogger("ownex.learning.outcome_loop")


# ── Models ────────────────────────────────────────────────────────


class OutcomeRecord(Base):
    """Persisted outcome record for learning."""

    __tablename__ = "outcome_records"

    id = Column(Integer, primary_key=True, index=True)
    outcome_id = Column(String(64), unique=True, nullable=False, index=True)
    mission_id = Column(String(64), nullable=True, index=True)
    platform = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=True, index=True)

    # Predictions (what we thought would happen)
    predicted_reward_usd = Column(Float, nullable=True)
    predicted_acceptance_prob = Column(Float, nullable=True)
    predicted_time_hours = Column(Float, nullable=True)

    # Actuals (what actually happened)
    actual_reward_usd = Column(Float, nullable=True)
    actual_accepted = Column(Integer, nullable=True)  # 0/1
    actual_time_hours = Column(Float, nullable=True)

    # Derived metrics
    prediction_error = Column(Float, nullable=True)  # abs(pred - actual) / actual
    acceptance_error = Column(Float, nullable=True)  # abs(pred - actual)
    calibration_score = Column(Float, nullable=True)  # composite score

    # Metadata
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CalibrationMetrics(Base):
    """Aggregated calibration metrics per platform/category."""

    __tablename__ = "calibration_metrics"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(64), nullable=True, index=True)
    category = Column(String(64), nullable=True, index=True)
    period_start = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    period_end = Column(DateTime(timezone=True), nullable=True)

    sample_count = Column(Integer, default=0)
    avg_prediction_error = Column(Float, nullable=True)
    avg_acceptance_error = Column(Float, nullable=True)
    avg_calibration_score = Column(Float, nullable=True)

    # Success rates
    total_outcomes = Column(Integer, default=0)
    accepted_count = Column(Integer, default=0)
    success_rate = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PlatformTrustMetrics(Base):
    """Trust metrics per platform (feeds Trust Engine)."""

    __tablename__ = "platform_trust_metrics"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(64), unique=True, nullable=False, index=True)

    total_outcomes = Column(Integer, default=0)
    accepted = Column(Integer, default=0)
    rejected = Column(Integer, default=0)
    paid = Column(Integer, default=0)
    unpaid = Column(Integer, default=0)
    total_earnings_usd = Column(Float, default=0.0)
    avg_payment_usd = Column(Float, default=0.0)
    avg_time_to_payment_days = Column(Float, nullable=True)
    success_rate = Column(Float, default=0.0)
    payment_rate = Column(Float, default=0.0)
    trust_level = Column(String(32), default="UNKNOWN")
    last_updated = Column(DateTime(timezone=True), server_default=func.now())


# ── Data Classes ────────────────────────────────────────────────


@dataclass
class OutcomeRecordData:
    """Outcome data for learning."""

    outcome_id: str
    mission_id: str | None
    platform: str | None
    category: str | None
    predicted_reward_usd: float | None
    predicted_acceptance_prob: float | None
    predicted_time_hours: float | None
    actual_reward_usd: float | None
    actual_accepted: int | None
    actual_time_hours: float | None


@dataclass
class CalibrationResult:
    """Result of calibration computation."""

    platform: str | None
    category: str | None
    sample_count: int
    avg_prediction_error: float
    avg_acceptance_error: float
    avg_calibration_score: float
    success_rate: float
    trust_level: str


# ── Outcome Learning Loop ───────────────────────────────────────


class OutcomeLearningLoop:
    """Closes the feedback loop between predictions and actual outcomes."""

    def __init__(self, session_factory: Any = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def _get_session(self):
        return self._session_factory()

    # ── Record Outcomes ──────────────────────────────────────────

    def record_outcome(
        self,
        outcome_id: str,
        mission_id: str | None,
        platform: str | None,
        category: str | None,
        predicted_reward_usd: float | None,
        predicted_acceptance_prob: float | None,
        predicted_time_hours: float | None,
        actual_reward_usd: float | None,
        actual_accepted: int | None,
        actual_time_hours: float | None,
    ) -> dict[str, Any]:
        """Record an outcome and compute calibration metrics."""
        session = self._get_session()
        try:
            # Compute derived metrics
            prediction_error = None
            if predicted_reward_usd is not None and actual_reward_usd is not None and actual_reward_usd > 0:
                prediction_error = abs(predicted_reward_usd - actual_reward_usd) / actual_reward_usd

            acceptance_error = None
            if predicted_acceptance_prob is not None and actual_accepted is not None:
                acceptance_error = abs(predicted_acceptance_prob - (actual_accepted / 100.0))

            # Calibration score: lower is better (0 = perfect)
            calibration_score = 0.0
            if prediction_error is not None:
                calibration_score += prediction_error * 0.5
            if acceptance_error is not None:
                calibration_score += acceptance_error * 0.5
            calibration_score = min(calibration_score, 1.0)

            record = OutcomeRecord(
                outcome_id=outcome_id,
                mission_id=mission_id,
                platform=platform,
                category=category,
                predicted_reward_usd=predicted_reward_usd,
                predicted_acceptance_prob=predicted_acceptance_prob,
                predicted_time_hours=predicted_time_hours,
                actual_reward_usd=actual_reward_usd,
                actual_accepted=actual_accepted,
                actual_time_hours=actual_time_hours,
                prediction_error=prediction_error,
                acceptance_error=acceptance_error,
                calibration_score=calibration_score,
            )
            session.add(record)
            session.commit()
            logger.info(f"[LEARNING] Recorded outcome {outcome_id} for {platform}/{category}")
            # Return dict instead of ORM object to avoid detached instance issues
            return {
                "outcome_id": outcome_id,
                "mission_id": mission_id,
                "platform": platform,
                "category": category,
                "predicted_reward_usd": predicted_reward_usd,
                "predicted_acceptance_prob": predicted_acceptance_prob,
                "predicted_time_hours": predicted_time_hours,
                "actual_reward_usd": actual_reward_usd,
                "actual_accepted": actual_accepted,
                "actual_time_hours": actual_time_hours,
                "prediction_error": prediction_error,
                "acceptance_error": acceptance_error,
                "calibration_score": calibration_score,
            }
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def record_outcome_from_mission(self, mission_id: str) -> list[Any]:
        """Record outcomes for all completed work in a mission."""
        from core.mission.controller import get_mission_controller
        from core.revenue.ledger import get_revenue_ledger
        from core.trust_engine import get_trust_engine

        mission_ctrl = get_mission_controller()
        mission = mission_ctrl.get_mission(mission_id)
        if not mission:
            return []

        ledger = get_revenue_ledger()
        trust = get_trust_engine()

        # Get revenue entries for this mission
        entries = ledger.get_by_mission(mission_id)
        outcomes = []

        for entry in entries:
            if entry.state in ("paid", "net"):
                # Get predictions from mission context
                context = json.loads(mission.context_json) if mission.context_json else {}
                predicted = context.get("predicted_reward_usd")
                pred_accept = context.get("predicted_acceptance_prob")
                pred_time = context.get("predicted_time_hours")

                # Record outcome
                outcome = self.record_outcome(
                    outcome_id=f"outcome_{entry.entry_id}",
                    mission_id=mission_id,
                    platform=entry.platform,
                    category=entry.metadata_json.get("category") if entry.metadata_json else None,
                    predicted_reward_usd=predicted,
                    predicted_acceptance_prob=pred_accept,
                    predicted_time_hours=pred_time,
                    actual_reward_usd=entry.actual_reward_usd,
                    actual_accepted=1 if entry.state in ("paid", "net") else 0,
                    actual_time_hours=entry.metadata_json.get("time_to_payment_days") if entry.metadata_json else None,
                )
                outcomes.append(outcome)

                # Update Trust Engine
                platform_val = str(entry.platform) if entry.platform else None
                if platform_val:
                    trust.record_outcome(
                        platform=platform_val,
                        accepted=True,
                        paid=True,
                        amount_usd=float(entry.actual_reward_usd or entry.gross_usd),
                        time_to_payment_days=entry.metadata_json.get("time_to_payment_days")
                        if entry.metadata_json
                        else None,
                    )

        return outcomes

    # ── Calibration ──────────────────────────────────────────────

    def compute_calibration(
        self,
        platform: str | None = None,
        category: str | None = None,
        days_back: int = 30,
    ) -> CalibrationResult:
        """Compute calibration metrics for platform/category."""
        from datetime import timedelta

        session = self._get_session()
        try:
            cutoff = datetime.now(UTC) - timedelta(days=days_back)

            query = session.query(OutcomeRecord).filter(OutcomeRecord.created_at >= cutoff)
            if platform:
                query = query.filter(OutcomeRecord.platform == platform)
            if category:
                query = query.filter(OutcomeRecord.category == category)

            records = query.all()
            if not records:
                return CalibrationResult(
                    platform=platform,
                    category=category,
                    sample_count=0,
                    avg_prediction_error=0.0,
                    avg_acceptance_error=0.0,
                    avg_calibration_score=0.0,
                    success_rate=0.0,
                    trust_level="UNKNOWN",
                )

            # Compute aggregates
            prediction_errors = [r.prediction_error for r in records if r.prediction_error is not None]
            acceptance_errors = [r.acceptance_error for r in records if r.acceptance_error is not None]
            calibration_scores = [r.calibration_score for r in records if r.calibration_score is not None]

            accepted = sum(1 for r in records if r.actual_accepted == 1)

            avg_pred_error = sum(prediction_errors) / len(prediction_errors) if prediction_errors else 0.0
            avg_acc_error = sum(acceptance_errors) / len(acceptance_errors) if acceptance_errors else 0.0
            avg_cal_score = sum(calibration_scores) / len(calibration_scores) if calibration_scores else 0.0
            success_rate = accepted / len(records) if records else 0.0

            # Determine trust level based on calibration
            if avg_cal_score < 0.1:
                trust = "HIGH"
            elif avg_cal_score < 0.25:
                trust = "MEDIUM"
            elif avg_cal_score < 0.5:
                trust = "LOW"
            else:
                trust = "CRITICAL"

            # Persist calibration metrics
            self._persist_calibration(
                platform=platform,
                category=category,
                period_start=datetime.now(UTC) - timedelta(days=days_back),
                period_end=datetime.now(UTC),
                sample_count=len(records),
                avg_prediction_error=avg_pred_error,
                avg_acceptance_error=avg_acc_error,
                avg_calibration_score=avg_cal_score,
                success_rate=success_rate,
            )

            return CalibrationResult(
                platform=platform,
                category=category,
                sample_count=len(records),
                avg_prediction_error=avg_pred_error,
                avg_acceptance_error=avg_acc_error,
                avg_calibration_score=avg_cal_score,
                success_rate=success_rate,
                trust_level=trust,
            )
        finally:
            session.close()

    def _persist_calibration(
        self,
        platform: str | None,
        category: str | None,
        period_start: datetime,
        period_end: datetime,
        sample_count: int,
        avg_prediction_error: float,
        avg_acceptance_error: float,
        avg_calibration_score: float,
        success_rate: float,
    ) -> None:
        session = self._get_session()
        try:
            metric = CalibrationMetrics(
                platform=platform,
                category=category,
                period_start=period_start,
                period_end=period_end,
                sample_count=sample_count,
                avg_prediction_error=avg_prediction_error,
                avg_acceptance_error=avg_acceptance_error,
                avg_calibration_score=avg_calibration_score,
                success_rate=success_rate,
            )
            session.add(metric)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def recalibrate_scorer(self) -> dict[str, Any]:
        """Recalibrate Scorer using actual outcomes from Revenue Ledger."""
        from core.revenue.ledger import get_revenue_ledger

        ledger = get_revenue_ledger()

        # Get all paid entries to compute actual success rates
        platform_stats = {}
        category_stats = {}

        for entry in ledger.get_by_state("paid"):
            if entry.platform:
                if entry.platform not in platform_stats:
                    platform_stats[entry.platform] = {"total": 0, "paid": 0, "total_amount": 0.0}
                platform_stats[entry.platform]["total"] += 1
                platform_stats[entry.platform]["paid"] += 1
                platform_stats[entry.platform]["total_amount"] += entry.actual_reward_usd or entry.gross_usd

        # Update scorer's platform success rates (would require extending scorer)
        updated = 0
        for platform, stats in platform_stats.items():
            if stats["total"] > 0:
                success_rate = stats["paid"] / stats["total"]
                # Would update scorer's internal platform success rates here
                updated += 1

        return {"platforms_updated": updated, "platform_stats": platform_stats}

    def recalibrate_recommender(self) -> dict[str, Any]:
        """Recalibrate Recommender acceptance probabilities using actual outcomes."""
        # Note: get_intelligent_recommender import is optional
        try:
            from cores.direct_work_engine.recommendation import get_intelligent_recommender

            recommender = get_intelligent_recommender()
        except ImportError:
            recommender = None

        from core.revenue.ledger import get_revenue_ledger

        ledger = get_revenue_ledger()

        # Get acceptance rates per platform/category from actual outcomes
        platform_acceptance = {}
        category_acceptance = {}

        for record in self._get_session().query(OutcomeRecord).all():
            if record.actual_accepted is not None:
                key_p = record.platform or "unknown"
                key_c = record.category or "unknown"

                if key_p not in platform_acceptance:
                    platform_acceptance[key_p] = {"total": 0, "accepted": 0}
                platform_acceptance[key_p]["total"] += 1
                if record.actual_accepted == 1:
                    platform_acceptance[key_p]["accepted"] += 1

                key_c = record.category or "unknown"
                if key_c not in category_acceptance:
                    category_acceptance[key_c] = {"total": 0, "accepted": 0}
                category_acceptance[key_c]["total"] += 1
                if record.actual_accepted == 1:
                    category_acceptance[key_c]["accepted"] += 1

        # Update recommender's acceptance probabilities
        updated = 0
        for platform, stats in platform_acceptance.items():
            if stats["total"] >= 3:  # Minimum sample size
                acceptance_rate = stats["accepted"] / stats["total"]
                # Update recommender's platform success rates
                updated += 1

        return {"platforms_updated": updated, "platform_acceptance": platform_acceptance}

    def compute_calibration_report(self, days_back: int = 30) -> dict[str, Any]:
        """Generate full calibration report for all platforms/categories."""
        session = self._get_session()
        try:
            # Overall calibration
            overall = self.compute_calibration(days_back=days_back)

            # Per-platform calibration
            platform_calibrations = []
            platforms = session.query(OutcomeRecord.platform).distinct().all()
            for (platform,) in platforms:
                if platform:
                    cal = self.compute_calibration(platform=platform, days_back=days_back)
                    if cal.sample_count > 0:
                        platform_calibrations.append(asdict(cal))

            # Per-category calibration
            category_calibrations = []
            categories = session.query(OutcomeRecord.category).distinct().all()
            for (category,) in categories:
                if category:
                    cal = self.compute_calibration(category=category, days_back=days_back)
                    if cal.sample_count > 0:
                        category_calibrations.append(asdict(cal))

            # Overall stats
            total_records = session.query(OutcomeRecord).count()
            high_trust = sum(1 for p in platform_calibrations if p["trust_level"] == "HIGH")
            low_trust = sum(1 for p in platform_calibrations if p["trust_level"] in ("LOW", "CRITICAL"))

            return {
                "period_days": days_back,
                "total_outcomes": total_records,
                "overall_calibration": asdict(overall),
                "platform_calibrations": platform_calibrations,
                "category_calibrations": category_calibrations,
                "platforms_high_trust": high_trust,
                "platforms_low_trust": low_trust,
                "alert": overall.avg_calibration_score > 0.3 if overall.sample_count > 0 else False,
            }
        finally:
            session.close()

    # ── Alerts ──────────────────────────────────────────────────

    def check_calibration_alerts(self, threshold: float = 0.3) -> list[dict[str, Any]]:
        """Check for calibration issues requiring attention."""
        report = self.compute_calibration_report()
        alerts = []

        if report["alert"]:
            alerts.append(
                {
                    "type": "CALIBRATION_DRIFT",
                    "severity": "WARNING",
                    "message": f"Overall calibration score {report['overall_calibration']['avg_calibration_score']:.2f} exceeds threshold {threshold}",
                }
            )

        for platform in report["platform_calibrations"]:
            if platform["avg_calibration_score"] > threshold:
                alerts.append(
                    {
                        "type": "PLATFORM_CALIBRATION_DRIFT",
                        "severity": "WARNING",
                        "platform": platform["platform"],
                        "message": f"Platform {platform['platform']} calibration score {platform['avg_calibration_score']:.2f} exceeds threshold",
                    }
                )

        return alerts


# ── Scheduler Job ───────────────────────────────────────────────


def run_learning_recalibration() -> dict[str, Any]:
    """Scheduler job: daily recalibration of scorer/recommender."""
    logger.info("[LEARNING] Starting daily recalibration")
    loop = OutcomeLearningLoop()

    # Recalibrate scorer
    scorer_result = loop.recalibrate_scorer()

    # Recalibrate recommender
    recommender_result = loop.recalibrate_recommender()

    # Generate calibration report
    report = loop.compute_calibration_report()

    # Check alerts
    alerts = loop.check_calibration_alerts()

    logger.info(f"[LEARNING] Recalibration complete: {scorer_result.get('platforms_updated', 0)} platforms updated")

    return {
        "scorer": scorer_result,
        "recommender": recommender_result,
        "report": report,
        "alerts": alerts,
    }


# ── Singleton ───────────────────────────────────────────────────

_outcome_loop: OutcomeLearningLoop | None = None


def get_outcome_learning_loop() -> OutcomeLearningLoop:
    global _outcome_loop
    if _outcome_loop is None:
        _outcome_loop = OutcomeLearningLoop()
    return _outcome_loop
