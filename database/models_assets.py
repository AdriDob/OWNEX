"""Asset model — structured scope assets for bug bounty programs.

Each asset is a single discoverable item: a domain, wildcard, mobile app,
API endpoint, smart contract, etc. Assets belong to Programs and can be
tracked for changes, health, and discovery status.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from database.db import Base

ASSET_TYPES = (
    "domain",
    "wildcard",
    "ip_range",
    "mobile_app",
    "api_endpoint",
    "graphql",
    "smart_contract",
    "binary",
    "source_code",
    "url",
    "other",
)


class Asset(Base):
    """A single scope asset belonging to a program."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False, index=True)
    asset_type = Column(String(32), nullable=False, index=True)
    value = Column(String(512), nullable=False, index=True)
    protocol = Column(String(16), default="")
    port = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    is_in_scope = Column(Boolean, default=True)
    tags = Column(Text, default="[]")
    source = Column(String(64), default="")
    confidence = Column(Float, default=0.8)
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
