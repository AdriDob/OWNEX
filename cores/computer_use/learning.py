"""Computer Use Learning System — Improve form filling over time.

Records successful form fills, stores field positions, and updates platform
templates so that subsequent attempts are faster and more accurate.

Architecture:
    Fill Attempt → Success/Failure → Learning Record → Template Update → Better Next Time

Key concepts:
    - FillRecord: one successful form fill with all metadata
    - FieldPosition: learned position of a field (coordinates, selector, tab order)
    - PlatformLearning: aggregate performance data per platform
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.computer_use.learning")


@dataclass
class FieldPosition:
    """Learned position of a form field on a platform."""

    field_name: str
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    css_selector: str = ""
    tab_index: int = -1  # tab order position
    confidence: float = 0.0  # how reliable this position is [0-1]
    times_used: int = 0
    times_succeeded: int = 0
    last_verified: float = 0.0  # timestamp
    screenshot_path: str = ""  # screenshot where this was detected

    @property
    def success_rate(self) -> float:
        return self.times_succeeded / max(1, self.times_used)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "css_selector": self.css_selector,
            "tab_index": self.tab_index,
            "confidence": round(self.confidence, 3),
            "times_used": self.times_used,
            "times_succeeded": self.times_succeeded,
            "success_rate": round(self.success_rate, 3),
            "last_verified": self.last_verified,
        }


@dataclass
class FillRecord:
    """Record of a single form fill attempt."""

    id: str
    platform: str
    task: str
    success: bool
    fields_filled: list[dict[str, Any]]
    field_positions: list[FieldPosition]
    duration_ms: float = 0.0
    steps_taken: int = 0
    screenshots: list[str] = field(default_factory=list)
    error: str | None = None
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "platform": self.platform,
            "task": self.task,
            "success": self.success,
            "fields_filled": self.fields_filled,
            "field_positions": [fp.to_dict() for fp in self.field_positions],
            "duration_ms": self.duration_ms,
            "steps_taken": self.steps_taken,
            "screenshots": self.screenshots,
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class PlatformLearning:
    """Aggregate learning data for a platform."""

    platform: str
    total_attempts: int = 0
    successful_fills: int = 0
    failed_fills: int = 0
    avg_duration_ms: float = 0.0
    avg_steps: float = 0.0
    field_positions: dict[str, FieldPosition] = field(default_factory=dict)
    last_attempt: float = 0.0
    best_duration_ms: float = float("inf")
    common_errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        return self.successful_fills / max(1, self.total_attempts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "total_attempts": self.total_attempts,
            "successful_fills": self.successful_fills,
            "failed_fills": self.failed_fills,
            "success_rate": round(self.success_rate, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "avg_steps": round(self.avg_steps, 1),
            "best_duration_ms": round(self.best_duration_ms, 1) if self.best_duration_ms != float("inf") else None,
            "field_positions": {k: v.to_dict() for k, v in self.field_positions.items()},
            "last_attempt": self.last_attempt,
            "common_errors": self.common_errors[:5],
        }


class ComputerUseLearner:
    """Learns from form fill attempts and improves future performance.

    Usage:
        learner = ComputerUseLearner()
        learner.record_success(platform="outlier", task="fill form", fields=[...], positions=[...])
        learner.get_best_positions("outlier")  # → optimized field positions
    """

    def __init__(self, data_dir: str | Path | None = None):
        self._data_dir = Path(data_dir) if data_dir else Path("data/computer_use_learning")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._records_file = self._data_dir / "fill_records.jsonl"
        self._platforms_file = self._data_dir / "platform_learning.json"
        self._platforms: dict[str, PlatformLearning] = {}
        self._load_platforms()

    def _load_platforms(self) -> None:
        """Load platform learning data from disk."""
        if self._platforms_file.exists():
            try:
                data = json.loads(self._platforms_file.read_text())
                for pid, pdata in data.items():
                    fp_dict = pdata.get("field_positions", {})
                    field_positions = {k: FieldPosition(**v) for k, v in fp_dict.items()}
                    self._platforms[pid] = PlatformLearning(
                        platform=pid,
                        total_attempts=pdata.get("total_attempts", 0),
                        successful_fills=pdata.get("successful_fills", 0),
                        failed_fills=pdata.get("failed_fills", 0),
                        avg_duration_ms=pdata.get("avg_duration_ms", 0),
                        avg_steps=pdata.get("avg_steps", 0),
                        field_positions=field_positions,
                        last_attempt=pdata.get("last_attempt", 0),
                        best_duration_ms=pdata.get("best_duration_ms", float("inf")),
                        common_errors=pdata.get("common_errors", []),
                    )
            except Exception as exc:
                logger.warning("Failed to load platform learning: %s", exc)

    def _save_platforms(self) -> None:
        """Persist platform learning data."""
        data = {pid: pl.to_dict() for pid, pl in self._platforms.items()}
        self._platforms_file.write_text(json.dumps(data, indent=2))

    def _append_record(self, record: FillRecord) -> None:
        """Append a fill record to the JSONL log."""
        with open(self._records_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def record_success(
        self,
        platform: str,
        task: str,
        fields: list[dict[str, Any]],
        positions: list[FieldPosition] | None = None,
        duration_ms: float = 0.0,
        steps: int = 0,
        screenshots: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FillRecord:
        """Record a successful form fill."""
        import uuid

        record = FillRecord(
            id=f"fill_{uuid.uuid4().hex[:8]}",
            platform=platform,
            task=task,
            success=True,
            fields_filled=fields,
            field_positions=positions or [],
            duration_ms=duration_ms,
            steps_taken=steps,
            screenshots=screenshots or [],
            metadata=metadata or {},
        )

        self._append_record(record)
        self._update_platform(platform, record)

        logger.info(
            "[LEARNING] Recorded success for %s (%.0fms, %d steps)",
            platform,
            duration_ms,
            steps,
        )
        return record

    def record_failure(
        self,
        platform: str,
        task: str,
        error: str,
        duration_ms: float = 0.0,
        steps: int = 0,
        screenshots: list[str] | None = None,
    ) -> FillRecord:
        """Record a failed form fill."""
        import uuid

        record = FillRecord(
            id=f"fill_{uuid.uuid4().hex[:8]}",
            platform=platform,
            task=task,
            success=False,
            fields_filled=[],
            field_positions=[],
            duration_ms=duration_ms,
            steps_taken=steps,
            screenshots=screenshots or [],
            error=error,
        )

        self._append_record(record)
        self._update_platform(platform, record)

        logger.warning("[LEARNING] Recorded failure for %s: %s", platform, error)
        return record

    def _update_platform(self, platform: str, record: FillRecord) -> None:
        """Update platform learning aggregate."""
        if platform not in self._platforms:
            self._platforms[platform] = PlatformLearning(platform=platform)

        pl = self._platforms[platform]
        pl.total_attempts += 1
        pl.last_attempt = record.timestamp

        if record.success:
            pl.successful_fills += 1
            # Update average duration (running average)
            n = pl.successful_fills
            pl.avg_duration_ms = ((pl.avg_duration_ms * (n - 1)) + record.duration_ms) / n
            pl.avg_steps = ((pl.avg_steps * (n - 1)) + record.steps_taken) / n
            if record.duration_ms < pl.best_duration_ms:
                pl.best_duration_ms = record.duration_ms

            # Merge field positions
            for fp in record.field_positions:
                existing = pl.field_positions.get(fp.field_name)
                if existing:
                    # Update with better confidence
                    if fp.confidence > existing.confidence:
                        pl.field_positions[fp.field_name] = fp
                    existing.times_used += 1
                    existing.times_succeeded += 1
                    existing.confidence = min(1.0, existing.confidence + 0.05)
                else:
                    fp.times_used = 1
                    fp.times_succeeded = 1
                    pl.field_positions[fp.field_name] = fp
        else:
            pl.failed_fills += 1
            # Track common errors
            error_entry = {"error": record.error or "unknown", "timestamp": record.timestamp}
            pl.common_errors.append(error_entry)
            # Keep only last 10 errors
            pl.common_errors = pl.common_errors[-10:]

        self._save_platforms()

    def get_best_positions(self, platform: str) -> dict[str, FieldPosition]:
        """Get best known field positions for a platform."""
        pl = self._platforms.get(platform)
        if not pl:
            return {}
        # Filter to positions with >50% success rate
        return {k: v for k, v in pl.field_positions.items() if v.success_rate >= 0.5 and v.times_used >= 2}

    def get_platform_stats(self, platform: str) -> dict[str, Any] | None:
        """Get learning stats for a platform."""
        pl = self._platforms.get(platform)
        return pl.to_dict() if pl else None

    def get_all_stats(self) -> list[dict[str, Any]]:
        """Get learning stats for all platforms."""
        return [pl.to_dict() for pl in self._platforms.values()]

    def should_use_cached_positions(self, platform: str) -> bool:
        """Check if we have reliable cached positions for a platform."""
        positions = self.get_best_positions(platform)
        return len(positions) >= 2  # need at least 2 reliable positions

    def get_recommendation(self, platform: str) -> dict[str, Any]:
        """Get a recommendation for how to approach a platform.

        Returns advice based on historical performance.
        """
        pl = self._platforms.get(platform)
        if not pl or pl.total_attempts == 0:
            return {
                "platform": platform,
                "status": "no_data",
                "recommendation": "No historical data. Use default template.",
                "confidence": 0.0,
            }

        sr = pl.success_rate
        if sr >= 0.8:
            status = "reliable"
            rec = f"Platform is reliable ({sr:.0%} success rate). Use cached positions for faster fills."
        elif sr >= 0.5:
            status = "moderate"
            rec = f"Platform works moderately ({sr:.0%}). Verify positions before each fill."
        else:
            status = "unreliable"
            rec = f"Platform is unreliable ({sr:.0%}). Consider manual submission or template update."

        return {
            "platform": platform,
            "status": status,
            "recommendation": rec,
            "success_rate": round(sr, 3),
            "total_attempts": pl.total_attempts,
            "avg_duration_ms": round(pl.avg_duration_ms, 1),
            "best_duration_ms": round(pl.best_duration_ms, 1) if pl.best_duration_ms != float("inf") else None,
            "cached_positions": len(self.get_best_positions(platform)),
            "last_attempt": pl.last_attempt,
        }

    def get_records(self, platform: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Read fill records from the JSONL log."""
        if not self._records_file.exists():
            return []

        records = []
        with open(self._records_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if platform and record.get("platform") != platform:
                        continue
                    records.append(record)
                except json.JSONDecodeError:
                    continue

        # Return most recent first
        return sorted(records, key=lambda r: r.get("timestamp", 0), reverse=True)[:limit]


# ── Singleton ─────────────────────────────────────────────────────

_learner: ComputerUseLearner | None = None


def get_computer_use_learner(data_dir: str | Path | None = None) -> ComputerUseLearner:
    """Get or create the Computer Use learner singleton."""
    global _learner
    if _learner is None:
        _learner = ComputerUseLearner(data_dir)
    return _learner
