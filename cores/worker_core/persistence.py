"""WorkerCore persistence — checkpoint persistence and resume capability.

Persistence layer for WorkerCore work items. Checkpoints are written to the
SQLite ``worker_checkpoints`` table so a workflow can survive an unexpected
crash/restart and resume from the last completed phase.

This is a thin adapter over the SQLAlchemy model; the WorkerCore orchestrator
holds the workflow state machine, this module owns durable state.
"""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from database.db import SessionLocal
from database.models import WorkerCheckpoint

logger = logging.getLogger("worker_core.persistence")

# Phases in dependency order (the state machine progression).
PHASE_ORDER = [
    "discover",
    "evaluate",
    "select",
    "prepare",
    "execute",
    "validate",
    "deliver",
    "learn",
]

# Phases after which an external, expensive action is typically persisted
# and therefore safe to resume from (avoid re-running them).
_RESUMABLE_AFTER = ["discover", "evaluate", "select", "prepare", "execute", "validate", "deliver"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def save_checkpoint(
    work_item_id: str,
    phase: str,
    checkpoint_data: dict[str, Any] | None = None,
    *,
    work_item_title: str = "",
    work_item_platform: str = "",
    work_item_category: str = "",
    phase_completed: bool = True,
    error: str | None = None,
    retry_count: int = 0,
    session: Any = None,
) -> None:
    """Persist a WorkerCore checkpoint for a work item.

    A checkpoint marks "we have reached phase X". If ``phase_completed`` is
    True, the worker may resume AFTER this phase (e.g. a resume from
    ``execute`` means we do not re-execute).
    """
    sess = session or SessionLocal()
    created = session is None
    try:
        row = WorkerCheckpoint(
            work_item_id=work_item_id,
            work_item_title=work_item_title,
            work_item_platform=work_item_platform,
            work_item_category=work_item_category,
            phase=phase,
            checkpoint_data=json.dumps(checkpoint_data or {}, default=str),
            phase_completed="true" if phase_completed else "false",
            error=error,
            retry_count=retry_count,
        )
        sess.add(row)
        sess.commit() if session is None else sess.flush()
        logger.info("Checkpoint saved: work=%s phase=%s", work_item_id, phase)
    except Exception as exc:  # persistence must never crash the worker
        logger.exception("Failed to persist checkpoint work=%s phase=%s: %s", work_item_id, phase, exc)
    finally:
        if created:
            with contextlib.suppress(Exception):
                sess.close()


def get_latest_checkpoint(work_item_id: str, session: Any = None) -> WorkerCheckpoint | None:
    """Return the most recent checkpoint for a work item (by autoincrement id desc).

    The ``id`` primary key is monotonic and therefore gives reliable insertion
    order; ``updated_at`` is not reliable because ``server_default=func.now()``
    produces identical timestamps for rows inserted within the same second.
    """
    sess = session or SessionLocal()
    created = session is None
    try:
        row = (
            sess.query(WorkerCheckpoint)
            .filter(WorkerCheckpoint.work_item_id == work_item_id)
            .order_by(WorkerCheckpoint.id.desc())
            .first()
        )
        return row
    except Exception as exc:
        logger.exception("Failed to load latest checkpoint work=%s: %s", work_item_id, exc)
        return None
    finally:
        if created:
            with contextlib.suppress(Exception):
                sess.close()


def get_all_checkpoints(work_item_id: str, session: Any = None) -> list[WorkerCheckpoint]:
    """Return all checkpoints for a work item in chronological order."""
    sess = session or SessionLocal()
    created = session is None
    try:
        return (
            sess.query(WorkerCheckpoint)
            .filter(WorkerCheckpoint.work_item_id == work_item_id)
            .order_by(WorkerCheckpoint.id.asc())
            .all()
        )
    except Exception as exc:
        logger.exception("Failed to load checkpoints work=%s: %s", work_item_id, exc)
        return []
    finally:
        if created:
            with contextlib.suppress(Exception):
                sess.close()


def get_active_work_items(session: Any = None) -> list[str]:
    """Return distinct work_item_ids that have persisted checkpoints."""
    sess = session or SessionLocal()
    created = session is None
    try:
        rows = sess.execute(text("SELECT DISTINCT work_item_id FROM worker_checkpoints")).fetchall()
        return [r[0] for r in rows]
    except Exception as exc:
        logger.exception("Failed to list active work items: %s", exc)
        return []
    finally:
        if created:
            with contextlib.suppress(Exception):
                sess.close()


def resume_from(checkpoint: WorkerCheckpoint) -> str | None:
    """Determine the next phase to run given a persisted checkpoint.

    Returns the phase name to resume FROM (we re-enter that phase), or None
    if the workflow is complete/concluded (already learned).
    """
    phase = str(checkpoint.phase) if checkpoint.phase is not None else ""
    if phase not in PHASE_ORDER:
        return None
    idx = PHASE_ORDER.index(phase)
    # If the last phase was completed, resume at the NEXT phase.
    if str(checkpoint.phase_completed) == "true":
        if idx >= len(PHASE_ORDER) - 1:
            return None  # already delivered+learned
        return PHASE_ORDER[idx + 1]
    # Not completed → re-run this phase.
    return phase


def checkpoint_data_dict(checkpoint: WorkerCheckpoint | None) -> dict[str, Any] | None:
    """Deserialize a checkpoint's JSON payload to a dict (or None)."""
    if checkpoint is None:
        return None
    raw = getattr(checkpoint, "checkpoint_data", None)
    if raw is None or str(raw) in ("", "null"):
        return None
    try:
        return json.loads(str(raw))
    except (json.JSONDecodeError, TypeError):
        return None
