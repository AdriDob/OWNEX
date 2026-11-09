"""Sync history — append-only JSONL log of sync/import events per provider.

Gives OWNEX traceability: when each sync ran, source, mode, records count,
and outcome — without storing credentials or raw payloads.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("ownex.connections.sync_history")

_SAFE_NAME = re.compile(r"[^a-z0-9_-]+")
MAX_HISTORY_ENTRIES = 200


def _history_path(provider: str) -> Path:
    safe = _SAFE_NAME.sub("_", provider.lower()).strip("_") or "unknown"
    return get_config().data_dir / "connections" / "history" / f"{safe}.jsonl"


def record_event(provider: str, event: dict[str, Any]) -> None:
    """Append a sync/import event. ``event`` must not contain secrets."""
    entry = {"ts": datetime.now(UTC).isoformat(), "provider": provider, **event}
    path = _history_path(provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    logger.info("Sync history event provider=%s kind=%s", provider, event.get("kind"))


def get_history(provider: str, limit: int = 50) -> list[dict[str, Any]]:
    path = _history_path(provider)
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read sync history for %s: %s", provider, exc)
        return []
    return entries[-max(1, min(limit, MAX_HISTORY_ENTRIES)) :][::-1]
