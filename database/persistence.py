"""Persistence layer — saves capital state, goals, and learning actions to DB."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from database.db import SessionLocal
from database.models_capital import CapitalState, FinancialGoal, LearningAction, LearningInsight

logger = logging.getLogger("ownex.persistence")


def _ensure_tables() -> None:
    """Create capital/learning tables if they don't exist."""
    try:
        from database.db import engine
        from database.models_capital import Base

        Base.metadata.create_all(engine)
    except Exception as exc:
        logger.warning("Failed to create capital tables: %s", exc)


# Run on import
_ensure_tables()


class CapitalPersistence:
    """Persist capital state and goals to DB."""

    def save_state(self, state: Any) -> None:
        """Save capital state to DB."""
        try:
            with SessionLocal() as session:
                existing = session.query(CapitalState).first()
                if existing:
                    existing.net_worth = state.net_worth
                    existing.cash = state.cash
                    existing.savings = state.savings
                    existing.investments = state.investments
                    existing.monthly_income = state.monthly_income
                    existing.monthly_expenses = state.monthly_expenses
                    existing.updated_at = datetime.now(UTC)
                else:
                    session.add(
                        CapitalState(
                            id=1,
                            net_worth=state.net_worth,
                            cash=state.cash,
                            savings=state.savings,
                            investments=state.investments,
                            monthly_income=state.monthly_income,
                            monthly_expenses=state.monthly_expenses,
                        )
                    )
                session.commit()
        except Exception as exc:
            logger.warning("Failed to save capital state: %s", exc)

    def load_state(self) -> dict[str, Any] | None:
        """Load capital state from DB."""
        try:
            with SessionLocal() as session:
                state = session.query(CapitalState).first()
                if state:
                    return {
                        "net_worth": state.net_worth,
                        "cash": state.cash,
                        "savings": state.savings,
                        "investments": state.investments,
                        "monthly_income": state.monthly_income,
                        "monthly_expenses": state.monthly_expenses,
                    }
        except Exception as exc:
            logger.warning("Failed to load capital state: %s", exc)
        return None

    def save_goals(self, goals: list[Any]) -> None:
        """Save financial goals to DB."""
        try:
            with SessionLocal() as session:
                # Clear existing
                session.query(FinancialGoal).delete()
                # Add new
                for goal in goals:
                    session.add(
                        FinancialGoal(
                            id=goal.id,
                            name=goal.name,
                            target_amount=goal.target_amount,
                            current_amount=goal.current_amount,
                            monthly_contribution=goal.monthly_contribution,
                            priority=goal.priority,
                            category=goal.category,
                            deadline_months=goal.deadline_months,
                            notes=goal.notes,
                        )
                    )
                session.commit()
        except Exception as exc:
            logger.warning("Failed to save goals: %s", exc)

    def load_goals(self) -> list[dict[str, Any]]:
        """Load financial goals from DB."""
        try:
            with SessionLocal() as session:
                goals = session.query(FinancialGoal).all()
                return [
                    {
                        "id": g.id,
                        "name": g.name,
                        "target_amount": g.target_amount,
                        "current_amount": g.current_amount,
                        "monthly_contribution": g.monthly_contribution,
                        "priority": g.priority,
                        "category": g.category,
                        "deadline_months": g.deadline_months,
                        "notes": g.notes,
                    }
                    for g in goals
                ]
        except Exception as exc:
            logger.warning("Failed to load goals: %s", exc)
            return []


class LearningPersistence:
    """Persist learning actions and insights to DB."""

    def save_action(self, action: Any) -> None:
        """Save a learning action to DB."""
        try:
            with SessionLocal() as session:
                session.add(
                    LearningAction(
                        id=action.id,
                        opportunity_id=action.opportunity_id,
                        action_type=action.action_type,
                        title=action.title,
                        description=action.description,
                        human_minutes=action.human_minutes,
                        expected_value=action.expected_value,
                        actual_revenue=action.actual_revenue,
                        status=action.status,
                        learning_tags=json.dumps(action.learning_tags),
                        completed_at=action.completed_at,
                        paid_at=action.paid_at,
                    )
                )
                session.commit()
        except Exception as exc:
            logger.warning("Failed to save learning action: %s", exc)

    def update_action(self, action: Any) -> None:
        """Update a learning action in DB."""
        try:
            with SessionLocal() as session:
                existing = session.query(LearningAction).filter(LearningAction.id == action.id).first()
                if existing:
                    existing.actual_revenue = action.actual_revenue
                    existing.status = action.status
                    existing.completed_at = action.completed_at
                    existing.paid_at = action.paid_at
                    existing.learning_tags = json.dumps(action.learning_tags)
                    session.commit()
        except Exception as exc:
            logger.warning("Failed to update learning action: %s", exc)

    def save_insight(self, insight: dict[str, Any]) -> None:
        """Save a learning insight to DB."""
        try:
            with SessionLocal() as session:
                session.add(
                    LearningInsight(
                        action_id=insight.get("action_id", ""),
                        action_type=insight.get("action_type", ""),
                        expected_value=insight.get("expected_value", 0),
                        actual_revenue=insight.get("actual_revenue", 0),
                        human_minutes=insight.get("human_minutes", 0),
                        ev_per_hour=insight.get("ev_per_hour", 0),
                        actual_per_hour=insight.get("actual_per_hour", 0),
                        status=insight.get("status", ""),
                        ev_accuracy=insight.get("ev_accuracy"),
                        insight=insight.get("insight"),
                        tags=json.dumps(insight.get("tags", [])),
                    )
                )
                session.commit()
        except Exception as exc:
            logger.warning("Failed to save learning insight: %s", exc)

    def load_actions(self, limit: int = 100) -> list[dict[str, Any]]:
        """Load recent learning actions from DB."""
        try:
            with SessionLocal() as session:
                actions = session.query(LearningAction).order_by(LearningAction.created_at.desc()).limit(limit).all()
                return [
                    {
                        "id": a.id,
                        "opportunity_id": a.opportunity_id,
                        "action_type": a.action_type,
                        "title": a.title,
                        "human_minutes": a.human_minutes,
                        "expected_value": a.expected_value,
                        "actual_revenue": a.actual_revenue,
                        "status": a.status,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in actions
                ]
        except Exception as exc:
            logger.warning("Failed to load learning actions: %s", exc)
            return []

    def load_insights(self, limit: int = 50) -> list[dict[str, Any]]:
        """Load recent learning insights from DB."""
        try:
            with SessionLocal() as session:
                insights = session.query(LearningInsight).order_by(LearningInsight.learned_at.desc()).limit(limit).all()
                return [
                    {
                        "action_id": i.action_id,
                        "action_type": i.action_type,
                        "ev_accuracy": i.ev_accuracy,
                        "insight": i.insight,
                        "learned_at": i.learned_at.isoformat() if i.learned_at else None,
                    }
                    for i in insights
                ]
        except Exception as exc:
            logger.warning("Failed to load learning insights: %s", exc)
            return []


# Singletons
_capital_persistence: CapitalPersistence | None = None
_learning_persistence: LearningPersistence | None = None


def get_capital_persistence() -> CapitalPersistence:
    global _capital_persistence
    if _capital_persistence is None:
        _capital_persistence = CapitalPersistence()
    return _capital_persistence


def get_learning_persistence() -> LearningPersistence:
    global _learning_persistence
    if _learning_persistence is None:
        _learning_persistence = LearningPersistence()
    return _learning_persistence
