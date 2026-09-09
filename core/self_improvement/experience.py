"""Experience store for the self-improvement loop.

Persists completed loop iterations as JSON (survives restarts), exposes the
history to the curriculum (novelty), and prunes to a max size. Paths are
injectable so tests never touch real data.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

from core.self_improvement.config import SelfImprovementConfig
from core.self_improvement.models import Experience

logger = logging.getLogger("ownex.self_improvement.experience")


class ExperienceStore:
    """JSON-backed store of Experiences."""

    def __init__(self, config: SelfImprovementConfig, path: str | Path | None = None) -> None:
        self.config = config
        self.path = Path(path) if path else config.store_paths()["experiences"]
        self._lock = threading.Lock()
        self._items: list[Experience] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._items = [Experience.from_dict(item) for item in raw]
        except Exception as exc:  # noqa: BLE001 — never crash on corrupt store
            logger.warning("failed to load experiences from %s: %s", self.path, exc)
            self._items = []

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps([e.to_dict() for e in self._items], indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, experience: Experience) -> None:
        with self._lock:
            self._items.append(experience)
            if len(self._items) > self.config.max_experiences_kept:
                self._items = self._items[-self.config.max_experiences_kept :]
            self._persist()

    def all(self) -> list[Experience]:
        with self._lock:
            return list(self._items)

    def recent(self, limit: int = 20) -> list[Experience]:
        return self.all()[-limit:]

    def count(self) -> int:
        return len(self._items)

    def success_rate(self, recent: int = 50) -> float:
        items = self.all()[-recent:]
        if not items:
            return 0.0
        return sum(1 for e in items if e.evaluation.valid) / len(items)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.all()]
