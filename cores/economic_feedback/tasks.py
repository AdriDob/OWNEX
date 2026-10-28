"""Economic Feedback tasks — scheduled recalibration."""

from __future__ import annotations

import logging

logger = logging.getLogger("ownex.economic_feedback.tasks")


def run_economic_feedback() -> dict:
    """Daily LEARN→RECALIBRATE→REALLOCATE. Persists snapshot, logs reallocation hint."""
    try:
        from cores.economic_feedback.engine import build_snapshot, persist_snapshot

        snap = build_snapshot()
        path = persist_snapshot(snap)
        hint = snap.reallocation
        logger.info(
            "[ECONOMIC-FEEDBACK] total_paid=%d total_net=%.2f global_nph=%s reallocation=%s → %s",
            snap.total_paid,
            snap.total_net,
            snap.global_net_per_hour,
            hint,
            path,
        )
        return {"success": True, "snapshot": snap.to_dict(), "path": str(path)}
    except Exception as exc:
        logger.warning("run_economic_feedback failed: %s", exc)
        return {"success": False, "error": str(exc)}
