from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class UpdateInfo:
    current_version: str
    remote_version: str | None = None
    remote_url: str = "origin/main"
    commits_behind: int = 0
    has_update: bool = False
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_version": self.current_version,
            "remote_version": self.remote_version,
            "remote_url": self.remote_url,
            "commits_behind": self.commits_behind,
            "has_update": self.has_update,
            "checked_at": self.checked_at,
        }


@dataclass
class UpdateResult:
    success: bool
    pulled: bool = False
    dependencies_installed: bool = False
    migrated: bool = False
    restarted: bool = False
    error: str | None = None
    log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "pulled": self.pulled,
            "dependencies_installed": self.dependencies_installed,
            "migrated": self.migrated,
            "restarted": self.restarted,
            "error": self.error,
            "log": self.log,
        }


class UpdateStatus:
    IDLE = "idle"
    CHECKING = "checking"
    PULLING = "pulling"
    INSTALLING = "installing"
    MIGRATING = "migrating"
    RESTARTING = "restarting"
    DONE = "done"
    FAILED = "failed"
