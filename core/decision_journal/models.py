from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DecisionEntry(Base):
    """Immutable record of an agent decision."""

    __tablename__ = "core_decision_journal"

    id = Column(Integer, primary_key=True)
    app_id = Column(String(32), nullable=False, index=True)  # atlas, odyssey, cateye
    agent_id = Column(String(64), nullable=False, index=True)
    decision_id = Column(String(64), unique=True, nullable=False)
    action = Column(String(128), nullable=False)  # rebalance, buy, sell, alert
    reason = Column(Text, nullable=False)  # why this decision
    data_snapshot = Column(Text, default="")  # serialized context
    confidence = Column(Float, default=0.0)  # 0.0 - 1.0
    risk_score = Column(Float, default=0.0)  # 0.0 - 1.0
    outcome = Column(String(32), default="pending")  # pending, success, failure
    reward = Column(Float, default=0.0)  # feedback reward
    feedback_notes = Column(Text, default="")
    executed_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
