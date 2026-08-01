"""Engagement memory — stores agent engagement outcomes for continuous learning."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

_ENGAGEMENTS: list[dict[str, Any]] = []
_LOCK = threading.Lock()
_MAX_ENGAGEMENTS = 10_000


def record_engagement_outcome(
    agent_id: str,
    engagement_data: dict[str, Any],
    success: bool,
    reward: float = 0.0,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Record an engagement outcome for an agent."""
    engagement_id = hashlib.sha1(
        f"{agent_id}:{time.time()}:{json.dumps(engagement_data, sort_keys=True, default=str)}".encode()
    ).hexdigest()[:12]
    record = {
        "id": f"eng_{engagement_id}",
        "agent_id": agent_id,
        "engagement_data": engagement_data,
        "success": bool(success),
        "reward": float(reward),
        "metadata": metadata or {},
        "recorded_at": time.time(),
    }
    with _LOCK:
        _ENGAGEMENTS.append(record)
        if len(_ENGAGEMENTS) > _MAX_ENGAGEMENTS:
            del _ENGAGEMENTS[: len(_ENGAGEMENTS) - _MAX_ENGAGEMENTS]
    return record["id"]


def find_similar_engagements(
    agent_id: str | None = None,
    target: str | None = None,
    action: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find similar past engagements."""
    with _LOCK:
        matches = []
        for rec in _ENGAGEMENTS:
            if agent_id is not None and rec["agent_id"] != agent_id:
                continue
            data = rec["engagement_data"]
            if target is not None and data.get("target") != target:
                continue
            if action is not None and data.get("action") != action:
                continue
            matches.append(rec)
        matches.sort(key=lambda r: r["recorded_at"], reverse=True)
        return matches[:limit]


def get_learning_stats(agent_id: str | None = None) -> dict[str, Any]:
    """Aggregate learning statistics."""
    with _LOCK:
        if agent_id is None:
            records = _ENGAGEMENTS
        else:
            records = [r for r in _ENGAGEMENTS if r["agent_id"] == agent_id]
        total = len(records)
        successes = sum(1 for r in records if r["success"])
        rewards = sum(r["reward"] for r in records)
        by_action: dict[str, dict[str, Any]] = {}
        for r in records:
            action = r["engagement_data"].get("action", "unknown")
            stats = by_action.setdefault(action, {"total": 0, "successes": 0, "failures": 0})
            stats["total"] += 1
            stats["successes"] += 1 if r["success"] else 0
            stats["failures"] += 0 if r["success"] else 1
        return {
            "total_engagements": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": (successes / total) if total else 0.0,
            "total_reward": rewards,
            "avg_reward": (rewards / total) if total else 0.0,
            "by_action": by_action,
            "last_recorded_at": records[-1]["recorded_at"] if records else None,
        }


def embed_engagement(engagement_data: dict[str, Any]) -> list[float]:
    """Lightweight deterministic embedding of an engagement for similarity search."""
    text = json.dumps(engagement_data, sort_keys=True, default=str).lower()
    vector = [0.0] * 64
    for i, ch in enumerate(text):
        vector[i % 64] += (ord(ch) % 128) / 128.0
    norm = sum(v * v for v in vector) ** 0.5 or 1.0
    return [v / norm for v in vector]
