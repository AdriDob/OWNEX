from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from cores.validation.confidence import ConfidenceScore
from cores.validation.rules import ValidationReport

logger = logging.getLogger("orion.validation.gate")

DEFAULT_CONFIDENCE_THRESHOLD = 0.60
STATE_FILE = Path.home() / ".orion" / "gate_state.json"

VULN_THRESHOLDS: dict[str, float] = {
    "idor": 0.85,
    "ssrf": 0.90,
    "xss": 0.80,
    "sqli": 0.80,
    "auth_bypass": 0.95,
    "rce": 0.90,
    "lfi": 0.85,
    "open_redirect": 0.80,
    "csrf": 0.75,
    "information_disclosure": 0.70,
    "directory_listing": 0.70,
    "unknown": DEFAULT_CONFIDENCE_THRESHOLD,
}

# Context modifiers: adjust threshold based on target type
CONTEXT_MODIFIERS: dict[str, dict[str, float]] = {
    "b2b_saas": {"idor": -0.05, "auth_bypass": -0.03, "ssrf": -0.05},
    "consumer_app": {"idor": +0.05, "xss": -0.05, "open_redirect": -0.10},
    "api": {"auth_bypass": -0.05, "rce": -0.05, "sqli": -0.05},
    "mobile": {"idor": +0.05, "auth_bypass": +0.03},
    "financial": {"ssrf": -0.10, "rce": -0.10, "sqli": -0.05},
    "critical": {"all": -0.10},  # higher-stakes programs — admit more aggressively
    "default": {},
}


@dataclass
class Verdict:
    hot_path_id: str
    status: Literal["confirmed", "rejected", "inconclusive"]
    confidence: float
    reproducibility_score: float
    validation: ValidationReport
    confidence_details: ConfidenceScore
    evidence_links: list[str]
    reason: str
    retry_count: int
    timestamp: str
    vulnerability_type: str = "unknown"
    alternative_explanations: list[dict[str, Any]] = field(default_factory=list)
    missing_verifications: list[str] = field(default_factory=list)
    next_best_test: dict[str, Any] | None = None
    uncertainty_level: str = "unknown"


