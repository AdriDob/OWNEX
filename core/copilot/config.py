"""Copilot configuration via environment/settings."""

from __future__ import annotations

import logging
import os

from core.copilot.permissions import AuthorityLevel

logger = logging.getLogger("orion.core.copilot.config")


class CopilotConfig:
    """Configuration for the Senior Copilot Agent.

    Reads from environment variables with sensible defaults.
    """

    def __init__(self) -> None:
        self.authority_level: AuthorityLevel = AuthorityLevel.from_str(
            os.environ.get("COPILOT_AUTHORITY", "observer"),
        )
        self.min_confidence_auto: float = float(
            os.environ.get("COPILOT_MIN_CONFIDENCE_AUTO", "0.70"),
        )
        self.min_confidence_report: float = float(
            os.environ.get("COPILOT_MIN_CONFIDENCE_REPORT", "0.92"),
        )
        self.max_decisions_logged: int = int(
            os.environ.get("COPILOT_MAX_DECISIONS", "1000"),
        )
        self.enable_auto_audit: bool = os.environ.get("COPILOT_ENABLE_AUTO_AUDIT", "true").lower() == "true"
        self.auto_audit_interval_hours: int = int(
            os.environ.get("COPILOT_AUDIT_INTERVAL", "24"),
        )
        self.enable_auto_review: bool = os.environ.get("COPILOT_ENABLE_AUTO_REVIEW", "true").lower() == "true"
        self.memory_enabled: bool = os.environ.get("COPILOT_MEMORY_ENABLED", "true").lower() == "true"
        self.hunter_mode: str = os.environ.get("COPILOT_HUNTER_MODE", "standard")

    def to_dict(self) -> dict:
        return {
            "authority_level": self.authority_level.value,
            "min_confidence_auto": self.min_confidence_auto,
            "min_confidence_report": self.min_confidence_report,
            "max_decisions_logged": self.max_decisions_logged,
            "enable_auto_audit": self.enable_auto_audit,
            "auto_audit_interval_hours": self.auto_audit_interval_hours,
            "enable_auto_review": self.enable_auto_review,
            "memory_enabled": self.memory_enabled,
            "hunter_mode": self.hunter_mode,
        }
