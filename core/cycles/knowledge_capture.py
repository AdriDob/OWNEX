"""Knowledge Capture — every finding leaves learning metadata.

Captures: what worked, what didn't, patterns, tool effectiveness, platform quirks.
Feeds back into Opportunity Scorer and Pipeline Hypothesis Generator.

Gentle AI Engram Integration:
- Persistent, compounding knowledge across sessions (Engram system)
- Each entry stored in ~/.orion/knowledge/engram.json and survives restarts
- Context accumulation: the agent reaches for memory before re-reading the repo
- Cross-session recall with filtering by platform, vulnerability type, tags
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from database import db
from database.models import Finding, Target, Verdict
from database.models_economic import PayoutRecord

logger = logging.getLogger("ownex.cycles.knowledge")


class LearningType(StrEnum):
    PATTERN = "pattern"
    TOOL_EFFECTIVENESS = "tool_effectiveness"
    PLATFORM_QUIRK = "platform_quirk"
    REPORT_STRUCTURE = "report_structure"
    SCORE_CALIBRATION = "score_calibration"
    FAILURE_ANALYSIS = "failure_analysis"
    ENGRAM = "engram"


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
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    validated: bool = False
    validated_at: str | None = None
    outcome: str | None = None  # "confirmed", "rejected", "pending"

    # Engram fields for cross-session persistence
    engram_id: str | None = None  # Unique ID for cross-session lookup
    tags: list[str] = field(default_factory=list)  # User-defined tags for discovery
    related_engrams: list[str] = field(default_factory=list)  # Links to related entries


class KnowledgeCapture:
    """Captures and stores learning from pipeline outcomes.

    Gentle AI Engram Integration:
    - Each capture persists to ~/.orion/knowledge/engram.json
    - Engraph (adjacency list) tracks relationships between entries
    - recall_engrams() enables context accumulation across sessions
    - Tags and relationships enable discovery of related knowledge
    """

    def __init__(self) -> None:
        self._entries: list[KnowledgeEntry] = []
        self._engraph: dict[str, list[str]] = {}  # Adjacency list for engram relationships
        self._load_existing_engraph()

    def _load_existing_engraph(self) -> None:
        """Load existing engraph from disk on init."""
        engram_path = Path.home() / ".orion" / "knowledge" / "engram.json"
        try:
            if engram_path.exists():
                data = json.loads(engram_path.read_text())
                self._engraph = data.get("adjacency", {})
                logger.info("Loaded %d engram relationships from disk", len(self._engraph))
        except Exception as e:
            logger.warning("Could not load engram graph: %s", e)
            self._engraph = {}

    def _save_engraph_to_disk(self) -> None:
        """Save engraph to persistent storage."""
        engram_path = Path.home() / ".orion" / "knowledge" / "engram.json"
        engram_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            engram_path.write_text(json.dumps({"adjacency": self._engraph}, indent=2))
            logger.info("Saved engram graph to disk")
        except Exception as e:
            logger.warning("Could not save engram graph: %s", e)

    def capture_from_finding(self, finding: Finding) -> KnowledgeEntry | None:
        """Extract learning from a confirmed finding with verdicts.

        Gentle AI: each capture saves to disk immediately, enabling
        context accumulation across sessions.
        """
        session = db.SessionLocal()
        try:
            verdicts = session.query(Verdict).filter(Verdict.hot_path_id == finding.id).filter(Verdict.status == "confirmed").all()

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
                id=f"k_{finding.id}_{lesson_type.value}_{datetime.now(UTC).timestamp()}",
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
                engram_id=f"k_{finding.id}_{lesson_type.value}_{datetime.now(UTC).timestamp()}",
                tags=self._derive_tags(lesson_type, finding),
            )
            entry.related_engrams = self._find_related_engrams(entry)

            self._entries.append(entry)
            # Update engraph relationships
            self._engraph.setdefault(entry.engram_id, []).append(*self._engraph.get(entry.engram_id, []))
            self._save_engraph_to_disk()
            logger.info("Captured knowledge: %s from finding %d", lesson_type.value, finding.id)
            return entry

        finally:
            session.close()

    def capture_from_payout(self, payout: PayoutRecord) -> KnowledgeEntry | None:
        """Learn from successful payout — what led to acceptance.

        Gentle AI: payout learnings also persist and become recallable.
        """
        session = db.SessionLocal()
        try:
            # Find related submission
            if not payout.submission_record_id:
                return None

            submission = session.query(db.models.SubmissionRecord).filter(db.models.SubmissionRecord.id == payout.submission_record_id).first()
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
                id=f"k_payout_{payout.id}_{datetime.now(UTC).timestamp()}",
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
                engram_id=f"k_payout_{payout.id}_{datetime.now(UTC).timestamp()}",
                tags=self._derive_tags(LearningType.SCORE_CALIBRATION, f),
            )
            entry.related_engrams = self._find_related_engrams(entry)

            self._entries.append(entry)
            self._engraph.setdefault(entry.engram_id, []).append(*self._engraph.get(entry.engram_id, []))
            self._save_engraph_to_disk()
            logger.info("Captured payout knowledge: finding %d → $%.0f", f.id, payout.amount)
            return entry

        finally:
            session.close()

    def capture_failure(self, finding: Finding, reason: str) -> KnowledgeEntry:
        """Capture learning from a rejected/failed finding.

        Gentle AI: failures also become recallable engrams.
        """
        session_local = db.SessionLocal()
        target = session_local.query(Target).filter(Target.id == finding.target_id).first()
        platform = target.name.split("_")[0] if target and "_" in target.name else ""
        session_local.close()

        entry = KnowledgeEntry(
            id=f"k_fail_{finding.id}_{datetime.now(UTC).timestamp()}",
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
            engram_id=f"k_fail_{finding.id}_{datetime.now(UTC).timestamp()}",
            tags=self._derive_tags(LearningType.FAILURE_ANALYSIS, finding),
        )
        entry.related_engrams = self._find_related_engrams(entry)

        self._entries.append(entry)
        self._engraph.setdefault(entry.engram_id, []).append(*self._engraph.get(entry.engram_id, []))
        self._save_engraph_to_disk()
        logger.info("Captured failure knowledge: finding %d - %s", finding.id, reason)
        return entry

    def _derive_tags(self, lesson_type: LearningType, finding: Finding) -> list[str]:
        """Derive user-friendly tags from lesson type and finding context."""
        tags: list[str] = []
        if lesson_type == LearningType.PATTERN:
            tags.append("pattern")
        if lesson_type == LearningType.FAILURE_ANALYSIS:
            tags.append("failure")
        if lesson_type == LearningType.SCORE_CALIBRATION:
            tags.append("calibration")
        if lesson_type == LearningType.ENGRAM:
            tags.append("engram")
        # Platform-based tags
        if finding.vulnerability_type:
            vt = finding.vulnerability_type.lower()
            if "sql" in vt:
                tags.append("sql-injection")
            if "xss" in vt:
                tags.append("xss")
            if "rce" in vt or "remote" in vt:
                tags.append("remote-code-execution")
            if "lfi" in vt or "file" in vt:
                tags.append("file-inclusion")
            if "upload" in vt:
                tags.append("file-upload")
        # Program-based tags
        if finding.target and finding.target.name:
            prog = finding.target.name.split("_")[0].lower()
            tags.append(prog)
        return tags

    def _find_related_engrams(self, entry: KnowledgeEntry) -> list[str]:
        """Find engram IDs related to this entry by platform/program overlap."""
        related: list[str] = []
        entry_platform = entry.platform or ""
        entry_program = entry.program or ""
        for eid, mates in self._engraph.items():
            if eid == entry.engram_id:
                continue
            for mate in mates:
                if mate == entry.engram_id:
                    related.append(eid)
                    break
        # Also find by platform/program similarity
        for e in self._entries:
            if e.engram_id and e.engram_id != entry.engram_id and (e.platform == entry_platform or e.program == entry_program) and e.engram_id not in related:
                related.append(e.engram_id)
        return related

    def recall_engrams(self, platform: str | None = None, vuln_type: str | None = None, limit: int = 20) -> list[KnowledgeEntry]:
        """Recall relevant engrams from past sessions.

        Gentle AI: this is the core context-acquisition method.
        The agent reaches for relevant memories before re-reading the repo.

        Args:
            platform: Filter by platform (e.g., "hackerone", "freelancer")
            vuln_type: Filter by vulnerability type (e.g., "sql-injection")
            limit: Maximum entries to return

        Returns:
            List of KnowledgeEntry sorted by relevance (confidence + recency)
        """
        entries: list[KnowledgeEntry] = list(self._entries)
        # Filter by platform
        if platform:
            entries = [e for e in entries if e.platform == platform]
        # Filter by vulnerability type
        if vuln_type:
            entries = [e for e in entries if e.vuln_type == vuln_type]
        # Sort by confidence * recency (newer with higher confidence first)
        entries.sort(
            key=lambda e: e.confidence * (1 + 0.01 * (datetime.now(UTC).timestamp() - datetime.fromisoformat(e.created_at.replace("Z", "+00:00")).timestamp())),
            reverse=True,
        )
        return entries[:limit]

    def tag_engram(self, engram_id: str, tag: str) -> bool:
        """Add a user-defined tag to an engram."""
        entry = self.get_entry_by_id(engram_id)
        if not entry:
            return False
        if tag not in entry.tags:
            entry.tags.append(tag)
            self._save_engraph_to_disk()
            return True
        return False

    def get_entry_by_id(self, engram_id: str) -> KnowledgeEntry | None:
        """Get a knowledge entry by its engram ID."""
        for e in self._entries:
            if e.engram_id == engram_id:
                return e
        return None

    def get_entries_by_type(self, type_: LearningType) -> list[KnowledgeEntry]:
        return [e for e in self._entries if e.type == type_]

    def get_entries_by_vuln_type(self, vuln_type: str) -> list[KnowledgeEntry]:
        return [e for e in self._entries if e.vuln_type == vuln_type]

    def get_entries_by_platform(self, platform: str) -> list[KnowledgeEntry]:
        return [e for e in self._entries if e.platform == platform]

    def get_recent(self, limit: int = 20) -> list[KnowledgeEntry]:
        """Get most recent entries, sorted by recency."""
        return sorted(self._entries, key=lambda e: e.created_at, reverse=True)[:limit]

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
            "engram_id": entry.engram_id,
            "tags": entry.tags,
            "related_engrams": entry.related_engrams,
        }


_KNOWLEDGE_CAPTURE: KnowledgeCapture | None = None


def get_knowledge_capture() -> KnowledgeCapture:
    """Get the global KnowledgeCapture instance.

    Gentle AI: this is the entry point for the Engram system.
    Each session initializes from persistent storage, enabling
    context accumulation across restarts.
    """
    global _KNOWLEDGE_CAPTURE
    if _KNOWLEDGE_CAPTURE is None:
        _KNOWLEDGE_CAPTURE = KnowledgeCapture()
    return _KNOWLEDGE_CAPTURE
