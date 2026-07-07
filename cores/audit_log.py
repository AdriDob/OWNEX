"""Audit log for authentication and security events.

Appends structured events to ~/.orion/audit.jsonl (owner-read-only).
No secrets or tokens are ever written to the log.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("cateye.audit")

_AUDIT_LOG: str | None = None


def _get_log_path() -> str:
    global _AUDIT_LOG
    if _AUDIT_LOG is None:
        home = os.environ.get("HOME", os.environ.get("USERPROFILE", "."))
        _AUDIT_LOG = os.path.join(home, ".orion", "audit.jsonl")
    return _AUDIT_LOG


def log_event(event: str, actor: str = "", detail: str = "", metadata: dict[str, Any] | None = None) -> None:
    """Append an audit event to the JSONL log.

    Args:
        event: Event type (e.g. "login", "logout", "token_revoke", "license_activate")
        actor: Who performed the action (user email, device_id, or IP)
        detail: Human-readable description
        metadata: Optional structured data (no secrets!)
    """
    path = _get_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "actor": actor,
        "detail": detail,
        "metadata": metadata or {},
    }
    try:
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        os.chmod(path, 0o600)
    except OSError as exc:
        logger.warning("Failed to write audit log: %s", exc)


def get_recent(limit: int = 100) -> list[dict[str, Any]]:
    """Read the most recent audit events."""
    path = _get_log_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            lines = f.readlines()
        events = [json.loads(l) for l in lines[-limit:]]
        return events[::-1]
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read audit log: %s", exc)
        return []
