"""Sistema de notificaciones inteligentes — niveles, prioridad, dedup, digest."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import IntEnum
from typing import Any

logger = logging.getLogger("orion.notifications.intelligent")


class DetailLevel(IntEnum):
    ESSENTIAL = 1
    NORMAL = 2
    DEBUG = 3


class Priority(IntEnum):
    LOW = 10
    MEDIUM = 50
    HIGH = 100
    CRITICAL = 200


@dataclass
class SmartNotification:
    id: str = ""
    event_type: str = ""
    title: str = ""
    body: str = ""
    priority: Priority = Priority.MEDIUM
    detail_level: DetailLevel = DetailLevel.NORMAL
    category: str = ""
    source: str = ""
    dedup_key: str = ""
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)


class IntelligentNotificationManager:
    """Gestor de notificaciones inteligentes con niveles, dedup semántico y digest."""

    def __init__(self, user_detail_level: DetailLevel = DetailLevel.NORMAL) -> None:
        self._user_level = user_detail_level
        self._history: list[SmartNotification] = []
        self._digest_queue: list[SmartNotification] = []
        self._dedup_cache: dict[str, float] = {}
        self._dedup_ttl = 300.0  # 5 min
        self._digest_interval = 3600.0  # 1 hour
        self._last_digest = time.time()
        self._total_suppressed = 0

    @property
    def user_level(self) -> DetailLevel:
        return self._user_level

    @user_level.setter
    def user_level(self, level: DetailLevel) -> None:
        self._user_level = level
        logger.info("User notification level set to %s", level.name)

    # ── Priority scoring ──

    def _compute_priority(self, event_type: str, data: dict[str, Any]) -> Priority:
        score_map: dict[str, Priority] = {
            "finding:confirmed": Priority.HIGH,
            "finding:created": Priority.MEDIUM,
            "report:accepted": Priority.CRITICAL,
            "report:generated": Priority.HIGH,
            "system:error": Priority.CRITICAL,
            "system:degraded": Priority.HIGH,
            "system:alert": Priority.CRITICAL,
            "revenue:payout_recorded": Priority.HIGH,
            "execution:workflow:failed": Priority.HIGH,
            "opportunity:found": Priority.MEDIUM,
            "quick_win:detected": Priority.HIGH,
            "hermes:security:blocked": Priority.CRITICAL,
            "copilot:recommendation": Priority.MEDIUM,
            "command:rejected": Priority.HIGH,
        }
        base = score_map.get(event_type, Priority.LOW)

        severity = data.get("severity", "")
        if severity in ("critical", "high"):
            base = Priority(max(int(base), int(Priority.HIGH)))

        confidence = data.get("confidence", 0)
        if confidence >= 0.8 and int(base) < int(Priority.CRITICAL):
            base = Priority.HIGH if int(base) < int(Priority.HIGH) else Priority.CRITICAL

        return base

    def _make_dedup_key(self, event_type: str, data: dict[str, Any]) -> str:
        key_parts = [event_type, data.get("title", ""), data.get("source", "")]
        dedup_source = data.get("dedup_key", "")
        if dedup_source:
            key_parts.append(dedup_source)
        return ":".join(str(p) for p in key_parts if p)

    def _is_duplicate(self, dedup_key: str) -> bool:
        if not dedup_key:
            return False
        now = time.time()
        last = self._dedup_cache.get(dedup_key)
        if last and (now - last) < self._dedup_ttl:
            return True
        self._dedup_cache[dedup_key] = now
        self._prune_dedup_cache()
        return False

    def _prune_dedup_cache(self) -> None:
        now = time.time()
        stale = [k for k, v in self._dedup_cache.items() if (now - v) > self._dedup_ttl]
        for k in stale:
            del self._dedup_cache[k]
        if len(self._dedup_cache) > 5000:
            sorted_items = sorted(self._dedup_cache.items(), key=lambda x: x[1])
            self._dedup_cache = dict(sorted_items[-2500:])

    # ── Process event ──

    def process_event(
        self,
        event_type: str,
        title: str,
        body: str = "",
        data: dict[str, Any] | None = None,
        override_level: DetailLevel | None = None,
    ) -> SmartNotification | None:
        data = data or {}
        priority = self._compute_priority(event_type, data)
        detail_level = override_level or self._user_level

        if priority < Priority.MEDIUM and detail_level < DetailLevel.NORMAL:
            self._total_suppressed += 1
            logger.debug("Suppressed low-priority notification: %s", event_type)
            return None

        dedup_key = self._make_dedup_key(event_type, data)
        if self._is_duplicate(dedup_key):
            self._total_suppressed += 1
            logger.debug("Suppressed duplicate: %s", dedup_key)
            return None

        notification = SmartNotification(
            id=f"n_{int(time.time() * 1000)}_{len(self._history)}",
            event_type=event_type,
            title=title,
            body=body,
            priority=priority,
            detail_level=detail_level,
            category=data.get("category", "general"),
            source=data.get("source", "system"),
            dedup_key=dedup_key,
            timestamp=time.time(),
            data=data,
        )

        self._history.append(notification)
        if len(self._history) > 500:
            self._history = self._history[-500:]

        return notification

    def route_to_user(self, notification: SmartNotification) -> dict[str, Any] | None:
        if notification.priority >= Priority.HIGH or notification.detail_level <= self._user_level:
            return self._format_for_user(notification)
        if self._user_level < DetailLevel.NORMAL:
            self._digest_queue.append(notification)
            return None
        return self._format_for_user(notification)

    def _format_for_user(self, n: SmartNotification) -> dict[str, Any]:
        emoji_map = {
            "finding": "🔍",
            "report": "📝",
            "system": "🖥",
            "revenue": "💰",
            "execution": "⚡",
            "opportunity": "🎯",
            "hermes": "🤖",
            "copilot": "🧠",
            "command": "⌨",
        }
        category_emoji = "ℹ️"
        for key, emoji in emoji_map.items():
            if n.event_type.startswith(key):
                category_emoji = emoji
                break
        if n.priority == Priority.CRITICAL:
            category_emoji = "🚨"
        elif n.priority == Priority.HIGH:
            category_emoji = "⚠️"

        return {
            "id": n.id,
            "emoji": category_emoji,
            "title": n.title,
            "body": n.body,
            "priority": n.priority.name.lower(),
            "event_type": n.event_type,
            "timestamp": datetime.fromtimestamp(n.timestamp, tz=UTC).isoformat(),
            "data": n.data,
        }

    # ── Digest ──

    def maybe_send_digest(self, force: bool = False) -> list[dict[str, Any]] | None:
        now = time.time()
        if not force and (now - self._last_digest) < self._digest_interval:
            return None
        if not self._digest_queue:
            return None

        self._last_digest = now
        grouped: dict[str, list[SmartNotification]] = {}
        for n in self._digest_queue:
            grouped.setdefault(n.category, []).append(n)

        digest: list[dict[str, Any]] = []
        for category, notifications in grouped.items():
            digest.append(
                {
                    "category": category,
                    "count": len(notifications),
                    "notifications": [self._format_for_user(n) for n in notifications[:5]],
                    "total_suppressed": len(notifications),
                }
            )

        self._digest_queue.clear()
        return digest

    # ── Stats ──

    def get_stats(self) -> dict[str, Any]:
        return {
            "user_level": self._user_level.name,
            "history_count": len(self._history),
            "digest_queue_size": len(self._digest_queue),
            "total_suppressed": self._total_suppressed,
            "dedup_cache_size": len(self._dedup_cache),
            "last_digest": datetime.fromtimestamp(self._last_digest, tz=UTC).isoformat(),
        }

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return [self._format_for_user(n) for n in self._history[-limit:]]


_INTELLIGENT: IntelligentNotificationManager | None = None


def get_intelligent_notifier() -> IntelligentNotificationManager:
    global _INTELLIGENT
    if _INTELLIGENT is None:
        _INTELLIGENT = IntelligentNotificationManager()
    return _INTELLIGENT
