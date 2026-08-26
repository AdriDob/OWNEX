"""Device Identity Module — Single Source of Truth for Device Identity across Desktop, Mobile, Watch."""

from __future__ import annotations

from .models import DeviceIdentity, DevicePlatform, DeviceRegistration, generate_device_id
from .service import DeviceIdentityService, get_device_identity_service

__all__ = [
    "DeviceIdentity",
    "DevicePlatform",
    "DeviceRegistration",
    "generate_device_id",
    "DeviceIdentityService",
    "get_device_identity_service",
]
