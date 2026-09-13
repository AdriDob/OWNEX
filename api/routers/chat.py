"""Unified chat API — single entry point for all assistant personas.

Thin dispatcher over the canonical persona routers (merlin / copilot /
assistant). No engine logic lives here: every persona delegates to its own
handler, so contracts (semantics blocks, approval gates, runs) are preserved
by construction. Legacy per-persona routes stay mounted (backward compat).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.routers import assistant as assistant_router
from api.routers import copilot as copilot_router
from api.routers import merlin as merlin_router

logger = logging.getLogger("ownex.api.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])

PERSONAS: tuple[str, ...] = ("merlin", "copilot", "assistant")
DEFAULT_PERSONA = "copilot"


class ChatMessage(BaseModel):
    role: str
    content: str


class UnifiedChatRequest(BaseModel):
    persona: str = DEFAULT_PERSONA
    message: str
    history: list[ChatMessage] = []
    task_type: str = "chat"
    context: dict[str, Any] = Field(default_factory=dict)


def _validate_persona(persona: str) -> str:
    p = (persona or "").strip().lower()
    if p not in PERSONAS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown persona '{persona}'. Valid: {', '.join(PERSONAS)}",
        )
    return p


def _history_for(module: Any, history: list[ChatMessage]) -> list[Any]:
    return [module.ChatMessage(role=m.role, content=m.content) for m in history]


async def _dispatch_merlin(message: str, context: dict[str, Any]) -> dict[str, Any]:
    req = merlin_router.ChatRequest(message=message, context=context or {})
    resp = await merlin_router.chat(req)
    return {
        "persona": "merlin",
        "status": "ok" if resp.is_success else "error",
        "response": resp.response,
        "semantics": resp.semantics,
        "tool_calls": [t.model_dump() for t in (resp.tool_calls or [])],
    }


async def _dispatch_copilot(message: str, history: list[ChatMessage], task_type: str) -> dict[str, Any]:
    req = copilot_router.ChatRequest(
        message=message,
        history=_history_for(copilot_router, history),
        task_type=task_type or "chat",
    )
    result = await copilot_router.copilot_chat(req)
    return {"persona": "copilot", **result}


async def _dispatch_assistant(message: str, history: list[ChatMessage]) -> dict[str, Any]:
    req = assistant_router.ChatRequest(message=message, history=_history_for(assistant_router, history))
    # Sync handler: run in a threadpool, same as FastAPI does for `def` endpoints.
    result = await run_in_threadpool(assistant_router.chat, req)
    if isinstance(result, dict):
        out: dict[str, Any] = {"persona": "assistant", "status": "ok", **result}
        out["response"] = result.get("answer") or result.get("response") or ""
        return out
    return {"persona": "assistant", "status": "ok", "response": str(result)}


@router.post("")
async def unified_chat(body: UnifiedChatRequest) -> dict[str, Any]:
    """Chat with any persona through one endpoint. Fail-closed on bad input."""
    persona = _validate_persona(body.persona)
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    try:
        if persona == "merlin":
            return await _dispatch_merlin(body.message, body.context)
        if persona == "copilot":
            return await _dispatch_copilot(body.message, body.history, body.task_type)
        return await _dispatch_assistant(body.message, body.history)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("[CHAT] Unified chat error (persona=%s): %s", persona, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/stream")
async def unified_chat_stream(body: UnifiedChatRequest):
    """SSE stream. Merlin (non-streaming engine) is wrapped as a single event."""
    from fastapi.responses import StreamingResponse

    persona = _validate_persona(body.persona)
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if persona == "merlin":
        result = await _dispatch_merlin(body.message, body.context)

        async def _single_event():
            import json

            yield f"data: {json.dumps(result['response'])}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(_single_event(), media_type="text/event-stream")
    if persona == "copilot":
        req = copilot_router.ChatRequest(
            message=body.message,
            history=_history_for(copilot_router, body.history),
            task_type=body.task_type or "chat",
        )
        return await copilot_router.copilot_chat_stream(req)
    req = assistant_router.ChatRequest(message=body.message, history=_history_for(assistant_router, body.history))
    return await assistant_router.chat_stream(req)


@router.post("/execute")
async def chat_execute(body: copilot_router.ExecuteRequest) -> dict[str, Any]:
    """Two-phase execution (propose → approve → execute). Same gate as copilot."""
    return await copilot_router.copilot_execute(body)


@router.post("/approve")
async def chat_approve(body: copilot_router.ApproveRequest) -> dict[str, Any]:
    """Issue a one-time human approval token. This click IS the confirmation."""
    return await copilot_router.copilot_approve(body)


@router.get("/runs")
async def chat_runs(limit: int = 20) -> dict[str, Any]:
    """List recent opencode runs (prompt/output/diff files)."""
    return await copilot_router.copilot_runs(limit=limit)
