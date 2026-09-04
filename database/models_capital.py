"""Capital & Learning DB models — persistence for capital engine, goals, and learning loop."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FinancialGoal(Base):
    """A financial goal (auto, vivienda, reserva, $1M)."""

    __tablename__ = "financial_goals"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False, default=0.0)
    current_amount = Column(Float, nullable=False, default=0.0)
    monthly_contribution = Column(Float, nullable=False, default=0.0)
    priority = Column(Integer, nullable=False, default=1)
    category = Column(String, nullable=False, default="general")
    deadline_months = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class CapitalState(Base):
    """Current capital state — single row, always updated."""

    __tablename__ = "capital_state"

    id = Column(Integer, primary_key=True, default=1)
    net_worth = Column(Float, nullable=False, default=0.0)
    cash = Column(Float, nullable=False, default=0.0)
    savings = Column(Float, nullable=False, default=0.0)
    investments = Column(Float, nullable=False, default=0.0)
    monthly_income = Column(Float, nullable=False, default=0.0)
    monthly_expenses = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


class LearningAction(Base):
    """A recorded human action in the learning loop."""

    __tablename__ = "learning_actions"

    id = Column(String, primary_key=True)
    opportunity_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    human_minutes = Column(Float, nullable=False, default=0.0)
    expected_value = Column(Float, nullable=False, default=0.0)
    actual_revenue = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="pending")
    learning_tags = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)


class LearningInsight(Base):
    """A learning insight generated from action results."""

    __tablename__ = "learning_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    expected_value = Column(Float, nullable=False)
    actual_revenue = Column(Float, nullable=False)
    human_minutes = Column(Float, nullable=False)
    ev_per_hour = Column(Float, nullable=False)
    actual_per_hour = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    ev_accuracy = Column(Float, nullable=True)
    insight = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    learned_at = Column(DateTime, default=lambda: datetime.now(UTC))
