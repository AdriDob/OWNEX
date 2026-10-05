"""Internal Dev Agent API — the repo's own task queue.

Flow: POST /dev-queue (human adds task) → daily propose job (agent,
read-only) → POST /dev-queue/{id}/approve with an approval_token from
POST /api/copilot/approve (human click) → agent builds + verifies → record.
The agent never commits, pushes, or leaves the task scope.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/internal-dev", tags=["internal-dev"])


def _queue():  # type: ignore[no-untyped-def]
    from cores.autonomy.internal_dev import DevQueue

    return DevQueue()  # data-dir aware per request (OWNEX_DATA_DIR), test-safe


class DevTaskIn(BaseModel):
    kind: str = "implement"
    description: str = Field(min_length=1, max_length=2000)
    scope_paths: list[str] = Field(default_factory=list)
    test_command: str = ""


class ApproveIn(BaseModel):
    approval_token: str = Field(min_length=1)


@router.post("/dev-queue", status_code=201)
async def dev_queue_add(payload: DevTaskIn) -> dict[str, Any]:
    """Queue an internal dev task (human)."""
    try:
        task = _queue().add(
            kind=payload.kind,
            description=payload.description,
            scope_paths=payload.scope_paths,
            test_command=payload.test_command,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    return task.to_dict()


@router.get("/dev-queue")
async def dev_queue_list(status: str | None = None) -> dict[str, Any]:
    """List queued/proposed/done tasks."""
    queue = _queue()
    tasks = queue.list(status=status) if status else queue.list()
    return {"total": len(tasks), "tasks": [t.to_dict() for t in tasks]}


@router.post("/dev-queue/propose")
async def dev_queue_propose() -> dict[str, Any]:
    """Manual trigger of the propose cycle (same as the daily job)."""
    from cores.autonomy.internal_dev import run_internal_dev_propose

    return await run_internal_dev_propose(_queue())


@router.post("/dev-queue/{task_id}/approve")
async def dev_queue_approve(task_id: str, payload: ApproveIn) -> dict[str, Any]:
    """Human-approved build: token → bridge writes → verify → record."""
    from cores.autonomy.internal_dev import approve_and_build

    out = await approve_and_build(task_id, payload.approval_token, queue=_queue())
    if not out.get("ok"):
        raise HTTPException(status_code=422, detail=str(out.get("error", "build fallido")))
    return out
