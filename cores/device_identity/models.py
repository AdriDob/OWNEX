"""Device Identity Models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class DevicePlatform(StrEnum):
    """Platform types for device identification."""

    DESKTOP = "desktop"
    MOBILE = "mobile"
    WATCH = "watch"
    WEB = "web"


@dataclass(slots=True)
class DeviceIdentity:
    """Device identity record."""

    device_id: str
    platform: str
    name: str
    push_token: str | None = None
    capabilities: list[str] = field(default_factory=list)
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "platform": self.platform,
            "name": self.name,
            "push_token": self.push_token,
            "capabilities": self.capabilities,
            "last_seen": self.last_seen,
            "registered_at": self.registered_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DeviceIdentity:
        return cls(
            device_id=data["device_id"],
            platform=data["platform"],
            name=data["name"],
            push_token=data.get("push_token"),
            capabilities=data.get("capabilities", []),
            last_seen=data.get("last_seen", ""),
            registered_at=data.get("registered_at", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass(slots=True)
class DeviceRegistration:
    """Device registration request/response."""

    device_id: str
    platform: str
    name: str
    push_token: str | None = None
    capabilities: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_device_identity(self) -> DeviceIdentity:
        return DeviceIdentity(
            device_id=self.device_id,
            platform=self.platform,
            name=self.name,
            push_token=self.push_token,
            capabilities=self.capabilities or [],
            metadata=self.metadata or {},
        )


def generate_device_id() -> str:
    """Generate a new unique device ID."""

    return f"dev_{__import__('uuid').uuid4().hex[:16]}"
