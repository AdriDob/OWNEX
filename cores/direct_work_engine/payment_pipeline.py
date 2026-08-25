"""Unified Payment Pipeline — Canonical state machine for OWNEX revenue flow.

Unifies:
- WorkBank states (preparing → ready_to_deliver/needs_access → delivered)
- ExecutionQueue states (DISCOVERED → ... → PAID)
- RevenueTracker states (PENDING/ACCEPTED/PAID/CANCELLED)

Into ONE canonical pipeline with 10 states:
DISCOVERED → QUALIFIED → READY → QUEUED → EXECUTING → WAITING_HUMAN
    → SUBMITTED → VERIFICATION → PAID
Terminal: REJECTED, BLOCKED, FAILED, DEAD_LETTER

This replaces the fragmented WorkBank + ExecutionQueue + RevenueTracker state machines.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from cores.direct_work_engine.workbank import WorkItem as WorkBankItem
from core.execution_queue.models import ExecState

logger = logging.getLogger("ownex.payment_pipeline")


class PaymentState(StrEnum):
    """Canonical payment pipeline states — Single Source of Truth."""

    # Discovery & Qualification
    DISCOVERED = "discovered"
    QUALIFIED = "qualified"

    # Ready & Queued
    READY = "ready"
    QUEUED = "queued"

    # Execution
    EXECUTING = "executing"
    WAITING_HUMAN = "waiting_human"

    # Submission & Verification
    SUBMITTED = "submitted"
    VERIFICATION = "verification"

    # Completion
    PAID = "paid"

    # Terminal Negative
    REJECTED = "rejected"
    BLOCKED = "blocked"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


# Legacy WorkBank statuses → PaymentState
_WORKBANK_TO_PAYMENT = {
    "preparing": "DISCOVERED",
    "ready_to_deliver": "READY",
    "needs_access": "WAITING_HUMAN",
    "delivered": "SUBMITTED",
}

# Legacy ExecutionQueue states → PaymentState (direct mapping for most)
_EXECUTION_TO_PAYMENT = {
    ExecState.DISCOVERED: "DISCOVERED",
    ExecState.QUALIFIED: "QUALIFIED",
    ExecState.READY: "READY",
    ExecState.QUEUED: "QUEUED",
    ExecState.EXECUTING: "EXECUTING",
    ExecState.WAITING_HUMAN: "WAITING_HUMAN",
    ExecState.SUBMITTED: "SUBMITTED",
    ExecState.VERIFICATION: "VERIFICATION",
    ExecState.PAID: "PAID",
    ExecState.REJECTED: "REJECTED",
    ExecState.BLOCKED: "BLOCKED",
    ExecState.FAILED: "FAILED",
    ExecState.DEAD_LETTER: "DEAD_LETTER",
}

# RevenueTracker statuses → PaymentState
_REVENUE_TO_PAYMENT = {
    "pending": "SUBMITTED",
    "reviewing": "VERIFICATION",
    "accepted": "VERIFICATION",
    "paid": "PAID",
    "cancelled": "REJECTED",
    "failed": "FAILED",
}


# Valid transitions for the canonical pipeline
_TRANSITIONS: dict[str, set[str]] = {
    "DISCOVERED": {"QUALIFIED", "REJECTED"},
    "QUALIFIED": {"READY", "REJECTED"},
    "READY": {"QUEUED"},
    "QUEUED": {"EXECUTING"},
    "EXECUTING": {"WAITING_HUMAN", "SUBMITTED", "FAILED"},
    "WAITING_HUMAN": {"EXECUTING", "SUBMITTED", "REJECTED", "BLOCKED"},
    "SUBMITTED": {"VERIFICATION", "REJECTED"},
    "VERIFICATION": {"PAID", "FAILED"},
    "PAID": set(),
    "REJECTED": set(),
    "BLOCKED": set(),
    "FAILED": {"QUEUED", "DEAD_LETTER"},
    "DEAD_LETTER": set(),
}

_TERMINAL_POSITIVE = {"PAID"}
_TERMINAL_NEGATIVE = {"REJECTED", "BLOCKED", "FAILED", "DEAD_LETTER"}
_TERMINAL = _TERMINAL_POSITIVE | _TERMINAL_NEGATIVE


# Legacy WorkBank statuses → PaymentState
_WORKBANK_TO_PAYMENT = {
    "preparing": "DISCOVERED",
    "ready_to_deliver": "READY",
    "needs_access": "WAITING_HUMAN",
    "delivered": "SUBMITTED",
}

# Legacy ExecutionQueue states → PaymentState (direct mapping for most)
_EXECUTION_TO_PAYMENT = {
    ExecState.DISCOVERED: "DISCOVERED",
    ExecState.QUALIFIED: "QUALIFIED",
    ExecState.READY: "READY",
    ExecState.QUEUED: "QUEUED",
    ExecState.EXECUTING: "EXECUTING",
    ExecState.WAITING_HUMAN: "WAITING_HUMAN",
    ExecState.SUBMITTED: "SUBMITTED",
    ExecState.VERIFICATION: "VERIFICATION",
    ExecState.PAID: "PAID",
    ExecState.REJECTED: "REJECTED",
    ExecState.BLOCKED: "BLOCKED",
    ExecState.FAILED: "FAILED",
    ExecState.DEAD_LETTER: "DEAD_LETTER",
}

# RevenueTracker statuses → PaymentState
_REVENUE_TO_PAYMENT = {
    "pending": "SUBMITTED",
    "reviewing": "VERIFICATION",
    "accepted": "VERIFICATION",
    "paid": "PAID",
    "cancelled": "REJECTED",
    "failed": "FAILED",
}


def can_transition(current: str, target: str) -> bool:
    """Check if transition is valid in canonical pipeline."""
    return target in _TRANSITIONS.get(current, set())


def assert_transition(current: str, target: str) -> None:
    """Raise if transition is invalid."""
    if not can_transition(current, target):
        raise ValueError(f"transición inválida: {current} → {target}")


def is_terminal(state: str) -> bool:
    return state in _TERMINAL


def is_terminal_positive(state: str) -> bool:
    return state in {"PAID"}


def is_terminal_negative(state: str) -> bool:
    return state in {"REJECTED", "BLOCKED", "FAILED", "DEAD_LETTER"}


def workbank_status_to_payment(status: str) -> str:
    """Convert legacy WorkBank status to canonical PaymentState."""
    return _WORKBANK_TO_PAYMENT.get(status, "DISCOVERED")


def execution_state_to_payment(state: str) -> str:
    """Convert legacy ExecState to canonical PaymentState."""
    try:
        return _EXECUTION_TO_PAYMENT[ExecState(state)]
    except (KeyError, ValueError):
        return "DISCOVERED"


def revenue_status_to_payment(status: str) -> str:
    """Convert RevenueTracker status to canonical PaymentState."""
    return _REVENUE_TO_PAYMENT.get(status.lower(), "SUBMITTED")


# Valid transitions for the canonical pipeline
_TRANSITIONS: dict[str, set[str]] = {
    "DISCOVERED": {"QUALIFIED", "REJECTED"},
    "QUALIFIED": {"READY", "REJECTED"},
    "READY": {"QUEUED"},
    "QUEUED": {"EXECUTING"},
    "EXECUTING": {"WAITING_HUMAN", "SUBMITTED", "FAILED"},
    "WAITING_HUMAN": {"EXECUTING", "SUBMITTED", "REJECTED", "BLOCKED"},
    "SUBMITTED": {"VERIFICATION", "REJECTED"},
    "VERIFICATION": {"PAID", "FAILED"},
    "PAID": set(),
    "REJECTED": set(),
    "BLOCKED": set(),
    "FAILED": {"QUEUED", "DEAD_LETTER"},
    "DEAD_LETTER": set(),
}

_TERMINAL_POSITIVE = {"PAID"}
_TERMINAL_NEGATIVE = {"REJECTED", "BLOCKED", "FAILED", "DEAD_LETTER"}
_TERMINAL = _TERMINAL_POSITIVE | _TERMINAL_NEGATIVE


# Legacy WorkBank statuses → PaymentState
_WORKBANK_TO_PAYMENT = {
    "preparing": "DISCOVERED",
    "ready_to_deliver": "READY",
    "needs_access": "WAITING_HUMAN",
    "delivered": "SUBMITTED",
}

# Legacy ExecutionQueue states → PaymentState (direct mapping for most)
_EXECUTION_TO_PAYMENT = {
    ExecState.DISCOVERED: "DISCOVERED",
    ExecState.QUALIFIED: "QUALIFIED",
    ExecState.READY: "READY",
    ExecState.QUEUED: "QUEUED",
    ExecState.EXECUTING: "EXECUTING",
    ExecState.WAITING_HUMAN: "WAITING_HUMAN",
    ExecState.SUBMITTED: "SUBMITTED",
    ExecState.VERIFICATION: "VERIFICATION",
    ExecState.PAID: "PAID",
    ExecState.REJECTED: "REJECTED",
    ExecState.BLOCKED: "BLOCKED",
    ExecState.FAILED: "FAILED",
    ExecState.DEAD_LETTER: "DEAD_LETTER",
}

# RevenueTracker statuses → PaymentState
_REVENUE_TO_PAYMENT = {
    "pending": "SUBMITTED",
    "reviewing": "VERIFICATION",
    "accepted": "VERIFICATION",
    "paid": "PAID",
    "cancelled": "REJECTED",
    "failed": "FAILED",
}


def can_transition(current: str, target: str) -> bool:
    """Check if transition is valid in canonical pipeline."""
    return target in _TRANSITIONS.get(current, set())


def assert_transition(current: str, target: str) -> None:
    """Raise if transition is invalid."""
    if not can_transition(current, target):
        raise ValueError(f"transición inválida: {current} → {target}")


def is_terminal(state: str) -> bool:
    return state in _TERMINAL


def is_terminal_positive(state: str) -> bool:
    return state in {"PAID"}


def is_terminal_negative(state: str) -> bool:
    return state in {"REJECTED", "BLOCKED", "FAILED", "DEAD_LETTER"}


def workbank_status_to_payment(status: str) -> str:
    """Convert legacy WorkBank status to canonical PaymentState."""
    return _WORKBANK_TO_PAYMENT.get(status, "DISCOVERED")


def execution_state_to_payment(state: str) -> str:
    """Convert legacy ExecState to canonical PaymentState."""
    try:
        return _EXECUTION_TO_PAYMENT[ExecState(state)]
    except (KeyError, ValueError):
        return "DISCOVERED"


def revenue_status_to_payment(status: str) -> str:
    """Convert RevenueTracker status to canonical PaymentState."""
    return _REVENUE_TO_PAYMENT.get(status.lower(), "SUBMITTED")


# Valid transitions for the canonical pipeline
_TRANSITIONS: dict[str, set[str]] = {
    "DISCOVERED": {"QUALIFIED", "REJECTED"},
    "QUALIFIED": {"READY", "REJECTED"},
    "READY": {"QUEUED"},
    "QUEUED": {"EXECUTING"},
    "EXECUTING": {"WAITING_HUMAN", "SUBMITTED", "FAILED"},
    "WAITING_HUMAN": {"EXECUTING", "SUBMITTED", "REJECTED", "BLOCKED"},
    "SUBMITTED": {"VERIFICATION", "REJECTED"},
    "VERIFICATION": {"PAID", "FAILED"},
    "PAID": set(),
    "REJECTED": set(),
    "BLOCKED": set(),
    "FAILED": {"QUEUED", "DEAD_LETTER"},
    "DEAD_LETTER": set(),
}

_TERMINAL_POSITIVE = {"PAID"}
_TERMINAL_NEGATIVE = {"REJECTED", "BLOCKED", "FAILED", "DEAD_LETTER"}
_TERMINAL = _TERMINAL_POSITIVE | _TERMINAL_NEGATIVE


@dataclass(slots=True)
class PipelineItem:
    """Unified pipeline item combining WorkBank + ExecutionQueue + Revenue."""

    item_id: str
    state: str
    source: str  # "workbank" | "execution" | "revenue"
    payload: dict
    history: list[str]
    created_at: str
    updated_at: str
    metadata: dict | None = None

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "state": self.state,
            "source": self.source,
            "payload": self.payload,
            "history": self.history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata or {},
        }


def _default_store_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[1] / "data"
    return root / "payment_pipeline.json"


class PaymentPipelineStore:
    """Unified store for the canonical payment pipeline."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        self._path = Path(store_path or _default_store_path())
        self._items: dict[str, PipelineItem] = {}
        self._load()

    def _load(self) -> None:
        try:
            if self._path.exists():
                data = json.loads(self._path.read_text())
                self._items = {k: PipelineItem(**v) if isinstance(v, dict) else v for k, v in data.items()}
        except Exception:
            self._items = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({k: v.to_dict() for k, v in self._items.items()}, indent=2))

    def add(
        self, item_id: str, source: str, payload: dict | None = None, initial_state: str = "DISCOVERED"
    ) -> PipelineItem:
        now = datetime.now(UTC).isoformat()
        item = PipelineItem(
            item_id=item_id,
            state=initial_state,
            source=source,
            payload=payload or {},
            history=[initial_state],
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            metadata={},
        )
        self._items[item_id] = item
        self._save()
        return item

    def get(self, item_id: str) -> PipelineItem | None:
        return self._items.get(item_id)

    def transition(self, item_id: str, target_state: str) -> PipelineItem:
        item = self._items[item_id]
        if not can_transition(item.state, target_state):
            raise ValueError(f"transición inválida: {item.state} → {target_state}")
        item.state = target_state
        item.history.append(target_state)
        item.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return item

    def get_by_state(self, *states: str) -> list[PipelineItem]:
        return [item for item in self._items.values() if item.state in states]

    def get_by_source(self, source: str) -> list[PipelineItem]:
        return [item for item in self._items.values() if item.source == source]

    def get_all(self) -> list[PipelineItem]:
        return list(self._items.values())


