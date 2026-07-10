"""FeedbackTuner — connects human feedback to ConfidenceScorer weight adjustments."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cores.validation.confidence import ConfidenceScorer

logger = logging.getLogger("catseye.validation.feedback_tuner")

FEEDBACK_LOG = Path.home() / ".orion" / "feedback_events.jsonl"
TUNING_LOG = Path.home() / ".orion" / "feedback_tunings.jsonl"
MIN_EVENTS_FOR_ANALYSIS = 3


class FeedbackTuner:
    """Accumulates human feedback events and periodically tunes ConfidenceScorer.

    1. accumulate feedback finding:confirmed / finding:rejected events
    2. after MIN_EVENTS_FOR_ANALYSIS events, call FeedbackLearner.analyze_verdict_patterns()
    3. apply suggested_rule_tuning() output to ConfidenceScorer.adjust_weights()
    4. persist everything to JSONL for audit and restart recovery
    """

    def __init__(self, confidence_scorer: ConfidenceScorer | None = None) -> None:
        self._scorer = confidence_scorer or ConfidenceScorer()
        self._events: list[dict[str, Any]] = self._load_persisted_events()
        self._tuning_history: list[dict[str, Any]] = self._load_persisted_tunings()

    # ── Public API ────────────────────────────────────────────────

    def record_feedback(self, event: dict[str, Any]) -> None:
        """Record a single feedback event (finding confirmed/rejected)."""
        feedback = {
            "finding_id": event.get("id"),
            "title": event.get("title", ""),
            "old_status": event.get("old_status", ""),
            "new_status": event.get("new_status", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._events.append(feedback)
        self._persist_event(feedback)
        logger.info("[TUNER] Feedback recorded: finding %s → %s", feedback["finding_id"], feedback["new_status"])

    def tune_if_ready(self, learner: Any | None = None) -> dict[str, Any]:
        """If enough events accumulated, run FeedbackLearner and adjust weights.

        Returns a status dict with what was done.
        """
        if len(self._events) < MIN_EVENTS_FOR_ANALYSIS:
            return {
                "status": "skipped",
                "events": len(self._events),
                "needed": MIN_EVENTS_FOR_ANALYSIS,
                "reason": f"Need {MIN_EVENTS_FOR_ANALYSIS}+ events, have {len(self._events)}",
            }

        if learner is None:
            try:
                from cores.validation.llm_analyzer import FeedbackLearner
                learner = FeedbackLearner()
            except ImportError:
                return {"status": "error", "reason": "FeedbackLearner not available"}

        try:
            insights = learner.analyze_verdict_patterns(self._events)
            if not insights:
                return {"status": "skipped", "reason": "No insights from analysis", "events": len(self._events)}

            tuning = learner.suggest_rule_tuning(insights)
            weight_adjustments = tuning.get("confidence_weights", {})
            old_weights = self._scorer.get_weights()

            if weight_adjustments:
                self._scorer.adjust_weights(weight_adjustments)

            new_weights = self._scorer.get_weights()
            tuning_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events_analyzed": len(self._events),
                "insights_count": len(insights),
                "old_weights": old_weights,
                "new_weights": new_weights,
                "adjustments_applied": weight_adjustments,
                "patterns": [i.pattern for i in insights],
            }
            self._tuning_history.append(tuning_record)
            self._persist_tuning(tuning_record)

            logger.info("[TUNER] Weights adjusted: %s → %s", old_weights, new_weights)
            return {
                "status": "tuned",
                "events_analyzed": len(self._events),
                "insights": len(insights),
                "old_weights": old_weights,
                "new_weights": new_weights,
                "adjustments": weight_adjustments,
                "patterns": tuning_record["patterns"],
            }
        except Exception as exc:
            logger.exception("[TUNER] Tuning failed")
            return {"status": "error", "reason": str(exc)}

    def status(self) -> dict[str, Any]:
        """Return current tuner state for health/status endpoints."""
        return {
            "total_feedback_events": len(self._events),
            "total_tunings": len(self._tuning_history),
            "ready_for_analysis": len(self._events) >= MIN_EVENTS_FOR_ANALYSIS,
            "current_weights": self._scorer.get_weights(),
            "last_tuning": self._tuning_history[-1] if self._tuning_history else None,
        }

    def get_events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def clear_events(self, keep: int = 0) -> None:
        """Clear accumulated events after successful tuning, optionally keeping N latest."""
        if keep > 0:
            self._events = self._events[-keep:]
        else:
            self._events = []
        logger.info("[TUNER] Cleaned feedback events (kept %s)", keep)

    # ── Persistence ───────────────────────────────────────────────

    def _persist_event(self, event: dict[str, Any]) -> None:
        try:
            FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(FEEDBACK_LOG, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as exc:
            logger.warning("[TUNER] Failed to persist event: %s", exc)

    def _load_persisted_events(self) -> list[dict[str, Any]]:
        if not FEEDBACK_LOG.exists():
            return []
        events: list[dict[str, Any]] = []
        try:
            with open(FEEDBACK_LOG) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        except Exception as exc:
            logger.warning("[TUNER] Failed to load persisted events: %s", exc)
        return events

    def _persist_tuning(self, tuning: dict[str, Any]) -> None:
        try:
            TUNING_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(TUNING_LOG, "a") as f:
                f.write(json.dumps(tuning) + "\n")
        except Exception as exc:
            logger.warning("[TUNER] Failed to persist tuning: %s", exc)

    def _load_persisted_tunings(self) -> list[dict[str, Any]]:
        if not TUNING_LOG.exists():
            return []
        tunings: list[dict[str, Any]] = []
        try:
            with open(TUNING_LOG) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        tunings.append(json.loads(line))
        except Exception as exc:
            logger.warning("[TUNER] Failed to load persisted tunings: %s", exc)
        return tunings
