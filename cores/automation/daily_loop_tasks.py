"""Daily Loop tasks — entry segura para el scheduler."""

from __future__ import annotations

import logging

logger = logging.getLogger("ownex.daily_loop_tasks")


def run_daily_loop_scheduler() -> dict:
    """Corre el daily loop (SELECT→PREPARE→GATE) y reporta. Nunca raisea."""
    try:
        from cores.automation.daily_loop import run_daily_loop

        total_minutes = 240  # default 4h/utilidad
        res = run_daily_loop(total_minutes=total_minutes)
        out = res.to_dict()
        out["scheduled_by"] = "daily_loop_run"
        return out
    except Exception as exc:
        logger.warning("[DAILY-LOOP-scheduler] fallo: %s", exc)
        return {"error": str(exc), "selected": [], "parked_gated": [], "scheduled_by": "daily_loop_run"}
