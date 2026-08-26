"""Sync Engine Models — Shared types for offline-first synchronization."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SyncOperation(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SyncEntityType(StrEnum):
    WORK_ITEM = "work_item"
    OPPORTUNITY = "opportunity"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    SETTINGS = "settings"
    TASK = "task"
    GOAL = "goal"
    HABIT = "habit"
    MOOD = "mood"


class ConflictStrategy(StrEnum):
    LOCAL_WINS = "local"
    REMOTE_WINS = "remote"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass(slots=True)
class SyncEvent:
    event_id: str = field(default_factory=lambda: f"evt_{__import__('uuid').uuid4().hex[:12]}")
    entity_type: str = ""
    entity_id: str = ""
    operation: str = ""
    payload: dict = field(default_factory=dict)
    device_id: str = ""
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "operation": self.operation,
            "payload": self.payload,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SyncEvent:
        return cls(
            event_id=data.get("event_id", ""),
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id", ""),
            operation=data.get("operation", ""),
            payload=data.get("payload", {}),
            device_id=data.get("device_id", ""),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", 1),
        )


@dataclass(slots=True)
class SyncConflict:
    entity_id: str
    entity_type: str
    local_version: dict
    remote_version: dict
    strategy: str = "remote"
    resolved_at: str | None = None
    resolved_by: str = ""

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "local_version": self.local_version,
            "remote_version": self.remote_version,
            "strategy": self.strategy,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
        }


@dataclass(slots=True)
class SyncRequest:
    device_id: str
    last_sync_at: str
    events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "last_sync_at": self.last_sync_at,
            "events": self.events,
        }


@dataclass(slots=True)
class SyncResponse:
    success: bool = True
    events: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    server_time: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "events": self.events,
            "conflicts": self.conflicts,
            "server_time": self.server_time,
            "error": self.error,
        }


@dataclass(slots=True)
class PendingMutation:
    mutation_id: str = field(default_factory=lambda: f"mut_{__import__('uuid').uuid4().hex[:12]}")
    entity_type: str = ""
    entity_id: str = ""
    operation: str = ""
    payload: dict = field(default_factory=dict)
    device_id: str = ""
    created_at: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())
    retry_count: int = 0
    last_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "mutation_id": self.mutation_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "operation": self.operation,
            "payload": self.payload,
            "device_id": self.device_id,
            "created_at": self.created_at,
            "retry_count": self.retry_count,
            "last_error": self.last_error,
        }
