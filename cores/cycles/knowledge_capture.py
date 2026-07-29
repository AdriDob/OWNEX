"""Knowledge Capture — every finding leaves learning metadata.

Captures: what worked, what didn't, patterns, tool effectiveness, platform quirks.
Feeds back into Opportunity Scorer and Pipeline Hypothesis Generator.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from database import db
from database.models import Finding, Target, Verdict
from database.models_economic import PayoutRecord

logger = logging.getLogger("ownex.cycles.knowledge")


class LearningType(str, Enum):
    PATTERN = "pattern"
    TOOL_EFFECTIVENESS = "tool_effectiveness"
    PLATFORM_QUIRK = "platform_quirk"
    REPORT_STRUCTURE = "report_structure"
    SCORE_CALIBRATION = "score_calibration"
    FAILURE_ANALYSIS = "failure_analysis"


@dataclass
class KnowledgeEntry:
    """A single piece of captured knowledge."""

    id: str
    type: LearningType
    source_finding_id: int | None
    source_target_id: int | None
    platform: str | None
    program: str | None = None
    vuln_type: str | None = None
    lesson: str = ""
    confidence: float = 0.0  # 0.0-1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validated: bool = False
    validated_at: str | None = None
    outcome: str | None = None  # "confirmed", "rejected", "pending"


class KnowledgeCapture:
    """Captures and stores learning from pipeline outcomes."""

    def __init__(self) -> None:
        self._entries: list[KnowledgeEntry] = []

    def capture_from_finding(self, finding: Finding) -> KnowledgeEntry | None:
        """Extract learning from a confirmed finding with verdicts."""
        session = db.SessionLocal()
        try:
            verdicts = (
                session.query(Verdict)
                .filter(Verdict.hot_path_id == finding.id)
                .filter(Verdict.status == "confirmed")
                .all()
            )

            if not verdicts:
                return None

            # Get platform and program info
            target = session.query(Target).filter(Target.id == finding.target_id).first()
            platform = ""
            program = ""
            if target and target.name and "_" in target.name:
                parts = target.name.split("_", 1)
                platform = parts[0]
                program = parts[1] if len(parts) > 1 else ""

            # Extract evidence quality indicators
            evidence_quality = self._assess_evidence_quality(verdicts, session)
            report_quality = self._assess_report_quality(finding, session)

            # Determine lesson type
            if finding.vulnerability_type:
                lesson_type = LearningType.PATTERN
            elif evidence_quality < 0.5:
                lesson_type = LearningType.FAILURE_ANALYSIS
            else:
                lesson_type = LearningType.SCORE_CALIBRATION

            # Build lesson
            lesson = self._build_lesson(finding, verdicts, evidence_quality, report_quality, platform, program)

            entry = KnowledgeEntry(
                id=f"k_{finding.id}_{lesson_type.value}_{datetime.now(timezone.utc).timestamp()}",
                type=lesson_type,
                source_finding_id=finding.id,
                source_target_id=finding.target_id,
                platform=platform or None,
                program=program or None,
                vuln_type=finding.vulnerability_type,
                lesson=lesson,
                confidence=evidence_quality * 0.7 + report_quality * 0.3,
                metadata={
                    "severity": finding.severity,
                    "cvss": finding.cvss_score,
                    "evidence_count": len(verdicts),
                    "evidence_quality": evidence_quality,
                    "report_quality": report_quality,
                },
            )

            self._entries.append(entry)
            logger.info("Captured knowledge: %s from finding %d", lesson_type.value, finding.id)
            return entry

        finally:
            session.close()

    def capture_from_payout(self, payout: PayoutRecord) -> KnowledgeEntry | None:
        """Learn from successful payout — what led to acceptance."""
        session = db.SessionLocal()
        try:
            # Find related submission
            if not payout.submission_record_id:
                return None

            submission = (
                session.query(db.models.SubmissionRecord)
                .filter(db.models.SubmissionRecord.id == payout.submission_record_id)
                .first()
            )
            if not submission or not submission.report_id:
                return None

            report = session.query(db.models.Report).filter(db.models.Report.id == submission.report_id).first()
            if not report:
                return None

            # Find findings in this report
            finding_ids = json.loads(report.finding_ids) if report.finding_ids else []
            findings = (session.query(Finding).filter(Finding.id.in_(finding_ids)).all()) if finding_ids else []

            if not findings:
                return None

            f = findings[0]
            target = session.query(Target).filter(Target.id == f.target_id).first()
            platform = target.name.split("_")[0] if target and "_" in target.name else ""

            entry = KnowledgeEntry(
                id=f"k_payout_{payout.id}_{datetime.now(timezone.utc).timestamp()}",
                type=LearningType.SCORE_CALIBRATION,
                source_finding_id=f.id,
                source_target_id=f.target_id,
                platform=platform or None,
                program=payout.program,
                vuln_type=f.vulnerability_type,
                lesson=(
                    f"Finding #{f.id} ({f.vulnerability_type}) accepted on {platform}/{payout.program} "
                    f"for ${payout.amount:.0f}. "
                    f"Severity: {f.severity}, CVSS: {f.cvss_score}. "
                    f"Score predicted: {f.score}, Actual payout: ${payout.amount:.0f}. "
                    f"Calibration: {'overestimated' if (f.score or 0) * 10000 > payout.amount else 'underestimated' if (f.score or 0) * 10000 < payout.amount else 'accurate'}"
                ),
                confidence=0.9,
                metadata={
                    "payout_amount": payout.amount,
                    "predicted_score": f.score,
                    "calibration": "over" if (f.score or 0) * 10000 > payout.amount else "under",
                },
            )

            self._entries.append(entry)
            logger.info("Captured payout knowledge: finding %d → $%.0f", f.id, payout.amount)
            return entry

        finally:
            session.close()

    def capture_failure(self, finding: Finding, reason: str) -> KnowledgeEntry:
        """Capture learning from a rejected/failed finding."""
        target = db.SessionLocal().query(Target).filter(Target.id == finding.target_id).first()
        platform = target.name.split("_")[0] if target and "_" in target.name else ""

        entry = KnowledgeEntry(
            id=f"k_fail_{finding.id}_{datetime.now(timezone.utc).timestamp()}",
            type=LearningType.FAILURE_ANALYSIS,
            source_finding_id=finding.id,
            source_target_id=finding.target_id,
            platform=platform or None,
            vuln_type=finding.vulnerability_type,
            lesson=(
                f"Finding #{finding.id} ({finding.vulnerability_type}) rejected on {platform}: {reason}. "
                f"Severity: {finding.severity}, Score: {finding.score}. "
                f"Likely gaps: {self._guess_gaps(reason, finding)}"
            ),
            confidence=0.8,
            metadata={
                "rejection_reason": reason,
                "severity": finding.severity,
                "predicted_score": finding.score,
            },
        )

        self._entries.append(entry)
        logger.info("Captured failure knowledge: finding %d - %s", finding.id, reason)
        return entry

    def _assess_evidence_quality(self, verdicts: list[Verdict], session) -> float:
        """Score evidence quality from verdicts (0-1)."""
        if not verdicts:
            return 0.0

        total_quality = 0.0
        for v in verdicts:
            quality = 0.5
            if v.evidence_links:
                try:
                    ev_count = len(
                        json.loads(v.evidence_links) if isinstance(v.evidence_links, str) else v.evidence_links
                    )
                    quality += min(0.3, ev_count * 0.1)
                except Exception:
                    pass
            if v.validation_report:
                try:
                    vr = json.loads(v.validation_report)
                    passed = len(vr.get("passed_rules", []))
                    failed = len(vr.get("failed_rules", []))
                    if passed + failed > 0:
                        quality += 0.2 * (passed / (passed + failed))
                except Exception:
                    pass
            total_quality += min(1.0, quality)

        return round(total_quality / len(verdicts), 2)

    def _assess_report_quality(self, finding: Finding, session) -> float:
        """Score report completeness (0-1)."""
        quality = 0.0
        if finding.title:
            quality += 0.2
        if finding.description and len(finding.description) > 100:
            quality += 0.2
        if finding.steps_to_reproduce:
            quality += 0.2
        if finding.impact_analysis:
            quality += 0.2
        if finding.remediation:
            quality += 0.2
        return round(quality, 2)

    def _build_lesson(
        self,
        finding: Finding,
        verdicts: list[Verdict],
        evidence_q: float,
        report_q: float,
        platform: str,
        program: str,
    ) -> str:
        vuln = finding.vulnerability_type or "unknown"
        parts = [
            f"Finding #{finding.id} ({vuln}) confirmed on {platform}/{program}.",
            f"Evidence quality: {evidence_q:.0%}, Report quality: {report_q:.0%}.",
            f"Severity: {finding.severity}, CVSS: {finding.cvss_score}.",
        ]

        # Add pattern insight
        if evidence_q > 0.7 and report_q > 0.7:
            parts.append("High-quality evidence + report = fast acceptance pattern.")
        elif evidence_q < 0.5:
            parts.append("Evidence gap detected — improve PoC collection for this vuln type.")
        elif report_q < 0.5:
            parts.append("Report structure weak — invest in remediation/impact sections.")

        return " ".join(parts)

    def _guess_gaps(self, reason: str, finding: Finding) -> str:
        """Guess what was missing based on rejection reason."""
        reason_lower = reason.lower()
        if "duplicate" in reason_lower:
            return "timing / reconnaissance scope"
        if "not reproducible" in reason_lower or "cannot reproduce" in reason_lower:
            return "PoC quality / environment details"
        if "insufficient impact" in reason_lower or "low impact" in reason_lower:
            return "impact analysis / business context"
        if "out of scope" in reason_lower:
            return "scope verification"
        if "informational" in reason_lower:
            return "severity justification"
        return "evidence completeness / report clarity"

    def get_entries(self, limit: int = 100) -> list[KnowledgeEntry]:
        """Get recent knowledge entries."""
        return sorted(self._entries, key=lambda e: e.created_at, reverse=True)[:limit]

    def get_entries_by_type(self, type_: LearningType) -> list[KnowledgeEntry]:
        return [e for e in self._entries if e.type == type_]

    def get_entries_by_vuln_type(self, vuln_type: str) -> list[KnowledgeEntry]:
        return [e for e in self._entries if e.vuln_type == vuln_type]

    def get_entries_by_platform(self, platform: str) -> list[KnowledgeEntry]:
        return [e for e in self._entries if e.platform == platform]

    def to_dict(self, entry: KnowledgeEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "type": entry.type.value,
            "source_finding_id": entry.source_finding_id,
            "source_target_id": entry.source_target_id,
            "platform": entry.platform,
            "program": entry.program,
            "vuln_type": entry.vuln_type,
            "lesson": entry.lesson,
            "confidence": entry.confidence,
            "metadata": entry.metadata,
            "created_at": entry.created_at,
            "validated": entry.validated,
            "validated_at": entry.validated_at,
            "outcome": entry.outcome,
        }


_KNOWLEDGE_CAPTURE: KnowledgeCapture | None = None


def get_knowledge_capture() -> KnowledgeCapture:
    """Get the global KnowledgeCapture instance."""
    global _KNOWLEDGE_CAPTURE
    if _KNOWLEDGE_CAPTURE is None:
        _KNOWLEDGE_CAPTURE = KnowledgeCapture()
    return _KNOWLEDGE_CAPTURE
