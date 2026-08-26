"""Execution Queue API — CRUD + transitions for the canonical execution flow."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.execution_queue.models import (
    ExecState,
    ExecutionQueueStore,
    assert_transition,
    can_transition,
    is_terminal,
)

router = APIRouter(prefix="/api/execution-queue", tags=["execution-queue"])

_store = ExecutionQueueStore()


class QueueItemCreate(BaseModel):
    payload: dict | None = None


class TransitionRequest(BaseModel):
    target_state: str


class QueueItemResponse(BaseModel):
    item_id: str
    state: str
    payload: dict
    history: list[str]


@router.post("", response_model=QueueItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(data: QueueItemCreate) -> QueueItemResponse:
    import uuid

    item_id = f"exec-{uuid.uuid4().hex[:8]}"
    item = _store.add(item_id, data.payload)
    return QueueItemResponse(item_id=item_id, state=item["state"], payload=item["payload"], history=item["history"])


@router.get("/{item_id}", response_model=QueueItemResponse)
def get_item(item_id: str) -> QueueItemResponse:
    item = _store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return QueueItemResponse(item_id=item_id, state=item["state"], payload=item["payload"], history=item["history"])


@router.post("/{item_id}/transition", response_model=QueueItemResponse)
def transition_item(item_id: str, req: TransitionRequest) -> QueueItemResponse:
    item = _store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if is_terminal(item["state"]):
        raise HTTPException(status_code=400, detail=f"Item in terminal state: {item['state']}")
    try:
        assert_transition(item["state"], req.target_state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    updated = _store.transition(item_id, req.target_state)
    return QueueItemResponse(
        item_id=item_id, state=updated["state"], payload=updated["payload"], history=updated["history"]
    )


@router.get("", response_model=list[QueueItemResponse])
def list_items(state: str | None = None) -> list[QueueItemResponse]:
    items = _store.pending_by_state(state) if state else list(_store._items.keys())
    return [
        QueueItemResponse(item_id=k, state=v["state"], payload=v["payload"], history=v["history"])
        for k in items
        for v in [_store._items[k]]
    ]


@router.get("/pending/{state}")
def get_pending(state: str) -> list[str]:
    return _store.pending_by_state(state)


@router.get("/states/terminal")
def terminal_states() -> list[str]:
    return [s.value for s in ExecState if s in {ExecState.PAID, ExecState.REJECTED, ExecState.BLOCKED}]


@router.get("/states/transitions")
def valid_transitions(current: str) -> list[str]:
    try:
        return [s.value for s in ExecState if can_transition(current, s)]
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid state: {current}")
