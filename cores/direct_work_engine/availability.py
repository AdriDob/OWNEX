"""Availability Intelligence — know ANTES if you have time for a task.

Single source of truth for human availability. Feeds income_plan, workbank,
and the Income Command Center. Zero invented data — only what the user
configures (Profile Kit) + optional calendar integration.

Core principle: availability is a HARD constraint, not a probability.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cores.direct_work_engine.profile_kit import ProfileKitEngine, UserProfile

logger = logging.getLogger("ownex.availability")


@dataclass(slots=True)
class AvailabilitySnapshot:
    """Current availability state for planning."""

    generated_at: str
    hours_today: float
    hours_this_week: float
    hours_this_month: float
    source: str  # "profile_kit" | "calendar" | "fallback"
    note: str


@dataclass(slots=True)
class TimeBlock:
    """A block of available or busy time."""

    start: str  # ISO datetime
    end: str
    type: str  # "available" | "busy" | "focus"
    title: str = ""


class AvailabilityEngine:
    """Computes available hours from Profile Kit + optional calendar."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or self._default_data_dir()
        self._calendar_path = self._data_dir / "availability_calendar.json"
        self._profile_kit = ProfileKitEngine()

    @staticmethod
    def _default_data_dir() -> Path:
        return Path(os.getenv("OWNEX_DATA_DIR", Path(__file__).resolve().parents[3] / "data"))

    # ── Public API ──

    def get_snapshot(self) -> AvailabilitySnapshot:
        """Get current availability snapshot (today/week/month)."""
        profile = self._load_profile()
        base_weekly = (
            float(profile.availability_hours) if profile.availability_hours and profile.availability_hours > 0 else 40.0
        )

        # If calendar exists, refine with actual free/busy
        if self._calendar_path.exists():
            return self._snapshot_with_calendar(profile, base_weekly)

        # Fallback: distribute weekly hours evenly across work days
        daily = base_weekly / 5.0
        monthly = base_weekly * 4.33
        return AvailabilitySnapshot(
            generated_at=datetime.now(UTC).isoformat(),
            hours_today=daily,
            hours_this_week=base_weekly,
            hours_this_month=monthly,
            source="profile_kit",
            note=f"Distributed evenly (no calendar): {daily:.1f}h/day, {base_weekly:.1f}h/week",
        )

    def get_available_hours(self, horizon: str = "today") -> float:
        """Get available hours for a given horizon."""
        snap = self.get_snapshot()
        return {
            "today": snap.hours_today,
            "this_week": snap.hours_this_week,
            "this_month": snap.hours_this_month,
        }[horizon]

    def get_time_blocks(self, days: int = 7) -> list[TimeBlock]:
        """Get available/busy time blocks for the next N days."""
        if not self._calendar_path.exists():
            return self._default_blocks(days)
        return self._parse_calendar(days)

    def can_accommodate(self, required_hours: float, horizon: str = "today") -> tuple[bool, float]:
        """Check if a task requiring N hours fits in available time."""
        available = self.get_available_hours(horizon)
        return available >= required_hours, available - required_hours

    def recommend_max_task_hours(self, horizon: str = "today") -> float:
        """Suggest max task duration based on availability (80% rule)."""
        return self.get_available_hours(horizon) * 0.8

    # ── Calendar integration ──

    def import_calendar_ics(self, ics_path: Path) -> int:
        """Import events from an ICS file. Returns count of events imported."""
        # Lazy import to avoid hard dependency
        try:
            import icalendar
        except ImportError:
            raise RuntimeError("icalendar package required for ICS import: pip install icalendar")

        with open(ics_path, "rb") as f:
            cal = icalendar.Calendar.from_ical(f.read())

        events = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")
            if not dtstart or not dtend:
                continue
            start = dtstart.dt
            end = dtend.dt
            if not isinstance(start, datetime) or not isinstance(end, datetime):
                continue
            # Ensure UTC
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            else:
                start = start.astimezone(UTC)
            if end.tzinfo is None:
                end = end.replace(tzinfo=UTC)
            else:
                end = end.astimezone(UTC)
            events.append(
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "title": str(component.get("summary", "")),
                    "type": "busy",
                }
            )

        self._save_calendar(events)
        logger.info("Imported %d events from ICS", len(events))
        return len(events)

    def add_busy_block(self, start: datetime, end: datetime, title: str = "") -> None:
        """Manually add a busy block."""
        events = self._load_calendar()
        events.append(
            {
                "start": start.astimezone(UTC).isoformat(),
                "end": end.astimezone(UTC).isoformat(),
                "title": title,
                "type": "busy",
            }
        )
        self._save_calendar(events)

    def add_available_block(self, start: datetime, end: datetime, title: str = "focus") -> None:
        """Manually add an available/focus block."""
        events = self._load_calendar()
        events.append(
            {
                "start": start.astimezone(UTC).isoformat(),
                "end": end.astimezone(UTC).isoformat(),
                "title": title,
                "type": "available",
            }
        )
        self._save_calendar(events)

    # ── Internals ──

    def _load_profile(self) -> UserProfile:
        raw = self._profile_kit.get() or self._profile_kit.default_profile()
        return ProfileKitEngine.profile_from_dict(raw)

    def _snapshot_with_calendar(self, profile: UserProfile, base_weekly: float) -> AvailabilitySnapshot:
        """Compute snapshot using calendar free/busy data."""
        blocks = self.get_time_blocks(7)
        today = datetime.now(UTC).date()
        today_hours = 0.0
        week_hours = 0.0
        for b in blocks:
            if b.type != "available":
                continue
            try:
                start = datetime.fromisoformat(b.start)
                end = datetime.fromisoformat(b.end)
            except Exception:
                continue
            if start.tzinfo is None:
                start = start.replace(tzinfo=UTC)
            else:
                start = start.astimezone(UTC)
            if end.tzinfo is None:
                end = end.replace(tzinfo=UTC)
            else:
                end = end.astimezone(UTC)

            if start.date() == today:
                day_end = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
                effective_end = min(end, day_end)
                if effective_end > start:
                    today_hours += (effective_end - start).total_seconds() / 3600

            if start.date() >= today:
                week_hours += (end - start).total_seconds() / 3600

        monthly = week_hours * 4.33
        return AvailabilitySnapshot(
            generated_at=datetime.now(UTC).isoformat(),
            hours_today=max(0.0, today_hours),
            hours_this_week=max(0.0, week_hours),
            hours_this_month=max(0.0, monthly),
            source="calendar",
            note=f"Computed from calendar events: {today_hours:.1f}h today, {week_hours:.1f}h this week",
        )

    def _default_blocks(self, days: int) -> list[TimeBlock]:
        """Evenly distributed blocks when no calendar."""
        base_weekly = self._load_profile().availability_hours or 40.0
        daily = base_weekly / 5.0
        blocks = []
        today = datetime.now(UTC).date()
        for i in range(days):
            day = today + timedelta(days=i)
            if day.weekday() >= 5:  # Skip weekends by default
                continue
            start = datetime.combine(day, datetime.min.time().replace(hour=9), tzinfo=UTC)
            end = start + timedelta(hours=daily)
            blocks.append(TimeBlock(start=start.isoformat(), end=end.isoformat(), type="available", title="work"))
        return [TimeBlock(start=b.start, end=b.end, type=b.type, title=b.title) for b in blocks]

    def _load_calendar(self) -> list[dict]:
        if not self._calendar_path.exists():
            return []
        try:
            return json.loads(self._calendar_path.read_text())
        except Exception:
            return []

    def _save_calendar(self, events: list[dict]) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._calendar_path.write_text(json.dumps(events, ensure_ascii=False, indent=2))

    def _parse_calendar(self, days: int) -> list[TimeBlock]:
        events = self._load_calendar()
        now = datetime.now(UTC)
        cutoff = now + timedelta(days=days)
        blocks = []
        for ev in events:
            try:
                start = datetime.fromisoformat(ev["start"])
                end = datetime.fromisoformat(ev["end"])
            except Exception:
                continue
            if start >= cutoff or end <= datetime.now(UTC):
                continue
            blocks.append(
                TimeBlock(start=ev["start"], end=ev["end"], type=ev.get("type", "busy"), title=ev.get("title", ""))
            )
        blocks.sort(key=lambda b: b.start)
        return blocks


# ── Singleton ──

_availability_engine: AvailabilityEngine | None = None


def get_availability_engine(data_dir: Path | None = None) -> AvailabilityEngine:
    global _availability_engine
    if _availability_engine is None:
        _availability_engine = AvailabilityEngine(data_dir)
    return _availability_engine


def get_availability_snapshot() -> AvailabilitySnapshot:
    """Convenience function for API/scheduler."""
    return get_availability_engine().get_snapshot()


def get_available_hours(horizon: str = "today") -> float:
    return get_availability_engine().get_available_hours(horizon)


def can_accommodate_task(required_hours: float, horizon: str = "today") -> tuple[bool, float]:
    return get_availability_engine().can_accommodate(required_hours, horizon)


def recommend_max_task_hours(horizon: str = "today") -> float:
    return get_availability_engine().recommend_max_task_hours(horizon)
