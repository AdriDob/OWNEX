"""Learning Engine — extracts patterns from opportunity outcomes.

Every execution produces learning data. Patterns feed Strategy Engine,
Context Engine, and Evolution Engine for continuous improvement.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.engine.base import Engine
from core.engine.classification import Opportunity

logger = logging.getLogger("ownex.learning")


def _connect(db_path: str) -> sqlite3.Connection:
    """Connect to SQLite, handling :memory: with shared cache."""
    if db_path == ":memory:":
        return sqlite3.connect("file::memory:?cache=shared", uri=True)
    return sqlite3.connect(db_path)


# ── Core types ─────────────────────────────────────────────────────


@dataclass
class LearningRecord:
    """A single learning record from an opportunity outcome."""

    opportunity_id: str
    outcome: str  # "paid", "accepted", "rejected", "failed", "skipped", "submitted"
    source_type: str
    cycle: str
    platform: str

    # Metrics
    effort_hours: float = 0.0
    reward: float = 0.0
    acceptance_days: float = 0.0

    # Classification accuracy
    predicted_value: float = 0.0
    predicted_effort: float = 0.0
    confidence: float = 0.0

    # What we learned
    success_patterns: list[str] = field(default_factory=list)
    failure_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    notes: str = ""


@dataclass
class LearnedPattern:
    """A pattern extracted from learning records."""

    id: str
    pattern: str
    confidence: float
    source_type: str
    cycle: str
    times_applied: int = 0
    success_rate: float = 0.5
    success_count: int = 0
    total_count: int = 0
    last_applied: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Learning Engine ────────────────────────────────────────────────


class LearningEngine(Engine):
    """Extracts patterns from opportunity outcomes.

    Multi-level learning:
    - Per-opportunity: what worked for this specific type
    - Per-platform: which platforms have best acceptance rates
    - Per-tag: which skills/technologies yield highest EV
    - Per-cycle: which cycles are most profitable
    - Strategy: which strategies produced best outcomes
    """

    name = "learning_engine"

    def __init__(self, db_path: str = "~/.orion/learning.db") -> None:
        super().__init__()
        self.db_path = os.path.expanduser(db_path)
        self._patterns: dict[str, LearnedPattern] = {}

    def _init_db(self) -> None:
        if dirname := os.path.dirname(self.db_path):
            os.makedirs(dirname, exist_ok=True)
        conn = _connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT UNIQUE,
                outcome TEXT NOT NULL,
                source_type TEXT NOT NULL,
                cycle TEXT NOT NULL,
                platform TEXT NOT NULL,
                effort_hours REAL DEFAULT 0,
                reward REAL DEFAULT 0,
                acceptance_days REAL DEFAULT 0,
                predicted_value REAL DEFAULT 0,
                predicted_effort REAL DEFAULT 0,
                confidence REAL DEFAULT 0,
                success_patterns TEXT DEFAULT '[]',
                failure_patterns TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL,
                notes TEXT DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id TEXT PRIMARY KEY,
                pattern TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                source_type TEXT DEFAULT '',
                cycle TEXT DEFAULT '',
                times_applied INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.5,
                success_count INTEGER DEFAULT 0,
                total_count INTEGER DEFAULT 0,
                last_applied TEXT,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.commit()
        conn.close()
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load existing patterns from DB into memory."""
        try:
            conn = _connect(self.db_path)
            cursor = conn.execute("SELECT * FROM learned_patterns")
            for row in cursor.fetchall():
                try:
                    meta = json.loads(row[10] or "{}")
                except (json.JSONDecodeError, IndexError):
                    meta = {}
                last = None
                if row[9]:
                    with contextlib.suppress(ValueError, TypeError):
                        last = datetime.fromisoformat(row[9])
                self._patterns[row[0]] = LearnedPattern(
                    id=row[0],
                    pattern=row[1],
                    confidence=row[2],
                    source_type=row[3],
                    cycle=row[4],
                    times_applied=row[5],
                    success_rate=row[6],
                    success_count=row[7],
                    total_count=row[8],
                    last_applied=last,
                    metadata=meta,
                )
            conn.close()
        except (sqlite3.OperationalError, FileNotFoundError):
            pass

    async def record_outcome(
        self,
        opportunity: Opportunity,
        execution_result: Any,
        outcome: str,
        reward: float = 0.0,
        effort_hours: float = 0.0,
        notes: str = "",
    ) -> LearningRecord:
        """Record the outcome of an executed opportunity."""
        record = LearningRecord(
            opportunity_id=opportunity.id,
            outcome=outcome,
            source_type=opportunity.source_type,
            cycle=opportunity.cycle,
            platform=opportunity.source_name,
            effort_hours=effort_hours,
            reward=reward,
            predicted_value=opportunity.estimated_reward_max,
            predicted_effort=opportunity.estimated_effort_hours,
            confidence=opportunity.confidence,
            tags=opportunity.technology_tags,
            notes=notes,
        )

        # Extract success/failure patterns from execution
        if outcome in ("paid", "accepted"):
            record.success_patterns = self._extract_success_patterns(execution_result)
        elif outcome in ("rejected", "failed"):
            record.failure_patterns = self._extract_failure_patterns(execution_result)

        # Persist
        self._persist_record(record)

        # Extract patterns
        await self._extract_patterns(record)

        return record

    def _extract_success_patterns(self, result: Any) -> list[str]:
        patterns: list[str] = []
        completed_steps = getattr(result, "completed_steps", [])
        for step in completed_steps:
            if step.status == "completed" and step.result and step.completed_at and step.started_at:
                actual_min = (step.completed_at - step.started_at).total_seconds() / 60
                if actual_min > 0 and step.estimated_minutes > 0:
                    ratio = actual_min / step.estimated_minutes
                    if ratio < 0.5:
                        patterns.append(f"Step '{step.name}' completed in {ratio:.0%} of estimated time")
                    elif ratio > 2:
                        patterns.append(f"Step '{step.name}' took {ratio:.0%} of estimated time (underestimated)")
        return patterns

    def _extract_failure_patterns(self, result: Any) -> list[str]:
        patterns: list[str] = []
        failed_step = getattr(result, "failed_step", None)
        if failed_step:
            patterns.append(f"Failed at step '{failed_step.name}'")
            if getattr(failed_step, "retry_count", 0) > 0:
                patterns.append(f"Required {failed_step.retry_count} retries before failure")
        error = getattr(result, "error", "")
        if error:
            patterns.append(f"Error pattern: {error[:200]}")
        return patterns

    def _persist_record(self, record: LearningRecord) -> None:
        conn = _connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO learning_records
               (opportunity_id, outcome, source_type, cycle, platform,
                effort_hours, reward, acceptance_days, predicted_value,
                predicted_effort, confidence, success_patterns, failure_patterns,
                tags, timestamp, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.opportunity_id,
                record.outcome,
                record.source_type,
                record.cycle,
                record.platform,
                record.effort_hours,
                record.reward,
                record.acceptance_days,
                record.predicted_value,
                record.predicted_effort,
                record.confidence,
                json.dumps(record.success_patterns),
                json.dumps(record.failure_patterns),
                json.dumps(record.tags),
                record.timestamp.isoformat(),
                record.notes,
            ),
        )
        conn.commit()
        conn.close()

    async def _extract_patterns(self, record: LearningRecord) -> None:
        """Extract and update learned patterns from this record."""
        conn = _connect(self.db_path)

        # Pattern: acceptance rate by source_type + platform
        cursor = conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN outcome IN ('paid', 'accepted') THEN 1 ELSE 0 END) as success "
            "FROM learning_records WHERE source_type = ? AND platform = ?",
            (record.source_type, record.platform),
        )
        row = cursor.fetchone()
        total, success = row[0], row[1] or 0

        pattern_id = f"acceptance:{record.source_type}:{record.platform}"
        pattern = LearnedPattern(
            id=pattern_id,
            pattern=(
                f"Acceptance rate for {record.platform} ({record.source_type}): "
                f"{success}/{total} = {success / total:.0%}"
                if total > 0
                else "No data yet"
            ),
            confidence=min(0.3 + total * 0.05, 0.95),
            source_type=record.source_type,
            cycle=record.cycle,
            times_applied=total,
            success_rate=success / total if total > 0 else 0.5,
            success_count=success,
            total_count=total,
            last_applied=record.timestamp,
        )
        self._patterns[pattern_id] = pattern

        conn.execute(
            "INSERT OR REPLACE INTO learned_patterns "
            "(id, pattern, confidence, source_type, cycle, times_applied, "
            "success_rate, success_count, total_count, last_applied, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pattern_id,
                pattern.pattern,
                pattern.confidence,
                pattern.source_type,
                pattern.cycle,
                pattern.times_applied,
                pattern.success_rate,
                pattern.success_count,
                pattern.total_count,
                pattern.last_applied.isoformat() if pattern.last_applied else None,
                json.dumps(pattern.metadata),
            ),
        )
        conn.commit()
        conn.close()

    def get_patterns_for_source(
        self,
        source_type: str,
        cycle: str,
    ) -> list[LearnedPattern]:
        return [p for p in self._patterns.values() if p.source_type == source_type or p.cycle == cycle]

    def get_statistics(self) -> dict[str, Any]:
        try:
            conn = _connect(self.db_path)
            cursor = conn.execute("SELECT outcome, COUNT(*) FROM learning_records GROUP BY outcome")
            outcomes = dict(cursor.fetchall())

            cursor = conn.execute(
                "SELECT source_type, COUNT(*) as total, "
                "SUM(CASE WHEN outcome IN ('paid', 'accepted') THEN 1 ELSE 0 END) as success "
                "FROM learning_records GROUP BY source_type"
            )
            by_type: dict[str, dict[str, int]] = {}
            for row in cursor:
                by_type[row[0]] = {"total": row[1], "success": row[2] or 0}

            cursor = conn.execute("SELECT COUNT(*) FROM learning_records")
            total_records = cursor.fetchone()[0]
            conn.close()
        except (sqlite3.OperationalError, FileNotFoundError):
            total_records = 0
            outcomes = {}
            by_type = {}

        return {
            "total_records": total_records,
            "outcomes": outcomes,
            "by_source_type": by_type,
            "patterns_count": len(self._patterns),
        }

    async def initialize(self) -> None:
        self._init_db()
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "name": self.name,
            "db_path": self.db_path,
            "total_records": self.get_statistics().get("total_records", 0),
            "patterns": len(self._patterns),
        }
