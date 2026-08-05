"""
OWNEX Daily Cycle — Morning briefing when you turn on the PC.

Shows:
- System status: OK/Degraded
- Tasks pending: 8
- Opportunities analyzed: 14
- Recommended improvement: Update module X
- Potential time saved: 3 hours
- Priority order chosen
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from cores.ai.runtime import get_oar
from cores.memory.system import MemoryNamespace, MemoryTier, get_learning_engine, get_memory_store
from cores.opportunity.engine import get_opportunity_engine
from cores.tools.system import get_compatibility_checker, get_tool_manager

logger = logging.getLogger("ownex.daily_cycle")


@dataclass
class SystemHealth:
    status: str  # "healthy", "degraded", "unhealthy"
    score: int  # 0-100
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DailyBriefing:
    generated_at: datetime
    greeting: str
    system: SystemHealth
    tasks_pending: int
    opportunities_analyzed: int
    top_opportunities: list[dict[str, Any]] = field(default_factory=list)
    recommended_improvement: str | None = None
    time_saved_estimate_hours: float = 0.0
    priority_order: list[str] = field(default_factory=list)
    weather: str | None = None


class SystemHealthChecker:
    """Checks overall system health."""

    def __init__(self):
        self.tool_manager = get_tool_manager()
        self.compat_checker = get_compatibility_checker()

    async def check(self) -> SystemHealth:
        score = 100
        details = {}

        # Tool compatibility
        compat = await self.compat_checker.full_compatibility_check()
        details["tools"] = compat
        if not compat["compatible"]:
            score -= 20
        elif compat["warnings"]:
            score -= 10

        # Memory health
        memory = get_memory_store()
        mem_stats = memory.get_stats()
        details["memory"] = mem_stats
        if mem_stats["total"] > 10000:
            score -= 5

        # Database connectivity
        try:
            from database import db

            session = db.SessionLocal()
            session.execute("SELECT 1")
            session.close()
            details["database"] = "connected"
        except Exception as e:
            details["database"] = f"error: {e}"
            score -= 30

        # AI providers
        try:
            oar = get_oar()
            if oar._initialized:
                health = oar._health.get_all_health() if oar._health else {}
                healthy_count = sum(1 for h in health.values() if h.get("status") == "healthy")
                total_count = len(health)
                if total_count > 0:
                    ai_score = (healthy_count / total_count) * 100
                    score = int(score * 0.7 + ai_score * 0.3)
                details["ai_providers"] = {"healthy": healthy_count, "total": total_count}
            else:
                details["ai_providers"] = "not_initialized"
                score -= 10
        except Exception as e:
            details["ai_providers"] = f"error: {e}"
            score -= 15

        if score >= 85:
            status = "healthy"
        elif score >= 60:
            status = "degraded"
        else:
            status = "unhealthy"

        return SystemHealth(status=status, score=max(0, score), details=details)


class TaskAnalyzer:
    """Analyzes pending tasks and opportunities."""

    def __init__(self):
        self.memory = get_memory_store()
        self.opportunity_engine = get_opportunity_engine()

    async def get_pending_tasks(self) -> int:
        tasks = self.memory.list(MemoryNamespace.TASK_OUTCOMES)
        pending = 0
        for entry in tasks:
            stats = entry.value
            if stats.get("total", 0) > stats.get("successful", 0):
                pending += 1
        return pending

    async def get_opportunities_analyzed(self) -> int:
        opps = self.memory.list(MemoryNamespace.OPPORTUNITIES)
        recent_cutoff = datetime.now(UTC) - timedelta(days=1)
        count = 0
        for entry in opps:
            try:
                created = datetime.fromisoformat(entry.metadata.get("created_at", ""))
                if created > recent_cutoff:
                    count += 1
            except Exception:
                pass
        return count

    async def get_top_opportunities(self, limit: int = 5) -> list[dict[str, Any]]:
        opps = self.memory.list(MemoryNamespace.OPPORTUNITIES, tag="ranked")
        ranked = []
        for entry in opps:
            ranked.append(
                {
                    "id": entry.key,
                    "title": entry.value.get("title", entry.key),
                    "score": entry.value.get("score", 0),
                    "reward_per_hour": entry.value.get("reward_per_hour", 0),
                    "match_score": entry.value.get("match_score", 0),
                }
            )
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:limit]


class ImprovementRecommender:
    """Recommends system improvements."""

    def __init__(self):
        self.learning = get_learning_engine()

    async def get_recommendation(self) -> str | None:
        compat = await get_compatibility_checker().full_compatibility_check()
        if compat["issues"]:
            return f"Install missing required tools: {', '.join([i.split(' ')[-1] for i in compat['issues']])}"
        if compat["warnings"]:
            return f"Update outdated tools: {', '.join([w.split(' ')[1] for w in compat['warnings']])}"

        patterns = self.learning.infer_user_patterns()
        tool_prefs = patterns.get("tool_preferences", {})
        for tool, stats in tool_prefs.items():
            if stats.get("uses", 0) > 5 and stats.get("success_rate", 1) < 0.7:
                return f"Improve {tool} usage (success rate: {stats['success_rate']:.0%})"

        task_patterns = patterns.get("task_patterns", {})
        for task, stats in task_patterns.items():
            if stats.get("total", 0) > 10 and stats.get("success_rate", 1) < 0.8:
                return f"Optimize {task} workflow (success rate: {stats['success_rate']:.0%})"

        return "Review and update tool configurations for better automation"


class TimeSavingsEstimator:
    """Estimates potential time savings from automation."""

    def __init__(self):
        self.learning = get_learning_engine()

    def estimate(self) -> float:
        patterns = self.learning.infer_user_patterns()
        task_patterns = patterns.get("task_patterns", {})

        total_hours = 0.0
        for task, stats in task_patterns.items():
            total_tasks = stats.get("total", 0)
            avg_duration = stats.get("avg_duration_ms", 0) / 1000 / 60
            success_rate = stats.get("success_rate", 1)
            if success_rate > 0.8 and total_tasks > 5:
                weekly_tasks = total_tasks / 4
                automatable_time = weekly_tasks * avg_duration * 0.6
                total_hours += automatable_time / 60

        total_hours += 1.5
        return round(total_hours, 1)


class PriorityOrderer:
    """Determines priority order for the day."""

    PRIORITY_CATEGORIES = [
        "Auditoría",
        "Estabilidad",
        "GitHub",
        "Núcleo asistente",
        "Memoria",
        "Guided Mode",
        "Opportunity Engine",
        "Herramientas",
        "Diseño",
        "Rutina diaria",
    ]

    def __init__(self):
        self.learning = get_learning_engine()

    def get_order(self) -> list[str]:
        patterns = self.learning.infer_user_patterns()
        task_patterns = patterns.get("task_patterns", {})

        scored = []
        for category in self.PRIORITY_CATEGORIES:
            score = 0
            base = len(self.PRIORITY_CATEGORIES) - self.PRIORITY_CATEGORIES.index(category)
            score += base * 10
            for task, stats in task_patterns.items():
                if category.lower() in task.lower() or task.lower() in category.lower():
                    score += stats.get("total", 0) * 2
            scored.append((category, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in scored]


class DailyCycleEngine:
    """Main daily cycle engine."""

    def __init__(self):
        self.health_checker = SystemHealthChecker()
        self.task_analyzer = TaskAnalyzer()
        self.improvement_recommender = ImprovementRecommender()
        self.time_estimator = TimeSavingsEstimator()
        self.priority_orderer = PriorityOrderer()
        self.memory = get_memory_store()

    async def generate_briefing(self) -> DailyBriefing:
        system, pending_tasks, opps_analyzed, top_opps, improvement, time_saved, priority = await asyncio.gather(
            self.health_checker.check(),
            self.task_analyzer.get_pending_tasks(),
            self.task_analyzer.get_opportunities_analyzed(),
            self.task_analyzer.get_top_opportunities(5),
            self.improvement_recommender.get_recommendation(),
            asyncio.get_event_loop().run_in_executor(None, self.time_estimator.estimate),
            asyncio.get_event_loop().run_in_executor(None, self.priority_orderer.get_order),
        )

        hour = datetime.now().hour
        if hour < 12:
            greeting = "Buenos días"
        elif hour < 18:
            greeting = "Buenas tardes"
        else:
            greeting = "Buenas noches"

        briefing = DailyBriefing(
            generated_at=datetime.now(UTC),
            greeting=greeting,
            system=system,
            tasks_pending=pending_tasks,
            opportunities_analyzed=opps_analyzed,
            top_opportunities=top_opps,
            recommended_improvement=improvement,
            time_saved_estimate_hours=time_saved,
            priority_order=priority,
        )

        self.memory.set(
            MemoryNamespace.SYSTEM_HEALTH,
            f"briefing_{datetime.now(UTC).date().isoformat()}",
            {
                "greeting": greeting,
                "system_status": system.status,
                "system_score": system.score,
                "tasks_pending": pending_tasks,
                "opportunities_analyzed": opps_analyzed,
                "time_saved_hours": time_saved,
                "priority_order": priority,
            },
            tier=MemoryTier.PERMANENT,
            tags=["daily_briefing", "morning"],
        )

        return briefing

    def format_briefing(self, briefing: DailyBriefing) -> str:
        status_emoji = {"healthy": "✅", "degraded": "⚠️", "unhealthy": "❌"}
        status_icon = status_emoji.get(briefing.system.status, "❓")

        lines = [
            f"{briefing.greeting}.",
            "",
            f"Sistema: {status_icon} {briefing.system.status.upper()} ({briefing.system.score}/100)",
            f"Tareas: {briefing.tasks_pending}",
            f"Oportunidades: {briefing.opportunities_analyzed} analizadas",
        ]

        if briefing.recommended_improvement:
            lines.append(f"Mejora recomendada: {briefing.recommended_improvement}")

        lines.append(f"Tiempo potencial ahorrado: {briefing.time_saved_estimate_hours} horas")
        lines.append("")
        lines.append("Orden de prioridad que elegiría:")
        for i, p in enumerate(briefing.priority_order[:7], 1):
            lines.append(f"  {i}. {p}")

        return "\n".join(lines)


_daily_engine: DailyCycleEngine | None = None


def get_daily_engine() -> DailyCycleEngine:
    global _daily_engine
    if _daily_engine is None:
        _daily_engine = DailyCycleEngine()
    return _daily_engine


async def run_daily_cycle() -> DailyBriefing:
    engine = get_daily_engine()
    return await engine.generate_briefing()


async def get_morning_briefing() -> str:
    briefing = await run_daily_cycle()
    engine = get_daily_engine()
    return engine.format_briefing(briefing)
