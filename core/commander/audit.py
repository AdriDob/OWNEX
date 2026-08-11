"""Permanent audit module for all Commander actions.

Every action taken by the Commander is logged with:
- objective
- reasoning summary
- tools used
- changes made
- validation
- result

This provides full traceability for future agents and debugging.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.commander.audit")

AUDIT_LOG_PATH = Path("~/.orion/commander_audit.jsonl").expanduser()


@dataclass
class AuditEntry:
    """Single audit entry for a Commander action."""

    entry_id: str
    timestamp: str
    objective: str
    reasoning: str
    tools_used: list[str]
    changes_made: list[str]
    validation: str
    result: str
    provider_used: str
    model_used: str
    agent_id: str
    session_id: str
    success: bool
    duration_ms: float = 0.0
    failover_used: bool = False
    failover_from: str = ""
    failover_to: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "objective": self.objective,
            "reasoning": self.reasoning,
            "tools_used": self.tools_used,
            "changes_made": self.changes_made,
            "validation": self.validation,
            "result": self.result,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "success": self.success,
            "duration_ms": round(self.duration_ms, 1),
            "failover_used": self.failover_used,
            "failover_from": self.failover_from,
            "failover_to": self.failover_to,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class AuditLogger:
    """Logs Commander actions permanently to disk for traceability."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._session_id = f"session-{int(datetime.now(UTC).timestamp())}"
        self._load_existing()

    def log(
        self,
        objective: str,
        reasoning: str,
        tools_used: list[str],
        changes_made: list[str],
        validation: str,
        result: str,
        provider_used: str,
        model_used: str,
        agent_id: str,
        success: bool = True,
        duration_ms: float = 0.0,
        failover_used: bool = False,
        failover_from: str = "",
        failover_to: str = "",
    ) -> AuditEntry:
        """Log a Commander action."""
        entry = AuditEntry(
            entry_id=f"audit-{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(UTC).isoformat(),
            objective=objective,
            reasoning=reasoning,
            tools_used=tools_used,
            changes_made=changes_made,
            validation=validation,
            result=result,
            provider_used=provider_used,
            model_used=model_used,
            agent_id=agent_id,
            session_id=self._session_id,
            success=success,
            duration_ms=duration_ms,
            failover_used=failover_used,
            failover_from=failover_from,
            failover_to=failover_to,
        )

        self._entries.append(entry)
        self._persist(entry)

        logger.info(
            "Audit: %s -> %s (success=%s, duration=%.0fms)",
            objective,
            result,
            success,
            duration_ms,
        )

        return entry

    def _persist(self, entry: AuditEntry) -> None:
        """Append entry to persistent log file."""
        try:
            AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(AUDIT_LOG_PATH, "a") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            logger.warning("Failed to persist audit entry: %s", e)

    def _load_existing(self) -> None:
        """Load existing audit entries from disk."""
        try:
            if AUDIT_LOG_PATH.exists():
                with open(AUDIT_LOG_PATH) as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            entry = AuditEntry(**data)
                            self._entries.append(entry)
                logger.info("Loaded %d existing audit entries", len(self._entries))
        except Exception as e:
            logger.warning("Failed to load audit history: %s", e)

    def get_entries(
        self,
        limit: int = 50,
        session_id: str | None = None,
        success_only: bool = False,
        failover_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve audit entries with optional filtering."""
        entries = self._entries

        if session_id:
            entries = [e for e in entries if e.session_id == session_id]
        if success_only:
            entries = [e for e in entries if e.success]
        if failover_only:
            entries = [e for e in entries if e.failover_used]

        return [e.to_dict() for e in entries[-limit:]]

    def get_session_summary(self, session_id: str | None = None) -> dict[str, Any]:
        """Get a summary of audit entries for a session."""
        entries = self._entries
        if session_id:
            entries = [e for e in entries if e.session_id == session_id]

        total = len(entries)
        successes = sum(1 for e in entries if e.success)
        failovers = sum(1 for e in entries if e.failover_used)
        avg_duration = sum(e.duration_ms for e in entries) / max(total, 1)

        return {
            "session_id": session_id or self._session_id,
            "total_entries": total,
            "successful": successes,
            "failed": total - successes,
            "failovers_used": failovers,
            "average_duration_ms": round(avg_duration, 1),
            "first_entry": entries[0].timestamp if entries else "",
            "last_entry": entries[-1].timestamp if entries else "",
        }


_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get the singleton AuditLogger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def log_action(
    objective: str,
    reasoning: str,
    tools_used: list[str],
    changes_made: list[str],
    validation: str,
    result: str,
    provider_used: str,
    model_used: str,
    agent_id: str,
    success: bool = True,
    duration_ms: float = 0.0,
    failover_used: bool = False,
    failover_from: str = "",
    failover_to: str = "",
) -> AuditEntry:
    """Convenience function to log an action immediately."""
    logger = get_audit_logger()
    return logger.log(
        objective=objective,
        reasoning=reasoning,
        tools_used=tools_used,
        changes_made=changes_made,
        validation=validation,
        result=result,
        provider_used=provider_used,
        model_used=model_used,
        agent_id=agent_id,
        success=success,
        duration_ms=duration_ms,
        failover_used=failover_used,
        failover_from=failover_from,
        failover_to=failover_to,
    )
