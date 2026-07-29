"""Cycle Engine — SQLAlchemy models for Work Cycles."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CycleStatus(str, Enum):
    INACTIVE = "inactive"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"


class CycleCategory(str, Enum):
    SECURITY = "security"
    FORGE = "forge"
    PULSE = "pulse"
    VAULT = "vault"
    ATLAS = "atlas"


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    CREATED = "created"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Default cycles for seeding database - needs to match registry.py
DEFAULT_CYCLES = [
    {
        "name": "Security",
        "slug": "security",
        "description": "Bug bounty, vulnerability research, Rastro pipeline",
        "category": "offensive",
        "status": "idle",
        "enabled": True,
        "priority": 10,
        "config": {
            "source_apps": ["rastro", "aegis"],
            "auto_priority": True,
        },
    },
    {
        "name": "Forge",
        "slug": "forge",
        "description": "Dev bounties, OSS contributions, code review rewards",
        "category": "development",
        "status": "idle",
        "enabled": True,
        "priority": 8,
        "config": {
            "platforms": ["superteam", "opire", "algora", "issuehunt"],
            "auto_discover": True,
        },
    },
    {
        "name": "Pulse",
        "slug": "pulse",
        "description": "AI training, data annotation, microtask platforms",
        "category": "ai_work",
        "status": "idle",
        "enabled": True,
        "priority": 6,
        "config": {
            "platforms": ["outlier", "dataannotation", "mindrift", "remotasks"],
            "skill_match": True,
        },
    },
    {
        "name": "Vault",
        "slug": "vault",
        "description": "Portfolio management, crypto, DeFi, arbitrage, financial analysis",
        "category": "finance",
        "status": "idle",
        "enabled": True,
        "priority": 7,
        "config": {
            "data_sources": ["coingecko", "defillama", "coingecko"],
            "auto_rebalance": False,
        },
    },
    {
        "name": "Atlas",
        "slug": "atlas",
        "description": "Research, OSINT, trend analysis, CVE tracking, market intelligence",
        "category": "intelligence",
        "status": "idle",
        "enabled": True,
        "priority": 5,
        "config": {
            "sources": ["cve", "github", "twitter", "rss"],
            "alert_threshold": "high",
        },
    },
]


class Cycle(Base):
    """Work Cycle entity — persistent, measurable, actionable."""

    __tablename__ = "cycles"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    slug = Column(String(32), nullable=False, unique=True, index=True)
    description = Column(Text, default="")
    category = Column(String(32), nullable=False, index=True)
    status = Column(String(16), nullable=False, default=CycleStatus.INACTIVE.value, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)
    config = Column(Text, default="{}")  # JSON config for cycle-specific settings
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    tasks = relationship("Task", back_populates="cycle", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "enabled": self.enabled,
            "priority": self.priority,
            "config": json.loads(self.config or "{}"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def config_dict(self) -> dict[str, Any]:
        try:
            return json.loads(self.config or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    def update_config(self, updates: dict[str, Any]) -> None:
        current = self.config_dict
        current.update(updates)
        self.config = json.dumps(current)


class Task(Base):
    """Task entity — individual work unit within a cycle."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    cycle_id = Column(Integer, ForeignKey("cycles.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")
    status = Column(String(16), nullable=False, default=TaskStatus.PENDING.value, index=True)
    priority = Column(Integer, nullable=False, default=0)
    order = Column(Integer, nullable=False, default=0)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    estimated_reward = Column(Float, nullable=True)
    actual_reward = Column(Float, nullable=True)
    target_id = Column(Integer, nullable=True)  # Reference to external target/finding/etc.
    target_type = Column(String(32), nullable=True)  # 'finding', 'opportunity', 'target', etc.
    config = Column(Text, default="{}")  # JSON config for task-specific settings
    result = Column(Text, default="{}")  # JSON result data
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    cycle = relationship("Cycle", back_populates="tasks")
    executions = relationship("ExecutionState", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "estimated_reward": self.estimated_reward,
            "actual_reward": self.actual_reward,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "config": json.loads(self.config or "{}"),
            "result": json.loads(self.result or "{}"),
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExecutionState(Base):
    """Execution state — tracks actual execution runs of a task."""

    __tablename__ = "execution_states"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default=ExecutionStatus.CREATED.value, index=True)
    progress = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    current_step = Column(String(64), nullable=True)
    total_steps = Column(Integer, nullable=True)
    completed_steps = Column(Integer, nullable=False, default=0)
    logs = Column(Text, default="[]")  # JSON array of log entries
    metrics = Column(Text, default="{}")  # JSON metrics
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    task = relationship("Task", back_populates="executions")
