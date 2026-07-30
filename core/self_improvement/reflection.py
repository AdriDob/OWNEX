"""Self-Improvement System — Auto-reflection, reasoning, and continuous learning.

The system:
1. Captures errors, limitations, and failures
2. Reasons about root causes and solutions
3. Generates improvement suggestions
4. Updates code/knowledge automatically
5. Learns from user feedback
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.self_improvement")


class IssueType(str, Enum):
    """Type of issue/limitation."""
    API_FAILURE = "api_failure"
    MISSING_FEATURE = "missing_feature"
    USER_REJECTED = "user_rejected"
    ERROR = "error"
    LIMITATION = "limitation"
    SUGGESTION = "suggestion"


class Severity(str, Enum):
    """Severity of issue."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Reflection:
    """A reflection on something the system couldn't do or failed at."""
    id: str
    timestamp: str
    issue_type: IssueType
    severity: Severity
    context: str  # What the system was trying to do
    failure: str  # What went wrong
    root_cause: str  # Analysis of why it failed
    proposed_solution: str  # How to fix it
    priority: int  # 1-10, higher = more important
    status: str = "pending"  # pending, analyzing, implementing, completed, rejected
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "context": self.context,
            "failure": self.failure,
            "root_cause": self.root_cause,
            "proposed_solution": self.proposed_solution,
            "priority": self.priority,
            "status": self.status,
            "metadata": self.metadata,
        }


class SelfReflectionEngine:
    """Engine for capturing, analyzing, and learning from failures."""

    def __init__(self, storage_path: str | Path = "~/.config/ownex/reflections.json"):
        self.storage_path = Path(storage_path).expanduser()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._reflections: list[Reflection] = []
        self._load_reflections()

    def _load_reflections(self) -> None:
        """Load reflections from storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text())
                self._reflections = [
                    Reflection(
                        id=r["id"],
                        timestamp=r["timestamp"],
                        issue_type=IssueType(r["issue_type"]),
                        severity=Severity(r["severity"]),
                        context=r["context"],
                        failure=r["failure"],
                        root_cause=r["root_cause"],
                        proposed_solution=r["proposed_solution"],
                        priority=r["priority"],
                        status=r["status"],
                        metadata=r.get("metadata", {}),
                    )
                    for r in data
                ]
                logger.info(f"Loaded {len(self._reflections)} reflections")
            except Exception as e:
                logger.warning(f"Failed to load reflections: {e}")

    def _save_reflections(self) -> None:
        """Save reflections to storage."""
        try:
            data = [r.to_dict() for r in self._reflections]
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save reflections: {e}")

    def reflect(
        self,
        context: str,
        failure: str,
        issue_type: IssueType = IssueType.ERROR,
        severity: Severity = Severity.MEDIUM,
        metadata: dict[str, Any] | None = None,
    ) -> Reflection:
        """Create a new reflection about a failure/limitation."""
        reflection_id = f"ref_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

        # Use AI to analyze root cause and propose solution
        root_cause, proposed_solution = self._analyze_failure(context, failure)

        reflection = Reflection(
            id=reflection_id,
            timestamp=datetime.now(UTC).isoformat(),
            issue_type=issue_type,
            severity=severity,
            context=context,
            failure=failure,
            root_cause=root_cause,
            proposed_solution=proposed_solution,
            priority=self._calculate_priority(issue_type, severity),
            metadata=metadata or {},
        )

        self._reflections.append(reflection)
        self._save_reflections()

        logger.info(f"[REFLECTION] Created: {reflection_id} - {issue_type.value}")
        return reflection

    def _analyze_failure(self, context: str, failure: str) -> tuple[str, str]:
        """Analyze failure to determine root cause and propose solution.

        This is a simplified version. In production, would use AI model.
        """
        # Pattern-based analysis (can be enhanced with AI)
        if "API key" in failure.lower() or "authentication" in failure.lower():
            return (
                "Missing or invalid API credentials",
                "Add API key to ~/.config/ownex/opportunity.env or prompt user to configure",
            )
        elif "timeout" in failure.lower() or "connection" in failure.lower():
            return (
                "Network connectivity issue or API unavailable",
                "Implement retry logic, increase timeout, or check network status",
            )
        elif "not found" in failure.lower() or "404" in failure:
            return (
                "Resource or endpoint not found",
                "Verify URL/path is correct, check API documentation",
            )
        elif "permission" in failure.lower() or "403" in failure:
            return (
                "Insufficient permissions",
                "Check API key scopes, verify user has required permissions",
            )
        elif "format" in failure.lower() or "validation" in failure:
            return (
                "Data format or validation error",
                "Verify request format matches API specification, add validation",
            )
        else:
            return (
                "Unknown error - needs investigation",
                "Add detailed logging, capture full error context, implement error handling",
            )

    def _calculate_priority(self, issue_type: IssueType, severity: Severity) -> int:
        """Calculate priority based on issue type and severity."""
        base = {
            IssueType.API_FAILURE: 7,
            IssueType.MISSING_FEATURE: 6,
            IssueType.USER_REJECTED: 5,
            IssueType.ERROR: 8,
            IssueType.LIMITATION: 4,
            IssueType.SUGGESTION: 3,
        }

        severity_multiplier = {
            Severity.LOW: 0.5,
            Severity.MEDIUM: 1.0,
            Severity.HIGH: 1.5,
            Severity.CRITICAL: 2.0,
        }

        return int(base.get(issue_type, 5) * severity_multiplier.get(severity, 1.0))

    def get_pending_reflections(self) -> list[Reflection]:
        """Get all pending reflections (not completed)."""
        return [r for r in self._reflections if r.status == "pending"]

    def get_high_priority_reflections(self, limit: int = 10) -> list[Reflection]:
        """Get highest priority pending reflections."""
        pending = self.get_pending_reflections()
        return sorted(pending, key=lambda r: r.priority, reverse=True)[:limit]

    def update_reflection_status(self, reflection_id: str, new_status: str) -> bool:
        """Update status of a reflection."""
        for r in self._reflections:
            if r.id == reflection_id:
                r.status = new_status
                self._save_reflections()
                return True
        return False

    def generate_improvement_plan(self) -> dict[str, Any]:
        """Generate an improvement plan based on reflections."""
        pending = self.get_pending_reflections()
        high_priority = self.get_high_priority_reflections(5)

        # Group by issue type
        by_type: dict[str, int] = {}
        for r in pending:
            by_type[r.issue_type.value] = by_type.get(r.issue_type.value, 0) + 1

        return {
            "total_pending": len(pending),
            "high_priority_count": len(high_priority),
            "by_type": by_type,
            "top_improvements": [
                {
                    "id": r.id,
                    "issue": r.context,
                    "solution": r.proposed_solution,
                    "priority": r.priority,
                }
                for r in high_priority
            ],
        }


_reflection_engine: SelfReflectionEngine | None = None


def get_reflection_engine() -> SelfReflectionEngine:
    """Get singleton reflection engine."""
    global _reflection_engine
    if _reflection_engine is None:
        _reflection_engine = SelfReflectionEngine()
    return _reflection_engine
