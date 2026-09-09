"""Freelance channel status — OPTIONAL commercial engine control.

Freelance is NOT a mandatory path in OWNEX. It is evaluated by the same
Opportunity Scoring Engine as everything else, and this registry is the
manual override:

- ACTIVE:   channel participates in recommendations.
- PAUSED:   temporarily hidden from recommendations (state kept).
- DISABLED: hidden until explicitly re-enabled.
- EXCLUDED: never recommend (user decision, e.g. Upwork/uTest).

Persisted in the OWNEX data dir so it survives restarts.
"""

from __future__ import annotations

import json
import logging
import os
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.freelance.channels")


class ChannelStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    EXCLUDED = "excluded"


# Freelance-family channels managed here. Primary engines
# (AI training, dev bounties, bug bounties) are NOT governed by this registry.
FREELANCE_CHANNELS: tuple[str, ...] = ("workana", "fiverr")

_DEFAULT_STATUS: dict[str, ChannelStatus] = {
    "workana": ChannelStatus.ACTIVE,
    "fiverr": ChannelStatus.ACTIVE,
}


def _store_path() -> Path:
    data_dir = os.environ.get("OWNEX_DATA_DIR", str(Path.home() / ".ownex"))
    return Path(data_dir) / "freelance_channels.json"


def _load() -> dict[str, str]:
    try:
        path = _store_path()
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not load freelance channel status: %s", exc)
    return {}


def _save(state: dict[str, str]) -> None:
    try:
        path = _store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2))
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not save freelance channel status: %s", exc)


def get_status(channel: str) -> ChannelStatus:
    """Return the status for a channel (defaults to ACTIVE for known channels)."""
    key = channel.strip().lower()
    state = _load()
    raw = state.get(key)
    if raw:
        try:
            return ChannelStatus(raw)
        except ValueError:
            pass
    return _DEFAULT_STATUS.get(key, ChannelStatus.ACTIVE)


def set_status(channel: str, status: ChannelStatus | str) -> ChannelStatus:
    """Set and persist the status for a channel."""
    key = channel.strip().lower()
    if isinstance(status, str):
        status = ChannelStatus(status.strip().lower())
    state = _load()
    state[key] = status.value
    _save(state)
    return status


def is_recommending(channel: str) -> bool:
    """Only ACTIVE channels participate in recommendations."""
    return get_status(channel) == ChannelStatus.ACTIVE


def list_channels() -> dict[str, Any]:
    """All freelance channels with status and recommendation flag."""
    return {
        channel: {
            "status": get_status(channel).value,
            "recommending": is_recommending(channel),
        }
        for channel in FREELANCE_CHANNELS
    }


def filter_by_channel_status(opportunities: list[Any]) -> list[Any]:
    """Drop opportunities from non-ACTIVE freelance channels.

    Primary engines pass through untouched; only freelance-family
    platforms (workana/fiverr) are filtered. Never raises.
    """
    try:
        out = []
        for opp in opportunities:
            platform = getattr(opp, "platform", "")
            key = str(getattr(platform, "value", platform) or "").strip().lower()
            if key in FREELANCE_CHANNELS and not is_recommending(key):
                continue
            out.append(opp)
        return out
    except Exception:  # pragma: no cover
        return opportunities