def _default_store_path() -> Path:
    base = os.environ.get("OWNEX_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[1] / "data"
    return root / "payment_pipeline.json"


def sync_workbank_to_pipeline() -> dict:
    """Sync WorkBank items to canonical pipeline."""
    from cores.direct_work_engine.workbank import get_workbank

    store = PaymentPipelineStore()
    wb = get_workbank()
    synced = 0
    errors = 0

    for item in wb._items.values():
        try:
            state = workbank_status_to_payment(item.status)
            existing = store.get(item.id)
            if existing:
                if existing.state != state:
                    existing.state = state
                    existing.history.append(state)
                    existing.updated_at = datetime.now(UTC).isoformat()
            else:
                store.add(
                    item_id=item.id,
                    source="workbank",
                    payload=item.to_dict(),
                    initial_state=state,
                )
            synced += 1
        except Exception as e:
            logger.error("Failed to sync workbank item %s: %s", item.id, e)
            errors += 1

    return {"synced": synced, "errors": errors}


def sync_execution_to_pipeline() -> dict:
    """Sync ExecutionQueue items to canonical pipeline."""
    from core.execution_queue.models import ExecutionQueueStore

    store = PaymentPipelineStore()
    eq_store = ExecutionQueueStore()
    synced = 0
    errors = 0

    for item_id, item in eq_store._items.items():
        try:
            state = execution_state_to_payment(item["state"])
            existing = store.get(item_id)
            if existing:
                if existing.state != state:
                    existing.state = state
                    existing.history.append(state)
                    existing.updated_at = datetime.now(UTC).isoformat()
            else:
                store.add(
                    item_id=item_id,
                    source="execution",
                    payload=item.get("payload", {}),
                    initial_state=state,
                )
            synced += 1
        except Exception as e:
            logger.error("Failed to sync execution item %s: %s", item_id, e)
            errors += 1

    return {"synced": synced, "errors": errors}


def sync_revenue_to_pipeline() -> dict:
    """Sync RevenueTracker items to canonical pipeline."""
    try:
        from cores.revenue_tracker.revenue_tracker import get_revenue_tracker

        tracker = get_revenue_tracker()
        if tracker is None:
            return {"synced": 0, "errors": 0, "message": "RevenueTracker not available"}
    except Exception:
        return {"synced": 0, "errors": 1, "message": "RevenueTracker import failed"}

    store = PaymentPipelineStore()
    synced = 0
    errors = 0

    try:
        opportunities = tracker.get_all_opportunities() if hasattr(tracker, "get_all_opportunities") else []
        for opp in opportunities:
            try:
                status = getattr(opp, "status", "pending")
                state = revenue_status_to_payment(status)
                item_id = getattr(opp, "id", f"revenue_{id(opp)}")
                existing = store.get(item_id)
                if existing:
                    if existing.state != state:
                        existing.state = state
                        existing.history.append(state)
                        existing.updated_at = datetime.now(UTC).isoformat()
                else:
                    store.add(
                        item_id=item_id,
                        source="revenue",
                        payload={"opportunity_id": item_id, "status": status},
                        initial_state=state,
                    )
                synced += 1
            except Exception as e:
                logger.error("Failed to sync revenue item %s: %s", item_id, e)
                errors += 1
    except Exception as e:
        logger.error("Failed to sync revenue tracker: %s", e)
        errors += 1

    return {"synced": synced, "errors": errors}


def full_pipeline_sync() -> dict:
    """Run all sync jobs."""
    results = {}
    results["workbank"] = sync_workbank_to_pipeline()
    results["execution"] = sync_execution_to_pipeline()
    results["revenue"] = sync_revenue_to_pipeline()
    return results


def get_pipeline_analytics() -> dict:
    """Get analytics for the unified pipeline."""
    store = PaymentPipelineStore()
    items = store.get_all()

    by_state = {}
    by_source = {}
    for item in items:
        by_state[item.state] = by_state.get(item.state, 0) + 1
        by_source[item.source] = by_source.get(item.source, 0) + 1

    terminal_positive = sum(1 for i in items if i.state == "PAID")
    terminal_negative = sum(1 for i in items if i.state in {"REJECTED", "BLOCKED", "FAILED", "DEAD_LETTER"})
    in_progress = len(items) - terminal_positive - terminal_negative

    return {
        "total": len(items),
        "by_state": by_state,
        "by_source": by_source,
        "terminal_positive": terminal_positive,
        "terminal_negative": terminal_negative,
        "in_progress": in_progress,
        "conversion_rate": terminal_positive / max(1, terminal_positive + terminal_negative),
    }


def pipeline_sync_job() -> dict:
    """Scheduler job: run full pipeline sync."""
    return full_pipeline_sync()


def pipeline_analytics_job() -> dict:
    """Scheduler job: compute pipeline analytics."""
    return get_pipeline_analytics()


def full_pipeline_sync() -> dict:
    """Run all sync jobs."""
    results = {}
    results["workbank"] = sync_workbank_to_pipeline()
    results["execution"] = sync_execution_to_pipeline()
    results["revenue"] = sync_revenue_to_pipeline()
    return results


# ──────────────────────────────────────────────────────────────────────
# Imports
# ──────────────────────────────────────────────────────────────────────

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.payment_pipeline")

from cores.direct_work_engine.workbank import WorkItem as WorkBankItem
from core.execution_queue.models import ExecState

# Legacy WorkBank statuses → PaymentState
_WORKBANK_TO_PAYMENT = {
    "preparing": "DISCOVERED",
    "ready_to_deliver": "READY",
    "needs_access": "WAITING_HUMAN",
    "delivered": "SUBMITTED",
}

# Legacy ExecutionQueue states → PaymentState (direct mapping for most)
_EXECUTION_TO_PAYMENT = {
    ExecState.DISCOVERED: "DISCOVERED",
    ExecState.QUALIFIED: "QUALIFIED",
    ExecState.READY: "READY",
    ExecState.QUEUED: "QUEUED",
    ExecState.EXECUTING: "EXECUTING",
    ExecState.WAITING_HUMAN: "WAITING_HUMAN",
    ExecState.SUBMITTED: "SUBMITTED",
    ExecState.VERIFICATION: "VERIFICATION",
    ExecState.PAID: "PAID",
    ExecState.REJECTED: "REJECTED",
    ExecState.BLOCKED: "BLOCKED",
    ExecState.FAILED: "FAILED",
    ExecState.DEAD_LETTER: "DEAD_LETTER",
}

# RevenueTracker statuses → PaymentState
_REVENUE_TO_PAYMENT = {
    "pending": "SUBMITTED",
    "reviewing": "VERIFICATION",
    "accepted": "VERIFICATION",
    "paid": "PAID",
    "cancelled": "REJECTED",
    "failed": "FAILED",
}
