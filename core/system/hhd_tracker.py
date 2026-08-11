"""HHD (Human Hours Daily) Tracker — Tracks human interaction time for autonomy KPI.

This module tracks how much time the system runs without human intervention.
HHD = Horas Humanas Diarias (Human Hours per Day) — lower is better for autonomy.

Goal: < 30 min/day human intervention (excellent), < 10 min/day (target).
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from pathlib import Path

# Global state
_hhd_lock = threading.RLock()
_last_human_activity: datetime = datetime.utcnow()
_system_start_time: datetime = datetime.utcnow()
_idle_seconds_accumulator: float = 0.0
_tracker_initialized: bool = False
_persist_path: Path | None = None


def init_hhd_tracker(data_dir: str | None = None) -> None:
    """Initialize the HHD tracker. Call once at application startup."""
    global _tracker_initialized, _persist_path, _system_start_time, _last_human_activity

    with _hhd_lock:
        if _tracker_initialized:
            return

        _system_start_time = datetime.utcnow()
        _last_human_activity = datetime.utcnow()

        # Setup persistence
        if data_dir:
            _persist_path = Path(data_dir) / "hhd_state.json"
        else:
            # Default to OWNEX config dir
            config_dir = Path(os.environ.get("OWNEX_DATA_DIR", Path.home() / ".config" / "ownex"))
            config_dir.mkdir(parents=True, exist_ok=True)
            _persist_path = config_dir / "hhd_state.json"

        # Load persisted state
        _load_persisted_state()

        _tracker_initialized = True


def _load_persisted_state() -> None:
    """Load HHD state from disk."""
    global _last_human_activity, _idle_seconds_accumulator, _system_start_time

    if _persist_path and _persist_path.exists():
        try:
            import json

            with open(_persist_path) as f:
                data = json.load(f)

            if "last_human_activity" in data:
                _last_human_activity = datetime.fromisoformat(data["last_human_activity"])
            if "idle_seconds_accumulator" in data:
                _idle_seconds_accumulator = float(data["idle_seconds_accumulator"])
            if "system_start_time" in data:
                _system_start_time = datetime.fromisoformat(data["system_start_time"])
        except Exception:
            # Ignore corrupted state, start fresh
            pass


def _persist_state() -> None:
    """Persist HHD state to disk."""
    if not _persist_path:
        return

    try:
        import json

        data = {
            "last_human_activity": _last_human_activity.isoformat(),
            "idle_seconds_accumulator": _idle_seconds_accumulator,
            "system_start_time": _system_start_time.isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Atomic write
        tmp_path = _persist_path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data, f)
        tmp_path.replace(_persist_path)
    except Exception:
        pass  # Best effort


def record_human_activity() -> None:
    """Call this whenever a human interacts with the system (API call, CLI, UI click, etc.)."""
    global _last_human_activity, _idle_seconds_accumulator

    with _hhd_lock:
        now = datetime.utcnow()
        idle_duration = (now - _last_human_activity).total_seconds()
        _idle_seconds_accumulator += idle_duration
        _last_human_activity = now
        _persist_state()


def get_idle_seconds() -> float:
    """Get total idle seconds since last human activity (including current idle period)."""
    with _hhd_lock:
        now = datetime.utcnow()
        current_idle = (now - _last_human_activity).total_seconds()
        return _idle_seconds_accumulator + current_idle


def get_idle_hours() -> float:
    """Get total idle hours."""
    return round(get_idle_seconds() / 3600, 2)


def get_last_activity() -> datetime:
    """Get timestamp of last recorded human activity."""
    with _hhd_lock:
        return _last_human_activity


def get_uptime_hours() -> float:
    """Get system uptime in hours."""
    with _hhd_lock:
        return round((datetime.utcnow() - _system_start_time).total_seconds() / 3600, 2)


def get_hhd_summary() -> dict:
    """Get HHD summary for health API."""
    with _hhd_lock:
        return {
            "idle_hours": get_idle_hours(),
            "uptime_hours": get_uptime_hours(),
            "last_human_activity": get_last_activity().isoformat(),
            "system_start_time": _system_start_time.isoformat(),
            "autonomy_score": _calculate_autonomy_score(),
        }


def _calculate_autonomy_score() -> float:
    """Calculate autonomy score (0-100). Higher = more autonomous.

    Score based on: idle_hours / uptime_hours * 100
    100 = fully autonomous (no human intervention)
    0 = constant human supervision
    """
    with _hhd_lock:
        uptime_h = get_uptime_hours()
        if uptime_h <= 0:
            return 100.0
        idle_h = get_idle_hours()
        # Cap at 100%
        return min(100.0, round((idle_h / uptime_h) * 100, 1))


def reset_tracker() -> None:
    """Reset tracker (for testing or new session)."""
    global _last_human_activity, _idle_seconds_accumulator, _system_start_time

    with _hhd_lock:
        _system_start_time = datetime.utcnow()
        _last_human_activity = datetime.utcnow()
        _idle_seconds_accumulator = 0.0
        _persist_state()


# Auto-record activity on module import (counts as system activity)
# This ensures the tracker starts with a baseline
if not _tracker_initialized:
    # Defer initialization until explicitly called
    pass
