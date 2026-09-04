"""Configuration Detector — Shows what's ready, what needs config, what's blocked.

Never silently fail. Always tell the user what's missing.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("ownex.configuration.detector")


@dataclass
class ConfigItem:
    """A configuration item."""

    id: str
    name: str
    category: str  # api_key, account, email, notification, payment, profile, timezone, goals
    status: str  # ready, partially_ready, action_required, blocked
    description: str
    instructions: str = ""
    env_var: str = ""
    is_optional: bool = False
    last_checked: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "description": self.description,
            "instructions": self.instructions,
            "env_var": self.env_var,
            "is_optional": self.is_optional,
        }


class ConfigurationDetector:
    """Detects what's configured, what's missing, what's blocked."""

    def __init__(self) -> None:
        self.items: list[ConfigItem] = []
        self._detect_all()

    def _detect_all(self) -> None:
        """Detect all configuration items."""
        self.items = []

        # API Keys
        self._check_env("hackerone_api_key", "HackerOne API Key", "api_key", "For bounty submissions")
        self._check_env("bugcrowd_api_key", "Bugcrowd API Key", "api_key", "For bounty submissions")
        self._check_env("intigriti_api_key", "Intigriti API Key", "api_key", "For bounty submissions")
        self._check_env("opire_api_key", "Opire API Key", "api_key", "For dev bounties")
        self._check_env("algora_api_key", "Algora API Key", "api_key", "For dev bounties")

        # Email
        self._check_env("SMTP_HOST", "SMTP Host", "email", "For monthly reports")
        self._check_env("SMTP_PORT", "SMTP Port", "email", "For monthly reports")
        self._check_env("SMTP_USER", "SMTP User", "email", "For monthly reports")
        self._check_env("SMTP_PASSWORD", "SMTP Password", "email", "For monthly reports")
        self._check_env("NOTIFICATION_EMAIL", "Notification Email", "email", "Where to send reports")

        # Mobile
        self._check_env("FCM_SERVER_KEY", "FCM Server Key", "notification", "For mobile push notifications")

        # Database
        self._check_item(
            "database",
            "Database",
            "infrastructure",
            "ready" if os.path.exists(os.path.expanduser("~/.ownex/database/cateye.db")) else "action_required",
            "SQLite database for all data",
            "Database is created automatically on first run",
        )

        # Scheduler
        self._check_item(
            "scheduler",
            "Scheduler",
            "automation",
            "ready",
            "Background scheduler for pipeline",
            "Starts automatically with API",
        )

        # Backup
        backup_dir = os.path.expanduser("~/.ownex/backups")
        self._check_item(
            "backup",
            "Backup Directory",
            "infrastructure",
            "ready" if os.path.exists(backup_dir) else "action_required",
            "Database backup location",
            f"Run: mkdir -p {backup_dir}",
        )

    def _check_env(self, env_var: str, name: str, category: str, description: str) -> None:
        """Check if an environment variable is set."""
        value = os.environ.get(env_var, "")
        status = "ready" if value else "action_required"
        self.items.append(
            ConfigItem(
                id=env_var.lower(),
                name=name,
                category=category,
                status=status,
                description=description,
                instructions=f"Set {env_var} in .env or environment",
                env_var=env_var,
                is_optional=category == "api_key",
            )
        )

    def _check_item(
        self,
        item_id: str,
        name: str,
        category: str,
        status: str,
        description: str,
        instructions: str,
    ) -> None:
        """Check a non-env configuration item."""
        self.items.append(
            ConfigItem(
                id=item_id,
                name=name,
                category=category,
                status=status,
                description=description,
                instructions=instructions,
            )
        )

    def get_dashboard(self) -> dict[str, Any]:
        """Get configuration dashboard."""
        total = len(self.items)
        ready = sum(1 for i in self.items if i.status == "ready")
        partial = sum(1 for i in self.items if i.status == "partially_ready")
        action_required = sum(1 for i in self.items if i.status == "action_required")
        blocked = sum(1 for i in self.items if i.status == "blocked")

        # Group by category
        by_category = {}
        for item in self.items:
            if item.category not in by_category:
                by_category[item.category] = []
            by_category[item.category].append(item.to_dict())

        # Missing items (action required)
        missing = [i.to_dict() for i in self.items if i.status == "action_required"]

        # Overall readiness
        if total == 0:
            readiness = 0
        else:
            readiness = round((ready / total) * 100, 1)

        return {
            "readiness": readiness,
            "total": total,
            "ready": ready,
            "partially_ready": partial,
            "action_required": action_required,
            "blocked": blocked,
            "by_category": by_category,
            "missing": missing,
            "recommendation": self._get_recommendation(missing),
            "checked_at": datetime.now(UTC).isoformat(),
        }

    def _get_recommendation(self, missing: list[dict]) -> str:
        """Get a recommendation based on missing items."""
        if not missing:
            return "All configuration is complete. OWNEX is fully operational."

        categories = set(m["category"] for m in missing)
        if "api_key" in categories:
            return "Configure API keys for maximum opportunity discovery. OWNEX works without them but finds fewer opportunities."
        if "email" in categories:
            return "Configure SMTP for monthly reports. Optional for daily operation."
        if "notification" in categories:
            return "Configure FCM for mobile push notifications. Optional."
        return "Some configuration is missing. Check the details below."

    def to_dict(self) -> dict[str, Any]:
        """Serialize detector state."""
        return self.get_dashboard()


# Singleton
_config_detector: ConfigurationDetector | None = None


def get_config_detector() -> ConfigurationDetector:
    """Get or create the global configuration detector."""
    global _config_detector
    if _config_detector is None:
        _config_detector = ConfigurationDetector()
    return _config_detector
