"""Trading state persistence — JSON store with atomic writes.

Single source of truth for copy trading follow state, risk controls,
intelligence alerts, proposals and strategy DNA. Survives restarts.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("catseye.trading.store")

DEFAULT_DATA_DIR = Path("data/trading")


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically (tmp + rename) to avoid corruption."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
        os.replace(tmp_path, str(path))
    except Exception:
        logger.exception("trading store atomic write failed for %s", path)
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def _read_json(path: Path) -> dict[str, Any]:
    """Read JSON tolerantly; corruption or missing file → empty state."""
    try:
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        logger.warning("trading store %s unreadable — resetting to empty state", path)
        return {}


class TradingStore:
    """Persistent state for the trading layer (copy, intelligence, reasoning)."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self._state_path = self.data_dir / "trading_state.json"

    def _load(self) -> dict[str, Any]:
        state = _read_json(self._state_path)
        state.setdefault("masters", [])
        state.setdefault("risk_controls", {})
        state.setdefault("daily_pnl", {})
        state.setdefault("alerts", [])
        state.setdefault("proposals", [])
        state.setdefault("dna", [])
        state.setdefault("status", {})
        return state

    def _save(self, state: dict[str, Any]) -> None:
        _atomic_write_json(self._state_path, state)

    def get(self, key: str) -> Any:
        return self._load().get(key)

    def set(self, key: str, value: Any) -> None:
        state = self._load()
        state[key] = value
        self._save(state)

    def update(self, key: str, value: Any) -> None:
        state = self._load()
        state[key] = value
        self._save(state)

    def upsert_item(self, key: str, item: dict[str, Any], id_key: str = "id") -> None:
        """Insert or replace an item in a list by its id."""
        state = self._load()
        items = state.get(key, [])
        items = [i for i in items if i.get(id_key) != item.get(id_key)]
        items.append(item)
        state[key] = items
        self._save(state)

    def remove_item(self, key: str, item_id: str, id_key: str = "id") -> bool:
        state = self._load()
        items = state.get(key, [])
        remaining = [i for i in items if i.get(id_key) != item_id]
        if len(remaining) == len(items):
            return False
        state[key] = remaining
        self._save(state)
        return True

    def now_iso(self) -> str:
        return datetime.now(UTC).isoformat()
