"""Task Hub Models — Unified task model across all platforms."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    """Status of a task across all platforms."""

    PENDING = "pending"  # Disponible para aceptar
    ACCEPTED = "accepted"  # Aceptada por el usuario
    IN_PROGRESS = "in_progress"  # En progreso
    SUBMITTED = "submitted"  # Trabajo enviado
    APPROVED = "approved"  # Aprobada/pagada
    REJECTED = "rejected"  # Rechazada
    EXPIRED = "expired"  # Expirada


class TaskPriority(StrEnum):
    """Priority level of a task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class UnifiedTask:
    """Unified task model across all platforms."""

    id: str  # Unique ID: platform_platform_id
    platform: str  # algora, freelancer, github, outlier, etc.
    platform_id: str  # Original ID from platform
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    reward: float  # USD
    estimated_hours: float
    platform_url: str
    submission_url: str | None = None
    deadline: str | None = None
    created_at: str = None
    updated_at: str = None
    synced_at: str = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(UTC).isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now(UTC).isoformat()
        if self.synced_at is None:
            self.synced_at = datetime.now(UTC).isoformat()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "platform": self.platform,
            "platform_id": self.platform_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "reward": self.reward,
            "estimated_hours": self.estimated_hours,
            "platform_url": self.platform_url,
            "submission_url": self.submission_url,
            "deadline": self.deadline,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "synced_at": self.synced_at,
            "metadata": self.metadata,
        }


@dataclass
class PlatformConnection:
    """Connection status for a platform."""

    platform: str
    connected: bool
    last_sync: str | None = None
    error: str | None = None
    total_tasks: int = 0
    pending_tasks: int = 0
    in_progress_tasks: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "connected": self.connected,
            "last_sync": self.last_sync,
            "error": self.error,
            "total_tasks": self.total_tasks,
            "pending_tasks": self.pending_tasks,
            "in_progress_tasks": self.in_progress_tasks,
        }
