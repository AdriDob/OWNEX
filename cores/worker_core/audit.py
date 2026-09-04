"""WorkerCore Audit Trail — immutable log of all workflow actions.

Every significant action in the WorkerCore lifecycle is recorded with:
- workflow_id: groups related actions in a single work cycle
- execution_id: unique per execution attempt (reset on resume)
- trace_id: distributed tracing context
- action, phase, status, cost, approval state, autonomy level

The audit log is append-only and never modified after creation.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from database.db import SessionLocal
from database.models import WorkerAuditLog

logger = logging.getLogger("worker_core.audit")


def create_audit_entry(
    *,
    workflow_id: str,
    execution_id: str,
    trace_id: str | None = None,
    work_item_id: str | None = None,
    action: str,
    phase: str | None = None,
    status: str = "pending",
    details: dict[str, Any] | None = None,
    error: str | None = None,
    cost_usd: float | None = None,
    requires_approval: bool = False,
    approved_by: str | None = None,
    approval_reason: str | None = None,
    autonomy_level: str | None = None,
    would_block_if_restricted: bool = False,
) -> WorkerAuditLog:
    """Create an immutable audit log entry.

    Args:
        workflow_id: Groups related actions in a single work cycle
        execution_id: Unique per execution attempt
        trace_id: Distributed tracing context
        work_item_id: Work item being acted upon
        action: Action name (discover, evaluate, execute, deliver, etc.)
        phase: Current workflow phase
        status: pending, success, failed, blocked, rejected
        details: Full context as JSON dict
        error: Error message if failed
        cost_usd: Cost of this action in USD
        requires_approval: Whether this action requires human approval
        approved_by: Who approved (human, auto, or None)
        approval_reason: Why it was approved/rejected
        autonomy_level: Current autonomy level
        would_block_if_restricted: Whether this would be blocked under stricter autonomy

    Returns:
        Created audit log entry
    """
    try:
        session = SessionLocal()
        entry = WorkerAuditLog(
            workflow_id=workflow_id,
            execution_id=execution_id,
            trace_id=trace_id,
            work_item_id=work_item_id,
            action=action,
            phase=phase,
            status=status,
            details=json.dumps(details, default=str) if details else None,
            error=error,
            cost_usd=cost_usd or 0.0,
            requires_approval="true" if requires_approval else "false",
            approved_by=approved_by,
            approval_reason=approval_reason,
            autonomy_level=autonomy_level,
            would_block_if_restricted="true" if would_block_if_restricted else "false",
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)  # Load all columns before session closes
        session.expunge(entry)  # Detach so fields are accessible after close
        logger.debug(
            "Audit: %s/%s %s → %s (workflow=%s)",
            action, phase or "-", status, work_item_id or "-", workflow_id[:8],
        )
        return entry
    except Exception as exc:
        logger.exception("Failed to create audit entry: %s", exc)
        # Create a dummy entry so callers don't break
        return WorkerAuditLog(
            workflow_id=workflow_id,
            execution_id=execution_id,
            action=action,
            status="error",
            error=f"Audit persistence failed: {exc}",
        )


def update_audit_entry(
    entry_id: int,
    *,
    status: str | None = None,
    details: dict[str, Any] | None = None,
    error: str | None = None,
    cost_usd: float | None = None,
    approved_by: str | None = None,
    approval_reason: str | None = None,
) -> WorkerAuditLog | None:
    """Update an existing audit entry (for completion status).

    Only status, details, error, cost, and approval fields are mutable.
    Action, workflow_id, execution_id are immutable.
    """
    try:
        session = SessionLocal()
        entry = session.query(WorkerAuditLog).filter(WorkerAuditLog.id == entry_id).first()
        if not entry:
            return None

        if status is not None:
            entry.status = status
        if details is not None:
            entry.details = json.dumps(details, default=str)
        if error is not None:
            entry.error = error
        if cost_usd is not None:
            entry.cost_usd = cost_usd
        if approved_by is not None:
            entry.approved_by = approved_by
        if approval_reason is not None:
            entry.approval_reason = approval_reason

        entry.completed_at = datetime.now(UTC)
        session.commit()
        return entry
    except Exception as exc:
        logger.exception("Failed to update audit entry %d: %s", entry_id, exc)
        return None


def get_workflow_audit(workflow_id: str, limit: int = 100) -> list[WorkerAuditLog]:
    """Get all audit entries for a workflow, chronological order."""
    try:
        session = SessionLocal()
        return (
            session.query(WorkerAuditLog)
            .filter(WorkerAuditLog.workflow_id == workflow_id)
            .order_by(WorkerAuditLog.id.asc())
            .limit(limit)
            .all()
        )
    except Exception as exc:
        logger.exception("Failed to get audit for workflow %s: %s", workflow_id, exc)
        return []


def get_execution_audit(execution_id: str) -> list[WorkerAuditLog]:
    """Get all audit entries for a single execution attempt."""
    try:
        session = SessionLocal()
        return (
            session.query(WorkerAuditLog)
            .filter(WorkerAuditLog.execution_id == execution_id)
            .order_by(WorkerAuditLog.id.asc())
            .all()
        )
    except Exception as exc:
        logger.exception("Failed to get audit for execution %s: %s", execution_id, exc)
        return []


def get_recent_audit(limit: int = 50, action: str | None = None) -> list[WorkerAuditLog]:
    """Get recent audit entries, optionally filtered by action type."""
    try:
        session = SessionLocal()
        query = session.query(WorkerAuditLog).order_by(WorkerAuditLog.id.desc())
        if action:
            query = query.filter(WorkerAuditLog.action == action)
        return query.limit(limit).all()
    except Exception as exc:
        logger.exception("Failed to get recent audit: %s", exc)
        return []


def get_audit_stats() -> dict[str, Any]:
    """Get aggregate audit statistics."""
    try:
        session = SessionLocal()
        total = session.query(WorkerAuditLog).count()
        blocked = session.query(WorkerAuditLog).filter(
            WorkerAuditLog.status == "blocked"
        ).count()
        failed = session.query(WorkerAuditLog).filter(
            WorkerAuditLog.status == "failed"
        ).count()
        pending_approval = session.query(WorkerAuditLog).filter(
            WorkerAuditLog.requires_approval == "true",
            WorkerAuditLog.approved_by.is_(None),
        ).count()

        # Total cost
        cost_result = session.execute(
            text("SELECT COALESCE(SUM(cost_usd), 0.0) FROM worker_audit_log")
        ).scalar()

        return {
            "total_entries": total,
            "blocked": blocked,
            "failed": failed,
            "pending_approval": pending_approval,
            "total_cost_usd": float(cost_result or 0.0),
        }
    except Exception as exc:
        logger.exception("Failed to get audit stats: %s", exc)
        return {
            "total_entries": 0,
            "blocked": 0,
            "failed": 0,
            "pending_approval": 0,
            "total_cost_usd": 0.0,
        }
