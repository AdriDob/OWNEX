"""Base tool interface for Hermes Desktop Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ToolResult:
    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }


class BaseTool:
    name: str = ""
    description: str = ""
    requires_admin: bool = False
    requires_windows: bool = False

    def check_available(self) -> ToolResult:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name!r})>"
