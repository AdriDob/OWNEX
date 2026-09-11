"""Hunter levels — XP progression from verified outcomes only.

Rules (never broken):
- XP comes ONLY from real events (confirmed finding, accepted report,
  received payout, completed stage/task, hit milestone). Hypotheses,
  views and clicks grant nothing.
- Append-only JSONL ledger under OWNEX_DATA_DIR/levels/xp.jsonl
  (survives restarts, diffable, path-injectable for tests).
- Levels are thresholds over lifetime XP, 1-10 with Spanish titles.
- Unknown events raise ValueError (never invent XP).
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.levels")

LEVELS_FILENAME = "xp.jsonl"

# Event → XP. Conservative: a payout is worth 10x a confirmed finding.
XP_TABLE: dict[str, int] = {
    "task_completed": 10,
    "stage_completed": 15,
    "finding_confirmed": 25,
    "opportunity_delivered": 30,
    "report_accepted": 50,
    "milestone_hit": 75,
    "payout_received": 100,
}

# (level, title, threshold XP)
LEVELS: tuple[tuple[int, str, int], ...] = (
    (1, "Novato", 0),
    (2, "Aprendiz", 100),
    (3, "Operador", 250),
    (4, "Cazador", 500),
    (5, "Profesional", 1000),
    (6, "Veterano", 2000),
    (7, "Experto", 4000),
    (8, "Elite", 7000),
    (9, "Leyenda", 11000),
    (10, "Mito", 16000),
)


def _data_dir() -> Path:
    return Path(os.environ.get("OWNEX_DATA_DIR", "data"))


@dataclass(frozen=True, slots=True)
class XpEvent:
    """One verified XP grant."""

    event: str
    xp: int
    ref_id: str = ""
    note: str = ""
    recorded_at: str = ""


@dataclass(frozen=True, slots=True)
class LevelInfo:
    """Current level snapshot."""

    level: int
    title: str
    total_xp: int
    current_threshold: int
    next_threshold: int | None
    pct_to_next: float


class ProgressionEngine:
    """Append-only XP ledger + level computation."""

    def __init__(self, store_path: str | Path | None = None) -> None:
        base = Path(store_path) if store_path else _data_dir() / "levels"
        self.store_path = base / LEVELS_FILENAME if base.is_dir() or not str(base).endswith(".jsonl") else base

    def award(self, event: str, ref_id: str = "", note: str = "") -> XpEvent:
        """Grant XP for a verified event. Unknown events raise (never invent)."""
        if event not in XP_TABLE:
            raise ValueError(f"unknown XP event: {event!r} (known: {sorted(XP_TABLE)})")
        rec = XpEvent(
            event=event,
            xp=XP_TABLE[event],
            ref_id=ref_id,
            note=note,
            recorded_at=datetime.now(UTC).isoformat(),
        )
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")
        return rec

    def _load(self) -> list[XpEvent]:
        if not self.store_path.exists():
            return []
        records: list[XpEvent] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    records.append(XpEvent(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    logger.warning("levels: corrupt XP line ignored")
        except OSError as exc:
            logger.warning("levels: store unreadable: %s", exc)
        return records

    def total_xp(self) -> int:
        return sum(r.xp for r in self._load())

    def level(self) -> LevelInfo:
        total = self.total_xp()
        current = LEVELS[0]
        nxt: tuple[int, str, int] | None = None
        for i, entry in enumerate(LEVELS):
            if total >= entry[2]:
                current = entry
                nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
        if nxt is None:
            pct = 100.0
        else:
            span = nxt[2] - current[2]
            pct = round((total - current[2]) / span * 100, 1) if span > 0 else 100.0
        return LevelInfo(
            level=current[0],
            title=current[1],
            total_xp=total,
            current_threshold=current[2],
            next_threshold=nxt[2] if nxt else None,
            pct_to_next=pct,
        )

    def history(self, limit: int = 50) -> list[XpEvent]:
        records = self._load()
        return records[-limit:]

    def summary(self) -> dict[str, Any]:
        lv = self.level()
        by_event: dict[str, int] = {}
        for r in self._load():
            by_event[r.event] = by_event.get(r.event, 0) + 1
        return {
            "level": lv.level,
            "title": lv.title,
            "total_xp": lv.total_xp,
            "current_threshold": lv.current_threshold,
            "next_threshold": lv.next_threshold,
            "pct_to_next": lv.pct_to_next,
            "events": by_event,
        }


_singleton: ProgressionEngine | None = None


def get_progression_engine(store_path: str | Path | None = None) -> ProgressionEngine:
    global _singleton
    if _singleton is None or store_path is not None:
        _singleton = ProgressionEngine(store_path)
    return _singleton


def reset_progression_engine() -> None:
    global _singleton
    _singleton = None
