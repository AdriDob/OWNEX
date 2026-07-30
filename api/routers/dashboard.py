"""Dashboard API — health, models, keys, logs, sessions for unified UI."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from cores.ai.provider import get_provider, get_registry

logger = logging.getLogger("ownex.api.dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# WebSocket connection manager for live logs
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            with contextlib.suppress(Exception):
                await connection.send_text(message)


manager = ConnectionManager()


# Pydantic models
class HealthStatus(BaseModel):
    provider: str
    status: str  # healthy, degraded, down
    latency_ms: float | None = None
    models_count: int = 0
    error: str | None = None
    last_check: str


class DashboardStatus(BaseModel):
    timestamp: str
    providers: list[HealthStatus]
    active_provider: str
    total_models: int
    fallback_chain: list[str]


class ModelInfo(BaseModel):
    id: str
    label: str
    provider: str
    available: bool
    capabilities: list[str] = []


class ApiKeyInfo(BaseModel):
    id: str
    provider: str
    name: str
    masked_key: str
    quota_used: int = 0
    quota_limit: int = 0
    active: bool = True


class SessionInfo(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    created_at: str
    updated_at: str
    message_count: int


# Health check for each provider
async def check_provider_health(provider_id: str, provider: any) -> HealthStatus:
    start = asyncio.get_event_loop().time()
    try:
        if hasattr(provider, "is_available"):
            available = await asyncio.wait_for(asyncio.to_thread(provider.is_available), timeout=5.0)
        else:
            available = True
        latency = (asyncio.get_event_loop().time() - start) * 1000

        models = 0
        if hasattr(provider, "get_models"):
            models = len(await asyncio.to_thread(provider.get_models))
        elif hasattr(provider, "list_models"):
            models = len(await asyncio.to_thread(provider.list_models))

        return HealthStatus(
            provider=provider_id,
            status="healthy" if available else "degraded",
            latency_ms=round(latency, 2),
            models_count=models,
            last_check=datetime.utcnow().isoformat() + "Z",
        )
    except TimeoutError:
        return HealthStatus(
            provider=provider_id,
            status="degraded",
            latency_ms=5000,
            error="timeout",
            last_check=datetime.utcnow().isoformat() + "Z",
        )
    except Exception as e:
        return HealthStatus(
            provider=provider_id, status="down", error=str(e), last_check=datetime.utcnow().isoformat() + "Z"
        )


@router.get("/status", response_model=DashboardStatus)
async def get_dashboard_status():
    """Unified health status for all providers in the fallback chain."""
    registry = get_registry()
    providers = registry.list_providers()

    health_checks = []
    for p in providers:
        provider = get_provider(p["id"])
        health = await check_provider_health(p["id"], provider)
        health_checks.append(health)

    active = get_provider().name if get_provider() else "none"
    total_models = sum(h.models_count for h in health_checks)
    fallback_chain = [p["id"] for p in providers]

    return DashboardStatus(
        timestamp=datetime.utcnow().isoformat() + "Z",
        providers=health_checks,
        active_provider=active,
        total_models=total_models,
        fallback_chain=fallback_chain,
    )


@router.get("/models")
async def list_models():
    """List all available models across all providers."""
    registry = get_registry()
    providers = registry.list_providers()

    models = []
    for p in providers:
        provider = get_provider(p["id"])
        if hasattr(provider, "get_models"):
            try:
                provider_models = await asyncio.to_thread(provider.get_models)
                for m in provider_models:
                    models.append(
                        ModelInfo(
                            id=m.get("id", ""),
                            label=m.get("label", m.get("id", "")),
                            provider=p["id"],
                            available=True,
                            capabilities=m.get("capabilities", []),
                        )
                    )
            except Exception:
                pass
    return models


@router.get("/keys", response_model=list[dict])
async def list_keys():
    """List API keys with quota info."""
    # TODO: Implement key management from config/secrets
    return []


@router.get("/sessions", response_model=list[dict])
async def list_sessions():
    """List active sessions."""
    # TODO: Implement session persistence
    return []


# WebSocket for live logs
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            with contextlib.suppress(Exception):
                await connection.send_text(message)


log_manager = ConnectionManager()


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for live log streaming."""
    await log_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back for keepalive
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        log_manager.disconnect(websocket)


# Background task to push logs via WebSocket
async def push_logs():
    """Background task to tail logs and push to WebSocket clients."""
    # Tail docker logs for omniroute and fcc
    proc = await asyncio.create_subprocess_exec(
        "docker", "logs", "-f", "omniroute", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    async for line in proc.stdout:
        await log_manager.broadcast(line.decode().strip())

    proc2 = await asyncio.create_subprocess_exec(
        "journalctl", "-f", "-u", "fcc-proxy", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    async for line in proc2.stdout:
        await log_manager.broadcast(f"[FCC] {line.decode().strip()}")


# Start background log pusher on module load
# asyncio.create_task(push_logs())
