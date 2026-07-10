"""Hermes configuration — env-based settings."""

from __future__ import annotations

import os

HERMES_SAFE_MODE = os.getenv("HERMES_SAFE_MODE", "true").lower() in ("1", "true", "yes")
HERMES_LOG_ACTIONS = os.getenv("HERMES_LOG_ACTIONS", "true").lower() in ("1", "true", "yes")
HERMES_AUTO_BACKUP = os.getenv("HERMES_AUTO_BACKUP", "false").lower() in ("1", "true", "yes")
HERMES_BACKUP_INTERVAL_H = int(os.getenv("HERMES_BACKUP_INTERVAL_H", "24"))
