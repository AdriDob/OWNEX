"""Auto Feedback Loop — connects finding outcomes to learning systems.

Subscribes to finding:status_changed events and automatically:
1. Records outcomes in the AcceptanceAnalyzer
2. Records learning signals in RewardLearner

This closes the feedback loop: every submission outcome
improves future predictions and prioritization.
"""

from __future__ import annotations

import logging
from typing import Any

from core.acceptance.analyzer import AcceptanceAnalyzer
from core.acceptance.models import AcceptanceOutcome

logger = logging.getLogger("orion.core.acceptance.feedback")


def on_finding_status_changed(
    event: dict[str, Any],
    analyzer: AcceptanceAnalyzer | None = None,
) -> dict[str, Any]:
    """Handle a finding:status_changed event.

    Expected event payload::
        {
            "finding_id": int,
            "finding": {finding_dict},
            "old_status": str,
            "new_status": str,
        }

    Maps status changes to learning outcomes:
    - confirmed/accepted/won → positive outcome
    - rejected/dismissed/false_positive → negative outcome
    - pending/submitted → no outcome (awaiting resolution)

    Returns a dict with recording status.
    """
    finding = event.get("finding", event)
    finding_id = finding.get("id", event.get("finding_id", 0))
    new_status = event.get("new_status", finding.get("status", ""))

    status_map = {
        "confirmed": "accepted",
        "accepted": "accepted",
        "won": "won",
        "rejected": "rejected",
        "dismissed": "dismissed",
        "false_positive": "rejected",
        "duplicate": "rejected",
        "informative": "dismissed",
        "not_applicable": "dismissed",
    }

    mapped_status = status_map.get(new_status.lower(), "")
    if not mapped_status:
        return {"recorded": False, "reason": f"Unmapped status: {new_status}", "finding_id": finding_id}

    outcome = AcceptanceOutcome(
        report_id=finding_id,
        platform=finding.get("platform", "unknown"),
        vulnerability_type=finding.get("vulnerability_type", ""),
        severity=finding.get("severity", ""),
        status=mapped_status,
        payout=float(finding.get("payout", 0)),
        has_poc=bool(finding.get("poc")),
        has_evidence=bool(finding.get("evidence")),
        description_length=len(finding.get("description", "") or ""),
        repro_steps_count=len(finding.get("reproduction_steps", []) or []),
        cvss_score=float(finding.get("cvss_score", 0) or 0),
        cwe_id=finding.get("cwe_id", "") or finding.get("cwe", ""),
    )

    if analyzer:
        analyzer.record_outcome(outcome)

    logger.info(
        "[Feedback] Finding %s → %s (score: %s, payout: %s)",
        finding_id,
        mapped_status,
        outcome.cvss_score,
        outcome.payout,
    )

    return {
        "recorded": True,
        "finding_id": finding_id,
        "status": mapped_status,
        "platform": outcome.platform,
        "vuln_type": outcome.vulnerability_type,
    }
