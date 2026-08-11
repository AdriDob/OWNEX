"""Unified Memory — SQLAlchemy models for namespaced memory entries."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

DEFAULT_NAMESPACES = [
    "global",
    "cateye",
    "atlas",
    "odyssey",
    "hermes",
    "copilot",
    "user",
    "projects",
    "research",
    "decision_history",
]


class MemoryEntry(Base):
    """A single memory entry with namespace, content, tags, and priority.

    Entries can optionally expire (expires_at) and support future embedding storage.
    """

    __tablename__ = "core_memory"

    id = Column(Integer, primary_key=True)
    namespace = Column(String(64), nullable=False, index=True)
    key = Column(String(128), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    metadata_json = Column(Text, default="{}")
    tags = Column(Text, default="[]")
    priority = Column(Float, default=0.0)
    embedding = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "namespace": self.namespace,
            "key": self.key,
            "content": self.content,
            "metadata": json.loads(self.metadata_json or "{}"),
            "tags": json.loads(self.tags or "[]"),
            "priority": self.priority,
            "expires_at": str(self.expires_at) if self.expires_at else None,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
        }
