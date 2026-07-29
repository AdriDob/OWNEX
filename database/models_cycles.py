"""Cycle-specific data models — persists platform opportunities and sync state."""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from .db import Base


class CycleSyncLog(Base):
    """Tracks sync operations per cycle platform."""

    __tablename__ = "cycle_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    cycle_slug = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)
    status = Column(String, default="pending", index=True)
    opportunities_found = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)


class CycleOpportunity(Base):
    """Persisted raw opportunity fetched from a cycle platform."""

    __tablename__ = "cycle_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    cycle_slug = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, index=True)
    opportunity_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    reward = Column(Float, default=0.0)
    effort_hours = Column(Float, default=1.0)
    tags = Column(Text, nullable=True)
    source_type = Column(String, nullable=True)
    source_name = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    status = Column(String, default="active", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
