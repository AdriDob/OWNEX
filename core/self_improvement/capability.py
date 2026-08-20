"""Capability tracking for the self-improvement loop.

Tracks per-skill performance (attempts, successes, last reward) and exposes it
through the shared CapabilityRegistry so other modules can see what the system
learned. Uses the existing registry, never duplicates it.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from core.self_improvement.config import SelfImprovementConfig

logger = logging.getLogger("ownex.self_improvement.capability")


class CapabilityTracker:
    """Rolling per-skill statistics persisted as JSON."""

    def __init__(self, config: SelfImprovementConfig, path: str | Path | None = None) -> None:
        self.config = config
        self.path = Path(path) if path else config.store_paths()["capabilities"]
        self._lock = threading.Lock()
        self._stats: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._stats = dict(raw)
        except Exception as exc:  # noqa: BLE001 — never crash on corrupt store
            logger.warning("failed to load capability stats from %s: %s", self.path, exc)
            self._stats = {}

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._stats, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def record(self, skill: str, success: bool, reward: float) -> None:
        if not skill:
            return
        with self._lock:
            entry = self._stats.setdefault(
                skill,
                {"attempts": 0, "successes": 0, "total_reward": 0.0, "last_reward": 0.0},
            )
            entry["attempts"] += 1
            if success:
                entry["successes"] += 1
            entry["total_reward"] = round(float(entry["total_reward"]) + reward, 6)
            entry["last_reward"] = round(float(reward), 6)
            self._persist()

    def stats(self) -> dict[str, Any]:
        with self._lock:
            out: dict[str, Any] = {}
            for skill, entry in self._stats.items():
                attempts = int(entry.get("attempts", 0))
                successes = int(entry.get("successes", 0))
                out[skill] = {
                    "attempts": attempts,
                    "successes": successes,
                    "success_rate": round(successes / attempts, 4) if attempts else 0.0,
                    "last_reward": round(float(entry.get("last_reward", 0.0)), 6),
                    "total_reward": round(float(entry.get("total_reward", 0.0)), 6),
                }
            return out

    def skills(self) -> list[str]:
        return sorted(self.stats().keys())
