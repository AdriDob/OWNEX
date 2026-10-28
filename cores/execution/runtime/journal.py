from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class JournalEntry:
    """A single entry in an execution journal.

    Records everything that happened during a node execution:
    input, output, decisions, duration, resources, exceptions.
    """

    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    execution_id: str = ""
    workflow_id: str = ""
    node_id: str = ""
    node_type: str = ""
    correlation_id: str = ""
    timestamp: float = 0.0
    input_data: dict[str, Any] = field(default_factory=dict)
    output_data: dict[str, Any] = field(default_factory=dict)
    decision: str | None = None
    duration_ms: float = 0.0
    cpu_ms: float = 0.0
    ram_mb: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    api_calls: int = 0
    retry_count: int = 0
    error: str | None = None
    exception: str | None = None
    snapshot: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "node_id": self.node_id,
            "node_type": self.node_type,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "decision": self.decision,
            "duration_ms": self.duration_ms,
            "cpu_ms": self.cpu_ms,
            "ram_mb": self.ram_mb,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "api_calls": self.api_calls,
            "retry_count": self.retry_count,
            "error": self.error,
            "exception": self.exception,
            "snapshot": self.snapshot,
        }


class ExecutionJournal:
    """Persistent journal for a single workflow execution.

    Each node execution produces one entry. The journal is the
    foundation for the Time Machine (DVR-style replay).
    """

    def __init__(self, execution_id: str, workflow_id: str, correlation_id: str) -> None:
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.correlation_id = correlation_id
        self._entries: list[JournalEntry] = []
        self._entry_map: dict[str, JournalEntry] = {}

    def record(self, entry: JournalEntry) -> None:
        self._entries.append(entry)
        self._entry_map[entry.entry_id] = entry

    def create_entry(
        self,
        node_id: str,
        node_type: str,
        timestamp: float,
        *,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        decision: str | None = None,
        duration_ms: float = 0.0,
        cpu_ms: float = 0.0,
        ram_mb: float = 0.0,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
        api_calls: int = 0,
        retry_count: int = 0,
        error: str | None = None,
        exception: str | None = None,
        snapshot: dict[str, Any] | None = None,
    ) -> JournalEntry:
        entry = JournalEntry(
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            node_id=node_id,
            node_type=node_type,
            correlation_id=self.correlation_id,
            timestamp=timestamp,
            input_data=input_data or {},
            output_data=output_data or {},
            decision=decision,
            duration_ms=duration_ms,
            cpu_ms=cpu_ms,
            ram_mb=ram_mb,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            api_calls=api_calls,
            retry_count=retry_count,
            error=error,
            exception=exception,
            snapshot=snapshot,
        )
        self.record(entry)
        return entry

    def get_entry(self, entry_id: str) -> JournalEntry | None:
        return self._entry_map.get(entry_id)

    def get_node_entries(self, node_id: str) -> list[JournalEntry]:
        return [e for e in self._entries if e.node_id == node_id]

    @property
    def entries(self) -> list[JournalEntry]:
        return list(self._entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def to_dict(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._entries]

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def clear(self) -> None:
        self._entries.clear()
        self._entry_map.clear()

    def replay(self) -> list[JournalEntry]:
        """Return all entries in order for Time Machine replay."""
        return list(self._entries)