class ReportGate:
    """Adaptive report gate with per-vulnerability thresholds and context awareness.

    Thresholds are persisted to ~/.orion/gate_state.json and can be tuned
    by FeedbackLearner based on human feedback patterns.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._thresholds: dict[str, float] = dict(VULN_THRESHOLDS)
        self._acceptance_stats: dict[str, dict[str, int]] = {}  # vuln_type -> {accepted, rejected}
        self._load_state()

    # ── Threshold management ─────────────────────────

    def get_threshold(self, vuln_type: str, context: str = "default") -> float:
        base = self._thresholds.get(vuln_type.lower(), DEFAULT_CONFIDENCE_THRESHOLD)
        modifier = self._get_context_modifier(vuln_type, context)
        return max(0.0, min(1.0, base + modifier))

    def set_threshold(self, vuln_type: str, threshold: float) -> None:
        with self._lock:
            self._thresholds[vuln_type.lower()] = max(0.0, min(1.0, threshold))
        self._save_state()

    def get_thresholds(self) -> dict[str, float]:
        return dict(self._thresholds)

    def reset_thresholds(self) -> None:
        with self._lock:
            self._thresholds = dict(VULN_THRESHOLDS)
            self._acceptance_stats = {}
        self._save_state()

    # ── Context-aware admission ─────────────────────

    def admit(self, verdict: Verdict, context: str = "default") -> bool:
        threshold = self.get_threshold(verdict.vulnerability_type, context)
        admitted = verdict.status == "confirmed" and verdict.confidence >= threshold
        self._record_decision(verdict.vulnerability_type, admitted)
        return admitted

    def reject_reason(self, verdict: Verdict, context: str = "default") -> str:
        threshold = self.get_threshold(verdict.vulnerability_type, context)
        if verdict.status == "confirmed":
            if verdict.confidence >= threshold:
                return f"Verdict is confirmed — confidence {verdict.confidence:.2f} >= {verdict.vulnerability_type} threshold {threshold:.2f}."
            return (
                f"Confirmed but below {verdict.vulnerability_type} threshold: "
                f"confidence {verdict.confidence:.2f} < {threshold:.2f}"
            )
        if verdict.status == "rejected":
            reasons = ["status=rejected", f"confidence={verdict.confidence:.2f}", f"threshold={threshold:.2f}"]
            if verdict.validation.failed_rules:
                reasons.append(f"failed_rules={verdict.validation.failed_rules}")
            return " | ".join(reasons)
        if verdict.status == "inconclusive":
            return (
                f"status=inconclusive | confidence={verdict.confidence:.2f} "
                f"(below {verdict.vulnerability_type} threshold {threshold:.2f}) | "
                f"reproducibility={verdict.reproducibility_score:.2f}"
            )
        return f"status={verdict.status} (unexpected)"

    # ── Feedback tuning ─────────────────────────────

    def tune_from_feedback(self, rule_thresholds: dict[str, float]) -> int:
        """Apply threshold adjustments from FeedbackLearner.

        Expects keys like ``idor_threshold``, ``ssrf_threshold``, etc.
        Returns number of thresholds updated.
        """
        updated = 0
        with self._lock:
            for key, value in rule_thresholds.items():
                if key.endswith("_threshold"):
                    vuln_type = key[:-10]  # strip "_threshold"
                    if vuln_type in self._thresholds or vuln_type == "unknown":
                        clamped = max(0.0, min(1.0, value))
                        self._thresholds[vuln_type] = clamped
                        updated += 1
                        logger.info("[GATE] Threshold tuned: %s → %.2f (from feedback)", vuln_type, clamped)
                elif key in self._thresholds:
                    clamped = max(0.0, min(1.0, value))
                    self._thresholds[key] = clamped
                    updated += 1
                    logger.info("[GATE] Threshold tuned: %s → %.2f (from feedback)", key, clamped)
        if updated:
            self._save_state()
        return updated

    # ── Acceptance stats ────────────────────────────

    def get_acceptance_rate(self, vuln_type: str) -> float | None:
        stats = self._acceptance_stats.get(vuln_type.lower())
        if not stats or stats["total"] == 0:
            return None
        return stats["accepted"] / stats["total"]

    def get_acceptance_stats(self) -> dict[str, dict[str, int]]:
        return dict(self._acceptance_stats)

    def reset_acceptance_stats(self) -> None:
        with self._lock:
            self._acceptance_stats = {}
        self._save_state()

    # ── Internal ────────────────────────────────────

    def _get_context_modifier(self, vuln_type: str, context: str) -> float:
        ctx_mods = CONTEXT_MODIFIERS.get(context, {})
        # Try specific vuln type modifier
        if vuln_type in ctx_mods:
            return ctx_mods[vuln_type]
        # Try "all" catch-all modifier
        if "all" in ctx_mods:
            return ctx_mods["all"]
        return 0.0

    def _record_decision(self, vuln_type: str, admitted: bool) -> None:
        vt = vuln_type.lower()
        with self._lock:
            stats = self._acceptance_stats.setdefault(vt, {"accepted": 0, "rejected": 0})
            stats["accepted" if admitted else "rejected"] += 1
            stats["total"] = stats["accepted"] + stats["rejected"]

    # ── Persistence ─────────────────────────────────

    def _save_state(self) -> None:
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "thresholds": self._thresholds,
                "acceptance_stats": self._acceptance_stats,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.warning("Failed to save gate state: %s", exc)

    def _load_state(self) -> None:
        if not STATE_FILE.exists():
            return
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            saved = data.get("thresholds", {})
            if saved:
                self._thresholds.update(saved)
            self._acceptance_stats = data.get("acceptance_stats", {})
            logger.info(
                "Gate state restored from %s (%d thresholds, %d types with stats)",
                STATE_FILE,
                len(saved),
                len(self._acceptance_stats),
            )
        except Exception as exc:
            logger.warning("Failed to load gate state: %s", exc)


_GATE: ReportGate | None = None
_GATE_LOCK = Lock()


def get_report_gate() -> ReportGate:
    """Singleton: all consumers share the same gate instance so feedback tuning is live."""
    global _GATE
    if _GATE is None:
        with _GATE_LOCK:
            if _GATE is None:
                _GATE = ReportGate()
    return _GATE


def reset_report_gate() -> None:
    """Reset the singleton (for testing)."""
    global _GATE
    _GATE = None
