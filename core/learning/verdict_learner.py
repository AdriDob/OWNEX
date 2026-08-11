"""VerdictAutoLearner — bridges FeedbackTuner ↔ AcceptanceLearner.

Listens to finding:status_changed events and feeds confirmed/rejected outcomes
into the AcceptanceLearner for automatic weight adaptation.
"""

from __future__ import annotations

import logging
from typing import Any

from cores.events.types import Events

logger = logging.getLogger("orion.core.learning.verdict_learner")


def get_acceptance_learner():
    from core.reports.acceptance.learner import AcceptanceLearner

    return AcceptanceLearner()


def get_bus():
    from cores.events.event_bus import get_event_bus

    return get_event_bus()


def get_quality_dimensions(finding_id: int) -> dict[str, float] | None:
    """Score a finding and return its quality dimensions (0-1 scale)."""
    try:
        from core.reports.quality.scorer import QualityScorer

        qs = QualityScorer()
        score = qs.score(finding_id)
        return {k: round(v, 4) for k, v in score.dimensions.items()}
    except Exception as exc:
        logger.debug("Quality scoring failed for %s: %s", finding_id, exc)
        return None


def get_finding_details(finding_id: int) -> dict[str, Any] | None:
    """Fetch finding details from DB."""
    try:
        from database import db, models

        session = db.SessionLocal()
        try:
            f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
            if not f:
                return None
            return {
                "id": f.id,
                "vulnerability_type": f.vulnerability_type or "generic",
                "severity": f.severity or "medium",
                "title": f.title or "",
                "status": f.status or "",
            }
        finally:
            session.close()
    except Exception as exc:
        logger.debug("Finding lookup failed: %s", exc)
        return None


class VerdictAutoLearner:
    """Bridges feedback signals into the AcceptanceLearner.

    Listens to finding:status_changed → on confirmed/rejected, records an
    outcome observation in AcceptanceLearner and publishes acceptance events.
    """

    def __init__(self) -> None:
        self._learner = get_acceptance_learner()
        self._event_count = 0

    def handle_finding_status_changed(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a finding:status_changed event for acceptance learning.

        Only acts on terminal statuses (confirmed → accepted, rejected).
        Records the outcome as a manual observation in the AcceptanceLearner.
        """
        new_status = payload.get("new_status", "")
        if new_status not in ("confirmed", "rejected"):
            return {"action": "skip", "reason": f"Status {new_status} not terminal"}

        finding_id = payload.get("id")
        if not finding_id:
            return {"action": "skip", "reason": "No finding_id in payload"}

        details = get_finding_details(finding_id)
        if not details:
            return {"action": "error", "reason": f"Finding {finding_id} not found"}

        outcome = "accepted" if new_status == "confirmed" else "rejected"
        vuln_type = details["vulnerability_type"]
        severity = details["severity"]

        dims = get_quality_dimensions(finding_id)
        if dims is None:
            dims = {
                "evidence": 0.5,
                "reproducibility": 0.5,
                "clarity": 0.5,
                "impact_severity": 0.5,
                "completeness": 0.5,
                "confidence": 0.5,
            }

        score = sum(dims.values()) / len(dims) * 100 if dims else 50.0

        try:
            platform = self._detect_platform(finding_id)
            self._learner.record_manual_outcome(
                platform=platform,
                program="",
                vulnerability_type=vuln_type,
                outcome=outcome,
                dimensions=dims,
                score=score,
                severity=severity,
                evidence_count=0,
            )
            self._event_count += 1
        except Exception as exc:
            logger.warning("Failed to record outcome for finding %s: %s", finding_id, exc)
            return {"action": "error", "reason": str(exc)}

        self._publish_events(finding_id, platform, outcome, score, dims)
        logger.info("[VERDICT-LEARNER] Finding %s → %s on %s (score=%.1f)", finding_id, outcome, platform, score)

        old_weights = self._learner.get_weights()
        _defaults = {
            "evidence": 20.0,
            "reproducibility": 20.0,
            "clarity": 15.0,
            "impact_severity": 15.0,
            "completeness": 15.0,
            "confidence": 15.0,
        }
        weights_adapted = any(abs(old_weights.get(k, 0) - v) > 0.1 for k, v in _defaults.items())

        return {
            "action": "recorded",
            "finding_id": finding_id,
            "outcome": outcome,
            "platform": platform,
            "score": score,
            "weights_adapted": weights_adapted,
        }

    def _detect_platform(self, finding_id: int) -> str:
        """Detect platform from finding's target, defaulting to hackerone."""
        try:
            from database import db, models

            session = db.SessionLocal()
            try:
                f = session.query(models.Finding).filter(models.Finding.id == finding_id).first()
                if f and f.target_id:
                    t = session.query(models.Target).filter(models.Target.id == f.target_id).first()
                    if t and t.name and "_" in t.name:
                        parts = t.name.split("_", 1)
                        known = {"hackerone", "bugcrowd", "intigriti", "yeswehack", "immunefi"}
                        if parts[0] in known:
                            return parts[0]
            finally:
                session.close()
        except Exception:
            pass
        return "hackerone"

    def _publish_events(
        self,
        finding_id: int,
        platform: str,
        outcome: str,
        score: float,
        dimensions: dict[str, float],
    ) -> None:
        """Publish acceptance events to EventBus."""
        try:
            bus = get_bus()
            bus.publish(
                Events.ACCEPTANCE_OUTCOME_RECORDED,
                finding_id=finding_id,
                platform=platform,
                outcome=outcome,
                score=round(score, 2),
            )
            bus.publish(
                Events.ACCEPTANCE_PREDICTION_MADE,
                finding_id=finding_id,
                platform=platform,
                outcome=outcome,
                score=round(score, 2),
            )
        except Exception as exc:
            logger.warning("Event publish failed: %s", exc)

    def status(self) -> dict[str, Any]:
        """Return current learner status."""
        try:
            summary = self._learner.get_summary()
            return {
                "events_processed": self._event_count,
                "total_observations": summary.get("total_observations", 0),
                "acceptance_rate": summary.get("acceptance_rate", 0),
                "platforms": list(summary.get("platforms", [])),
                "weights_adapted": any(
                    abs(w - d) > 0.1
                    for w, d in zip(
                        list(self._learner.get_weights().values()),
                        [20.0, 20.0, 15.0, 15.0, 15.0, 15.0],
                        strict=False,
                    )
                ),
            }
        except Exception as exc:
            return {"error": str(exc)}


_LEARNER: VerdictAutoLearner | None = None


def get_verdict_learner() -> VerdictAutoLearner:
    global _LEARNER
    if _LEARNER is None:
        _LEARNER = VerdictAutoLearner()
    return _LEARNER
