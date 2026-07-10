"""Decision Journal — append-only log of all agent decisions."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc

from core.database.manager import get_db_manager
from core.decision_journal.models import DecisionEntry, Base

logger = logging.getLogger("orion.core.decision_journal")

DB_ID = "orion"


def _ensure_db() -> None:
    mgr = get_db_manager()
    if DB_ID not in mgr.list_databases():
        mgr.register(DB_ID, "orion.db")
    mgr.run_migrations(DB_ID, Base)


def log_decision(
    app_id: str,
    agent_id: str,
    action: str,
    reason: str,
    data_snapshot: dict | None = None,
    confidence: float = 0.0,
    risk_score: float = 0.0,
) -> str:
    """Record a decision in the journal.

    Returns the decision_id.
    """
    _ensure_db()
    decision_id = f"{app_id}-{uuid.uuid4().hex[:12]}"
    db = get_db_manager().get_session(DB_ID)
    try:
        entry = DecisionEntry(
            app_id=app_id,
            agent_id=agent_id,
            decision_id=decision_id,
            action=action,
            reason=reason,
            data_snapshot=json.dumps(data_snapshot or {}),
            confidence=confidence,
            risk_score=risk_score,
        )
        db.add(entry)
        db.commit()
        logger.info("Decision logged: %s — %s (%s)", decision_id, action, app_id)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to log decision: %s", exc)
    finally:
        db.close()
    return decision_id


def record_outcome(decision_id: str, outcome: str, reward: float = 0.0, notes: str = "") -> bool:
    """Record the outcome of a previous decision (feedback loop)."""
    _ensure_db()
    db = get_db_manager().get_session(DB_ID)
    try:
        entry = db.query(DecisionEntry).filter(DecisionEntry.decision_id == decision_id).first()
        if entry is None:
            logger.warning("Decision %s not found for outcome recording", decision_id)
            return False
        entry.outcome = outcome
        entry.reward = reward
        entry.feedback_notes = notes
        entry.updated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Outcome recorded: %s → %s (reward=%.2f)", decision_id, outcome, reward)
        return True
    except Exception as exc:
        db.rollback()
        logger.error("Failed to record outcome: %s", exc)
        return False
    finally:
        db.close()


def get_decisions(
    app_id: str | None = None,
    agent_id: str | None = None,
    limit: int = 100,
    outcome: str | None = None,
) -> list[dict]:
    """Query the decision journal."""
    _ensure_db()
    db = get_db_manager().get_session(DB_ID)
    try:
        query = db.query(DecisionEntry)
        if app_id:
            query = query.filter(DecisionEntry.app_id == app_id)
        if agent_id:
            query = query.filter(DecisionEntry.agent_id == agent_id)
        if outcome:
            query = query.filter(DecisionEntry.outcome == outcome)
        entries = query.order_by(desc(DecisionEntry.executed_at)).limit(limit).all()
        return [
            {
                "id": e.id,
                "decision_id": e.decision_id,
                "app_id": e.app_id,
                "agent_id": e.agent_id,
                "action": e.action,
                "reason": e.reason,
                "confidence": e.confidence,
                "risk_score": e.risk_score,
                "outcome": e.outcome,
                "reward": e.reward,
                "executed_at": str(e.executed_at),
            }
            for e in entries
        ]
    finally:
        db.close()
