"""Sync API Router — Cross-device state synchronization for OWNEX."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field
from typing import Any
import uuid
import logging

from core.sync.engine import (
    SyncEngine,
    SyncEvent,
    SyncEventType,
    DeviceIdentity,
    get_sync_engine,
)
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends

router = APIRouter(prefix="/api/sync", tags=["sync"])

logger = logging.getLogger("ownex.sync")


class DeviceRegisterRequest(BaseModel):
    device_type: str = Field(..., description="Device type: desktop, mobile, watch")
    name: str = Field(..., description="Human-readable device name")
    public_key: str | None = Field(None, description="Public key for encryption")
    capabilities: list[str] = Field(default_factory=list, description="Device capabilities")


class SyncEventRequest(BaseModel):
    event_type: str = Field(..., description="Event type")
    payload: dict[str, Any] = Field(default_factory=dict)
    device_id: str | None = Field(None, description="Source device ID")


class SyncStatusResponse(BaseModel):
    device_id: str
    connected: bool
    connected_devices: list[str]
    offline_queue_size: int
    vector_clock: dict[str, int]


def get_sync_engine_dependency() -> Any:
    return get_sync_engine()


from dataclasses import asdict


@router.post("/device/register", response_model=dict)
async def register_device(
    request: DeviceRegisterRequest,
    engine=Depends(get_sync_engine_dependency),
) -> dict:
    """Register a new device for synchronization."""
    device = engine.register_device(
        device_type=request.device_type,
        name=request.name,
        public_key=request.public_key,
        capabilities=request.capabilities,
    )
    return {"device": asdict(device)}


@router.get("/device/identity")
async def get_device_identity(engine=Depends(get_sync_engine_dependency)):
    """Get current device identity."""
    identity = engine.get_device_identity()
    if not identity:
        raise HTTPException(status_code=404, detail="Device not registered")
    return asdict(identity)


@router.get("/devices")
async def list_devices(engine=Depends(get_sync_engine_dependency)):
    """List all registered devices."""
    devices = engine.get_all_devices()
    return {"devices": [asdict(d) for d in devices]}


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(engine=Depends(get_sync_engine_dependency)):
    """Get current sync status."""
    return engine.get_sync_status()


@router.post("/events")
async def create_event(request: SyncEventRequest, engine=Depends(get_sync_engine_dependency)):
    """Create and broadcast a sync event."""
    event = engine.create_event(request.event_type, request.payload, request.device_id)
    engine.publish_event(event)
    return {"event_id": event.event_id, "status": "published"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time sync."""
    await websocket.accept()
    device_id = f"ws_{uuid.uuid4().hex[:8]}"

    from core.sync.engine import get_sync_engine

    engine = get_sync_engine()
    engine.register_ws_connection(f"ws_{uuid.uuid4().hex[:8]}", None)

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "sync_event":
                event = SyncEvent(
                    event_id=f"evt_{uuid.uuid4().hex[:12]}",
                    device_id=data.get("device_id", "unknown"),
                    event_type=SyncEventType(data["event_type"]),
                    payload=data.get("payload", {}),
                )
                engine = get_sync_engine()
                engine.publish_event(event)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[SYNC] WebSocket error: {e}")
    finally:
        pass
