"""OAR (AI Runtime) API router.

Exposes the OWNEX AI Runtime unified provider OS to Mission Control and the
rest of the system: smart routing, health, costs, cache, learning, and chat
completion through the best available provider with automatic failover.

The OAR is initialized lazily (first request) and never takes the server
down: any initialization or provider failure is surfaced as a clean 503/502
instead of an unhandled exception.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from cores.ai.runtime import OAR, get_oar
from cores.ai.runtime.interfaces import TaskType

logger = logging.getLogger("ownex.api.oar")

router = APIRouter(prefix="/oar", tags=["oar"])

# Process-wide singleton; initialized lazily on first use.
_oar: OAR | None = None
_initialized = False


async def _get_oar() -> OAR:
    """Get the initialized OAR singleton, initializing on first use."""
    global _oar, _initialized
    if _oar is None:
        _oar = get_oar()
    if not _initialized:
        try:
            await _oar.initialize()
            _initialized = True
        except Exception as exc:  # pragma: no cover - network dependent
            logger.error("[OAR] Initialization failed: %s", exc)
            raise HTTPException(status_code=503, detail=f"OAR initialization failed: {exc}") from exc
    return _oar


def _resolve_task_type(value: str) -> TaskType:
    """Resolve a task_type string into a TaskType enum, with a friendly error."""
    try:
        return TaskType(value)
    except ValueError as exc:
        valid = ", ".join(t.value for t in TaskType)
        raise HTTPException(
            status_code=422,
            detail=f"Invalid task_type '{value}'. Valid values: {valid}",
        ) from exc


class ChatRequest(BaseModel):
    """Chat completion request through the smart router."""

    prompt: str = Field(..., min_length=1, description="User prompt or message list JSON string")
    task_type: str = "chat"
    session_id: str | None = None
    model: str | None = None
    provider: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.3
    privacy_required: bool = False
    speed_critical: bool = False
    max_cost_usd: float | None = None


class RouteRequest(BaseModel):
    """Routing-only request: select the best provider without executing."""

    prompt: str = Field(..., min_length=1)
    task_type: str = "chat"
    max_tokens: int = 4096


@router.get("/status")
async def oar_status() -> dict[str, Any]:
    """OAR status: initialization state, providers, health, costs, cache, learning."""
    oar = _oar if _oar is not None else get_oar()
    if not oar._initialized:  # noqa: SLF001 - status must work before init
        return {
            "initialized": False,
            "message": "OAR not initialized yet — first /oar/chat or /oar/doctor will initialize it",
        }
    try:
        return oar.status()
    except Exception as exc:  # pragma: no cover
        logger.error("[OAR] status failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/doctor")
async def oar_doctor() -> dict[str, Any]:
    """Comprehensive OAR diagnostics (health, budget, cache, recommendations, circuits)."""
    oar = await _get_oar()
    try:
        return oar.doctor()
    except Exception as exc:  # pragma: no cover
        logger.error("[OAR] doctor failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/route")
async def oar_route(request: RouteRequest) -> dict[str, Any]:
    """Select the best provider/model for a task without executing it."""
    from cores.ai.runtime.interfaces import RoutingContext

    oar = await _get_oar()
    task_type = _resolve_task_type(request.task_type)
    try:
        context = RoutingContext(
            task_type=task_type,
            messages=[{"role": "user", "content": request.prompt}],
            max_tokens=request.max_tokens,
        )
        decision = await oar._router.route(context)  # noqa: SLF001 - exposed via router for diagnostics
        return {
            "provider_id": decision.provider_id,
            "model_id": decision.model_id,
            "confidence": decision.confidence,
            "estimated_cost_usd": decision.estimated_cost_usd,
            "estimated_latency_ms": decision.estimated_latency_ms,
            "reasoning": decision.reasoning,
            "fallback_chain": decision.fallback_chain,
            "capabilities_met": sorted(getattr(c, "value", c) for c in decision.capabilities_met),
            "capabilities_missing": sorted(getattr(c, "value", c) for c in decision.capabilities_missing),
            "privacy_ok": decision.privacy_ok,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.error("[OAR] route failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/chat")
async def oar_chat(request: ChatRequest) -> dict[str, Any]:
    """Send a chat completion through the smart router with automatic failover."""
    oar = await _get_oar()
    task_type = _resolve_task_type(request.task_type)
    try:
        response = await oar.chat(
            request.prompt,
            task_type=task_type,
            session_id=request.session_id,
            model=request.model,
            provider=request.provider,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            privacy_required=request.privacy_required,
            speed_critical=request.speed_critical,
            max_cost_usd=request.max_cost_usd,
        )
    except Exception as exc:  # pragma: no cover - provider dependent
        logger.error("[OAR] chat failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"All providers failed: {exc}") from exc

    if response.metadata.get("error"):
        raise HTTPException(status_code=502, detail=response.metadata["error"])

    return {
        "content": response.content,
        "provider_id": response.provider_id,
        "model_id": response.model_id,
        "task_type": response.task_type.value,
        "usage": response.usage,
        "cost_usd": response.cost_usd,
        "latency_ms": response.latency_ms,
        "finish_reason": response.finish_reason,
        "routing_decision": response.metadata.get("routing_decision"),
    }


@router.post("/ask")
async def oar_ask(request: ChatRequest) -> dict[str, Any]:
    """Quick ask: returns just the content string (plus routing metadata)."""
    response = await oar_chat(request)
    return {"content": response["content"], "routing_decision": response.get("routing_decision")}
