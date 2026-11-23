"""Execution Queue API — CRUD + transitions for the canonical execution flow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from core.execution_queue.models import (
    ExecState,
    ExecutionQueueStore,
    assert_transition,
    can_transition,
    is_terminal,
)

router = APIRouter(prefix="/api/execution-queue", tags=["execution-queue"])


class QueueItemCreate(BaseModel):
    payload: dict | None = None


class TransitionRequest(BaseModel):
    target_state: str


# States that assert external progress or money movement. They may only be
# reached through the executor/approval/payment-evidence paths — never via
# this manual endpoint, which would let an operator (or a bug) fake them.
_EVIDENCE_GATED_STATES = {"executing", "submitted", "verification", "paid"}


class QueueItemResponse(BaseModel):
    item_id: str
    state: str
    payload: dict
    history: list[str]


@router.post("", response_model=QueueItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(data: QueueItemCreate) -> QueueItemResponse:
    import uuid

    item_id = f"exec-{uuid.uuid4().hex[:8]}"
    item = ExecutionQueueStore().add(item_id, data.payload)
    return QueueItemResponse(item_id=item_id, state=item["state"], payload=item["payload"], history=item["history"])


@router.get("/{item_id}", response_model=QueueItemResponse)
def get_item(item_id: str) -> QueueItemResponse:
    item = ExecutionQueueStore().get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return QueueItemResponse(item_id=item_id, state=item["state"], payload=item["payload"], history=item["history"])


# States that may never be reached via the manual transition endpoint,
# regardless of the transition matrix. These require the approved/publish path.
_EVIDENCE_GATED_STATES = {"executing", "submitted", "verification", "paid"}

# WAITING_HUMAN may only advance to SUBMITTED via the explicit /approve gate,
# never via the manual /transition endpoint. This prevents bypassing the human
# approval system and ensures approved_by comes from the authenticated session.
_WHITELIST_TRANSITIONS_FROM_WAITING_HUMAN = {"executing", "rejected", "blocked", "failed"}


@router.post("/{item_id}/transition", response_model=QueueItemResponse)
def transition_item(item_id: str, req: TransitionRequest) -> QueueItemResponse:
    store = ExecutionQueueStore()
    item = store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if is_terminal(item["state"]):
        raise HTTPException(status_code=400, detail=f"Item in terminal state: {item['state']}")
    # Block evidence-gated states entirely via manual transition.
    if req.target_state in _EVIDENCE_GATED_STATES:
        raise HTTPException(
            status_code=400,
            detail=(f"Manual transition to '{req.target_state}' is not allowed — use the executor, /approve, or payment-evidence paths"),
        )
    # Block WAITING_HUMAN → SUBMITTED via manual transition; that path is
    # exclusive to the /approve gate so approved_by can be captured from the
    # authenticated identity, not spoofed from the request body.
    if item.get("state") == "waiting_human" and req.target_state == "submitted":
        raise HTTPException(
            status_code=400,
            detail="Transition WAITING_HUMAN → SUBMITTED is not allowed via /transition — use POST /{item_id}/approve instead",
        )
    # Verify the transition is legal per the state machine, but also ensure
    # we aren't allowing an whitelisted exit from WAITING_HUMAN that shouldn't
    # exist (e.g. WAITING_HUMAN → executing is a no-op loop; only the approved
    # gate may reach submitted).
    if item.get("state") == "waiting_human" and req.target_state not in _WHITELIST_TRANSITIONS_FROM_WAITING_HUMAN:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from WAITING_HUMAN to {req.target_state}",
        )
    try:
        assert_transition(item["state"], req.target_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    updated = ExecutionQueueStore().transition(item_id, req.target_state)
    return QueueItemResponse(item_id=item_id, state=updated["state"], payload=updated["payload"], history=updated["history"])


@router.get("", response_model=list[QueueItemResponse])
def list_items(state: str | None = None) -> list[QueueItemResponse]:
    store = ExecutionQueueStore()
    items = store.pending_by_state(state) if state else list(store._items.keys())
    return [QueueItemResponse(item_id=k, state=v["state"], payload=v["payload"], history=v["history"]) for k in items for v in [store._items[k]]]


@router.post("/{item_id}/approve")
def approve_item(item_id: str, request: Request) -> dict:
    """Release the human-approval gate and execute a WAITING_HUMAN item.

    This is the ONLY path that lets a mutating executor action hit the
    external platform. Returns the executor result honestly —
    ``submitted`` only when the platform confirmed.

    The ``approved_by`` field is derived from the authenticated session,
    NOT from the request body, to prevent spoofing.
    """
    from api.middleware.auth_middleware import SESSION_COOKIE
    from core.execution_queue.driver import approve_and_execute
    from cores.auth.session_validator import get_session_validator

    # Extract token from Authorization header or session cookie
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        token = request.cookies.get(SESSION_COOKIE, "").strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required",
        )

    validator = get_session_validator()
    result = validator.validate(token)

    if not result.valid:
        raise HTTPException(
            status_code=401,
            detail=result.reason or "Invalid or expired token",
        )

    # approved_by comes from the authenticated identity, NOT from the request body
    approved_by = getattr(result, "user_id", None) or getattr(result, "device_id", "unknown")

    return approve_and_execute(item_id, approved_by=approved_by)


@router.get("/pending/{state}")
def get_pending(state: str) -> list[str]:
    store = ExecutionQueueStore()
    return store.pending_by_state(state)


@router.get("/states/terminal")
def terminal_states() -> list[str]:
    return [s.value for s in ExecState if s in {ExecState.PAID, ExecState.REJECTED, ExecState.BLOCKED}]


@router.get("/states/transitions")
def valid_transitions(current: str) -> list[str]:
    try:
        return [s.value for s in ExecState if can_transition(current, s)]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid state: {current}") from e
