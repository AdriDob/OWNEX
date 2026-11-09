"""Manual/API sync snapshots for connected providers.

Stores the last synced data payload per provider under the OWNEX data dir.
Never stores credentials — only data the user or an API adapter synced.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("ownex.connections.snapshots")

_SAFE_NAME = re.compile(r"[^a-z0-9_-]+")


def _snapshot_dir() -> Path:
    return get_config().data_dir / "connections" / "snapshots"


def _snapshot_path(provider: str) -> Path:
    safe = _SAFE_NAME.sub("_", provider.lower()).strip("_") or "unknown"
    return _snapshot_dir() / f"{safe}.json"


def save_snapshot(provider: str, payload: dict[str, Any], *, source: str = "manual") -> dict[str, Any]:
    """Persist a sync snapshot. Returns the stored envelope."""
    envelope = {
        "provider": provider,
        "source": source,
        "synced_at": datetime.now(UTC).isoformat(),
        "data": payload,
    }
    path = _snapshot_path(provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, indent=2, default=str))
    logger.info("Snapshot saved for provider=%s source=%s", provider, source)
    return envelope


def load_snapshot(provider: str) -> dict[str, Any] | None:
    path = _snapshot_path(provider)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load snapshot for %s: %s", provider, exc)
        return None
