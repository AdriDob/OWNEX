from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("orion.copilot.orion_context")


class OrionContext:
    """Aggregates full ORION system context from multiple sources.

    Provides a unified snapshot of:
      - System health & state
      - Active targets & findings
      - Knowledge Graph recent activity
      - Unified Memory top entries
      - Event Store recent events
      - Scheduler status
      - Active investigations
    """

    def __init__(self, db_factory: Any | None = None) -> None:
        self._db = db_factory
        self._cache: dict[str, Any] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl = 30.0

    def set_db(self, db_factory: Any) -> None:
        self._db = db_factory

    def _build(self) -> dict[str, Any]:
        ctx: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "system": self._get_system_state(),
            "targets": self._get_active_targets(),
            "findings": self._get_findings_summary(),
            "memory": self._get_memory_snapshot(),
            "events": self._get_recent_events(),
            "scheduler": self._get_scheduler_status(),
        }
        return ctx

    def get_context(self, force_refresh: bool = False) -> dict[str, Any]:
        import time

        now = time.monotonic()
        if force_refresh or (now - self._cache_ts) > self._cache_ttl:
            self._cache = self._build()
            self._cache_ts = now
        return dict(self._cache)

    def _get_system_state(self) -> dict[str, Any]:
        try:
            from core.system_state import get_system_state

            s = get_system_state()
            return {
                "health_score": s.get("health_score", 0),
                "total_targets": s.get("total_targets", 0),
                "total_findings": s.get("total_findings", 0),
                "confirmed_findings": s.get("confirmed_findings", 0),
                "reports_this_month": s.get("reports_this_month", 0),
                "active_targets": s.get("active_targets", 0),
                "uptime_hours": s.get("uptime_hours", 0),
            }
        except Exception as exc:
            logger.debug("System state unavailable: %s", exc)
            return {"error": "unavailable"}

    def _get_active_targets(self) -> list[dict[str, Any]]:
        if not self._db:
            return []
        try:
            from database.models import Target

            session = self._db()
            targets = session.query(Target).filter(Target.status.in_(["active", "scanning"])).limit(10).all()
            result = [
                {"id": t.id, "name": t.name, "domain": getattr(t, "domain", ""), "status": t.status} for t in targets
            ]
            session.close()
            return result
        except Exception as exc:
            logger.debug("Targets unavailable: %s", exc)
            return []

    def _get_findings_summary(self) -> dict[str, Any]:
        if not self._db:
            return {}
        try:
            from database.models import Finding

            session = self._db()
            total = session.query(Finding).count()
            confirmed = session.query(Finding).filter(Finding.status == "confirmed").count()
            pending = session.query(Finding).filter(Finding.status.in_(["detected", "validated"])).count()
            rejected = session.query(Finding).filter(Finding.status == "rejected").count()
            session.close()
            return {"total": total, "confirmed": confirmed, "pending": pending, "rejected": rejected}
        except Exception as exc:
            logger.debug("Findings unavailable: %s", exc)
            return {}

    def _get_memory_snapshot(self) -> list[dict[str, Any]]:
        try:
            from core.memory.store import get_memory_store

            store = get_memory_store()
            entries = store.query(namespace="global", limit=5)
            return [
                {"key": e.get("key", ""), "content": e.get("content", "")[:200], "priority": e.get("priority", 0)}
                for e in entries
            ]
        except Exception as exc:
            logger.debug("Memory unavailable: %s", exc)
            return []

    def _get_recent_events(self) -> list[dict[str, Any]]:
        try:
            from cores.events.store import get_event_store

            store = get_event_store()
            events = store.query(limit=10)
            return [{"type": e.get("event_type", ""), "timestamp": e.get("timestamp", "")} for e in events]
        except Exception as exc:
            logger.debug("Event store unavailable: %s", exc)
            return []

    def _get_scheduler_status(self) -> dict[str, Any]:
        try:
            from api.scheduler import get_scheduler_status

            return get_scheduler_status()
        except Exception as exc:
            logger.debug("Scheduler status unavailable: %s", exc)
            return {"error": "unavailable"}

    def format_for_llm(self, force_refresh: bool = False) -> str:
        """Format context as a prompt-friendly string for LLM injection."""
        ctx = self.get_context(force_refresh)
        lines = ["## ORION System Context", f"Timestamp: {ctx['timestamp']}", ""]

        sys = ctx.get("system", {})
        if "error" not in sys:
            lines.append(
                f"Health: {sys.get('health_score', '?')}/100 | "
                f"Targets: {sys.get('total_targets', 0)} ({sys.get('active_targets', 0)} active) | "
                f"Findings: {sys.get('total_findings', 0)} ({sys.get('confirmed_findings', 0)} confirmed, "
                f"{sys.get('total_findings', 0) - sys.get('confirmed_findings', 0)} pending) | "
                f"Reports this month: {sys.get('reports_this_month', 0)}"
            )
            lines.append("")

        f = ctx.get("findings", {})
        if f:
            lines.append(
                f"Findings detail: {f.get('total', 0)} total, {f.get('confirmed', 0)} confirmed, "
                f"{f.get('pending', 0)} pending, {f.get('rejected', 0)} rejected"
            )
            lines.append("")

        targets = ctx.get("targets", [])
        if targets:
            lines.append("Active targets (" + str(len(targets)) + "):")
            for t in targets[:5]:
                lines.append(f"  - {t.get('name', '?')} ({t.get('domain', '?')}) [{t.get('status', '?')}]")
            lines.append("")

        memory = ctx.get("memory", [])
        if memory:
            lines.append("Recent memory:")
            for m in memory:
                lines.append(f"  - [{m.get('priority', 0):.1f}] {m.get('content', '')[:100]}")
            lines.append("")

        events = ctx.get("events", [])
        if events:
            lines.append("Recent events:")
            for e in events[:5]:
                lines.append(f"  - {e.get('type', '?')} @ {e.get('timestamp', '?')}")
            lines.append("")

        return "\n".join(lines)


_orion_context: OrionContext | None = None


def get_orion_context(db_factory: Any | None = None) -> OrionContext:
    global _orion_context
    if _orion_context is None:
        _orion_context = OrionContext(db_factory)
    return _orion_context
