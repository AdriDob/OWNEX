"""Device Identity API Router."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from cores.device_identity import (
    DeviceIdentityService,
    DeviceRegistration,
    get_device_identity_service,
)

router = APIRouter(prefix="/api/device", tags=["device"])


class DeviceRegisterRequest(BaseModel):
    device_id: str | None = None
    platform: str = Field(..., description="desktop|mobile|watch|web")
    name: str = Field(..., min_length=1, max_length=100)
    push_token: str | None = None
    capabilities: list[str] = []
    metadata: dict = {}


class DeviceRegisterResponse(BaseModel):
    device_id: str
    registered: bool
    message: str


class DeviceResponse(BaseModel):
    device_id: str
    platform: str
    name: str
    push_token: str | None = None
    capabilities: list[str] = []
    last_seen: str
    registered_at: str
    metadata: dict = {}


class DeviceListResponse(BaseModel):
    devices: list[dict]
    total: int


@router.post("/register", response_model=DeviceRegisterResponse)
async def register_device(payload: DeviceRegisterRequest = Body(...)) -> DeviceRegisterResponse:
    """Register a new device or update existing one."""
    service: DeviceIdentityService = get_device_identity_service()

    registration = DeviceRegistration(
        device_id=payload.device_id,
        platform=payload.platform,
        name=payload.name,
        push_token=payload.push_token,
        capabilities=payload.capabilities,
        metadata=payload.metadata,
    )

    try:
        device = service.register(registration)
        return DeviceRegisterResponse(
            device_id=device["device_id"],
            registered=True,
            message=f"Device registered: {device['device_id']}",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {e}") from e


@router.get("/{device_id}", response_model=dict)
async def get_device(device_id: str) -> dict:
    """Get device by ID."""
    service: DeviceIdentityService = get_device_identity_service()
    device = service.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/", response_model=DeviceListResponse)
async def list_devices(platform: str | None = None) -> DeviceListResponse:
    """List all registered devices, optionally filtered by platform."""
    service = get_device_identity_service()

    devices = [d for d in service.get_all() if d.get("platform") == platform] if platform else service.get_all()
    return DeviceListResponse(devices=devices, total=len(devices))


@router.delete("/{device_id}")
async def delete_device(device_id: str) -> dict:
    """Delete a device."""
    service = get_device_identity_service()
    if service.delete(device_id):
        return {"success": True, "message": f"Device {device_id} deleted"}
    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_id}/heartbeat")
async def device_heartbeat(device_id: str) -> dict:
    """Update device last_seen timestamp."""
    service = get_device_identity_service()
    if service.update_last_seen(device_id):
        return {"success": True, "message": "Heartbeat recorded"}
    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_id}/push-token")
async def update_push_token(device_id: str, push_token: str = Body(..., embed=True)) -> dict:
    """Update push token for a device."""
    service = get_device_identity_service()
    if service.update_push_token(device_id, push_token):
        return {"success": True, "message": "Push token updated"}
    raise HTTPException(status_code=404, detail="Device not found")
