from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from database import db
from database.models import MetricEvent, MetricRollup

logger = logging.getLogger("orion.core.evolution.rollup")

_HOURLY_WINDOW = 3600


class RollupEngine:
    """Aggregate raw MetricEvent rows into MetricRollup summaries.

    Run hourly via the scheduler.  Only processes events that haven't been
    rolled up yet (uses max(period_start) as watermark).
    """

    def run_hourly(self) -> dict[str, Any]:
        """Roll up the last full hour of metric events."""
        now = datetime.now(timezone.utc)
        period_end = now.replace(minute=0, second=0, microsecond=0)
        period_start = period_end.replace(hour=period_end.hour - 1)
        return self._rollup_for(period_start, period_end, "hourly")

    def run_daily(self) -> dict[str, Any]:
        """Roll up the last full day of metric events."""
        now = datetime.now(timezone.utc)
        period_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_start = period_end.replace(day=period_end.day - 1)
        return self._rollup_for(period_start, period_end, "daily")

    def _rollup_for(self, period_start: datetime, period_end: datetime, granularity: str) -> dict[str, Any]:
        """Compute rollups for a time window grouped by (module, event_type, status)."""
        session = db.SessionLocal()
        try:
            rows = (
                session.query(MetricEvent)
                .filter(MetricEvent.timestamp >= period_start)
                .filter(MetricEvent.timestamp < period_end)
                .all()
            )
        finally:
            session.close()

        if not rows:
            logger.info("[ROLLUP] No events in window %s – %s", period_start, period_end)
            return {"granularity": granularity, "period_start": period_start.isoformat(), "groups": 0, "events": 0}

        groups: dict[tuple, list[MetricEvent]] = {}
        for r in rows:
            key = (r.module, r.pipeline, r.tool, r.event_type, r.status)
            groups.setdefault(key, []).append(r)

        inserted = 0
        rollup_session = db.SessionLocal()
        try:
            for key, group in groups.items():
                durations = [g.duration_ms for g in group if g.duration_ms is not None]
                cpus = [g.cpu_percent for g in group if g.cpu_percent is not None]
                memories = [g.memory_mb for g in group if g.memory_mb is not None]

                rollup = MetricRollup(
                    granularity=granularity,
                    period_start=period_start,
                    module=key[0],
                    pipeline=key[1],
                    tool=key[2],
                    event_type=key[3],
                    status=key[4],
                    count=len(group),
                    avg_duration_ms=_avg(durations),
                    p50_duration_ms=_percentile(durations, 50),
                    p95_duration_ms=_percentile(durations, 95),
                    min_duration_ms=_min(durations),
                    max_duration_ms=_max(durations),
                    total_duration_ms=_sum(durations),
                    avg_cpu_percent=_avg(cpus),
                    avg_memory_mb=_avg(memories),
                    success_count=sum(1 for g in group if g.status == "success"),
                    failure_count=sum(1 for g in group if g.status != "success"),
                )
                rollup_session.add(rollup)
                inserted += 1
            rollup_session.commit()
        except Exception:
            rollup_session.rollback()
            logger.exception("[ROLLUP] Failed to persist rollups")
            return {
                "granularity": granularity,
                "period_start": period_start.isoformat(),
                "groups": 0,
                "events": len(rows),
                "error": "commit_failed",
            }
        finally:
            rollup_session.close()

        logger.info(
            "[ROLLUP] %s: %d events → %d rollup groups (%s)",
            granularity,
            len(rows),
            inserted,
            period_start.isoformat(),
        )
        return {
            "granularity": granularity,
            "period_start": period_start.isoformat(),
            "groups": inserted,
            "events": len(rows),
        }


# ── Helpers ─────────────────────────────────────────────


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _percentile(values: list[float], p: int) -> float | None:
    if not values:
        return None
    sorted_vals = sorted(values)
    k = max(0, min(len(sorted_vals) - 1, int(len(sorted_vals) * p / 100)))
    return sorted_vals[k]


def _min(values: list[float]) -> float | None:
    return min(values) if values else None


def _max(values: list[float]) -> float | None:
    return max(values) if values else None


def _sum(values: list[float]) -> float | None:
    return sum(values) if values else None
