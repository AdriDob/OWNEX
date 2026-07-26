"""ProgramChangeTracker — persistent diff detection for program discovery.

Tracks known programs across scrape cycles to detect:
- New programs (never seen before)
- Removed programs (no longer listed)
- Updated programs (payout, scope, or tech changes)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cores.bounty_scraper.scraper import ScrapedProgram

logger = logging.getLogger("cateye.bounty_scraper.changes")

KNOWN_PROGRAMS_PATH = os.path.expanduser("~/.orion/known_programs.json")


@dataclass
class ProgramSnapshot:
    platform: str
    name: str
    program_url: str
    estimated_payout: int
    raw_payout_range: str
    technologies: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    wildcards: list[str] = field(default_factory=list)
    has_rewards: bool = True
    first_seen: str = ""
    last_seen: str = ""
    checks: int = 1

    @classmethod
    def from_scraped(cls, prog: Any) -> ProgramSnapshot:
        return cls(
            platform=prog.platform,
            name=prog.name,
            program_url=prog.program_url,
            estimated_payout=prog.estimated_payout,
            raw_payout_range=prog.raw_payout_range,
            technologies=prog.technologies,
            domains=prog.domains,
            wildcards=prog.wildcards,
            has_rewards=prog.has_rewards,
        )

    def key(self) -> str:
        return f"{self.platform.lower()}:{'_'.join(self.name.lower().split())}"


@dataclass
class DiscoveryDiff:
    new_programs: list[ProgramSnapshot] = field(default_factory=list)
    removed_programs: list[ProgramSnapshot] = field(default_factory=list)
    updated_programs: list[dict[str, Any]] = field(default_factory=list)
    total_before: int = 0
    total_after: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(self.new_programs or self.removed_programs or self.updated_programs)


class ProgramChangeTracker:
    """Tracks known programs across scrape cycles."""

    def __init__(self, path: str = KNOWN_PROGRAMS_PATH):
        self._path = path
        self._known: dict[str, ProgramSnapshot] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("programs", []):
                snap = ProgramSnapshot(**entry)
                self._known[snap.key()] = snap
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load known programs: %s", e)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "programs": [asdict(snap) for snap in self._known.values()],
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def compute_diff(self, programs: list[ScrapedProgram]) -> DiscoveryDiff:
        now = datetime.now(timezone.utc).isoformat()
        current_keys: set[str] = set()
        current_snapshots: dict[str, ProgramSnapshot] = {}

        for prog in programs:
            snap = ProgramSnapshot.from_scraped(prog)
            key = snap.key()
            current_keys.add(key)
            current_snapshots[key] = snap

        diff = DiscoveryDiff()
        diff.total_before = len(self._known)
        diff.total_after = len(current_keys)

        new_keys = current_keys - self._known.keys()
        removed_keys = self._known.keys() - current_keys
        common_keys = current_keys & self._known.keys()

        for key in new_keys:
            snap = current_snapshots[key]
            snap.first_seen = now
            snap.last_seen = now
            diff.new_programs.append(snap)
            self._known[key] = snap

        for key in removed_keys:
            diff.removed_programs.append(self._known[key])
            del self._known[key]

        for key in common_keys:
            old = self._known[key]
            new_snap = current_snapshots[key]
            changes: list[str] = []
            if old.estimated_payout != new_snap.estimated_payout:
                changes.append("payout")
            if old.technologies != new_snap.technologies:
                changes.append("technologies")
            if old.domains != new_snap.domains or old.wildcards != new_snap.wildcards:
                changes.append("scope")
            if old.raw_payout_range != new_snap.raw_payout_range and "payout" not in changes:
                changes.append("payout")
            if changes:
                diff.updated_programs.append(
                    {
                        "program": old.key(),
                        "platform": old.platform,
                        "name": old.name,
                        "changes": changes,
                        "before": {"payout": old.estimated_payout, "payout_range": old.raw_payout_range},
                        "after": {"payout": new_snap.estimated_payout, "payout_range": new_snap.raw_payout_range},
                    }
                )
            old.last_seen = now
            old.checks += 1

        if diff.has_changes or diff.total_before == 0:
            self._save()

        return diff

    def get_known_count(self) -> int:
        return len(self._known)

    def reset(self) -> None:
        self._known.clear()
        if os.path.exists(self._path):
            os.remove(self._path)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tracked_programs": len(self._known),
            "path": self._path,
        }


_TRACKER: ProgramChangeTracker | None = None


def get_change_tracker() -> ProgramChangeTracker:
    global _TRACKER
    if _TRACKER is None:
        _TRACKER = ProgramChangeTracker()
    return _TRACKER
