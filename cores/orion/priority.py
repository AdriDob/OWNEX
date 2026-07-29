"""ORION CORE — Dynamic priority queue that ranks what to work on next."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from core.orion.models import (
    OrionDecision,
    OrionTask,
    PriorityLevel,
    ROIScore,
    TaskKind,
)

logger = logging.getLogger("ownex.orion.priority")

_THRESHOLDS = {
    PriorityLevel.CRITICAL: 75.0,
    PriorityLevel.HIGH: 50.0,
    PriorityLevel.MEDIUM: 25.0,
    PriorityLevel.LOW: 10.0,
    PriorityLevel.BACKGROUND: 0.0,
}


def classify_priority(score: float) -> PriorityLevel:
    """Map a 0-100 score to a PriorityLevel."""
    for level, threshold in sorted(_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
        if score >= threshold:
            return level
    return PriorityLevel.BACKGROUND


def generate_decisions(scores: dict[str, ROIScore]) -> list[OrionDecision]:
    """Generate ORION decisions based on current ROI scores.

    For each platform, produce 0-N decisions depending on score:
        - Critical (≥75):  explore new targets + validate existing
        - High (≥50):      recon + hypothesis generation
        - Medium (≥25):    monitor + review pending submissions
        - Low (≥10):       background intel gathering
        - Background:      no decisions (wait for data)
    """
    decisions: list[OrionDecision] = []

    for pid, roi in scores.items():
        level = classify_priority(roi.score)
        now = datetime.now(timezone.utc)

        if level == PriorityLevel.CRITICAL:
            decisions.append(
                OrionDecision(
                    kind=TaskKind.EXPLORE,
                    platform=roi.platform,
                    priority=level,
                    score=roi.score,
                    reason=(
                        f"{pid.upper()} score={roi.score} — top earner "
                        f"(${roi.earnings_30d:.0f}/30d). Explore new targets."
                    ),
                    payload={
                        "platform": pid,
                        "max_decisions": 3,
                        "focus": "recon+hypothesis",
                    },
                    expires_at=(now + timedelta(hours=4)).isoformat(),
                )
            )
            decisions.append(
                OrionDecision(
                    kind=TaskKind.VALIDATE,
                    platform=roi.platform,
                    priority=level,
                    score=roi.score * 0.9,
                    reason=f"{pid.upper()} — pending findings need validation.",
                    payload={"platform": pid, "focus": "validate_pending"},
                    expires_at=(now + timedelta(hours=2)).isoformat(),
                )
            )

        elif level == PriorityLevel.HIGH:
            decisions.append(
                OrionDecision(
                    kind=TaskKind.RECON,
                    platform=roi.platform,
                    priority=level,
                    score=roi.score,
                    reason=(f"{pid.upper()} score={roi.score} — strong earner. Run recon on existing targets."),
                    payload={"platform": pid, "focus": "recon"},
                    expires_at=(now + timedelta(hours=6)).isoformat(),
                )
            )

        elif level == PriorityLevel.MEDIUM:
            decisions.append(
                OrionDecision(
                    kind=TaskKind.MONITOR,
                    platform=roi.platform,
                    priority=level,
                    score=roi.score,
                    reason=(f"{pid.upper()} score={roi.score} — potential. Monitor for new programs."),
                    payload={"platform": pid, "focus": "monitor"},
                    expires_at=(now + timedelta(hours=12)).isoformat(),
                )
            )

        elif level == PriorityLevel.LOW:
            decisions.append(
                OrionDecision(
                    kind=TaskKind.EXPLORE,
                    platform=roi.platform,
                    priority=level,
                    score=roi.score,
                    reason=f"{pid.upper()} score={roi.score} — low signal. Background intel.",
                    payload={"platform": pid, "focus": "discovery"},
                    expires_at=(now + timedelta(hours=24)).isoformat(),
                )
            )

    # Sort decisions by score descending
    decisions.sort(key=lambda d: d.score, reverse=True)
    return decisions


def decisions_to_tasks(decisions: list[OrionDecision]) -> list[OrionTask]:
    """Convert ORION decisions into concrete dispatchable tasks."""
    tasks: list[OrionTask] = []
    for i, d in enumerate(decisions[:10]):  # cap at 10 per cycle
        task_kind_map = {
            TaskKind.EXPLORE: "core.orion.intelligence.collector:collect_intel",
            TaskKind.RECON: "core.orion.intelligence.collector:collect_intel",
            TaskKind.VALIDATE: "core.orion.health.checker:collect_health_metrics",
            TaskKind.MONITOR: "core.orion.intelligence.collector:collect_intel",
        }
        tasks.append(
            OrionTask(
                id=f"orion-{i}-{datetime.now(timezone.utc).timestamp():.0f}",
                kind=d.kind,
                target=d.platform.value,
                description=d.reason,
                priority=d.priority,
                score=d.score,
                status="pending",
                handler=task_kind_map.get(d.kind, "core.orion.intelligence.collector:collect_intel"),
                payload=d.payload,
            )
        )
    return tasks


# Helper for timedelta
from datetime import timedelta  # noqa: E402 — needed at module level
