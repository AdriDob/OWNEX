"""Daily Operation Mode API — the GOOD MORNING consolidated panel.

Single morning call answering the protocol:

    System: Ready
    Important tasks:
    Opportunities found:
    Improvements suggested:
    Pending approvals:

Reuses every existing engine — nothing duplicated:
- StabilityGuardian (api/routers/stability) → system status
- UnifiedMemoryStore (core/memory)          → memory stats
- WorkBank (cores/direct_work_engine)       → unfinished work + production targets
- DailyBrief endpoint logic                 → top opportunity
- SourceIntelEngine                         → best sources for the next hour
- SkillEvolutionEngine/CapabilityExpansionDetector → improvements
- WearOSIntegration (cores/wear_os)        → pending approvals
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter

from api.routers.stability import stability_status
from core.memory.store import get_memory_store
from cores.direct_work_engine.models import UserProfile
from cores.direct_work_engine.source_intel import SourceIntelEngine
from cores.direct_work_engine.workbank import get_workbank
from cores.wear_os.integration import get_wear_os_integration

logger = logging.getLogger("orion.daily_mode")

router = APIRouter(prefix="/api/system", tags=["daily-operation"])


def _memory_stats() -> dict[str, Any]:
    try:
        store = get_memory_store()
        stats = store.get_stats()
        # El store devuelve "namespaces" como int (distinct count); el panel lo consume como dict.
        raw_ns = stats.get("namespaces", {})
        ns = raw_ns if isinstance(raw_ns, dict) else {}
        return {
            "healthy": True,
            "entries": stats.get("total_entries", 0),
            "namespaces": ns,
            "namespace_count": raw_ns if isinstance(raw_ns, int) else len(ns),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory stats unavailable: %s", exc)
        return {"healthy": False, "entries": 0, "namespaces": {}, "namespace_count": 0}


def _unfinished_work() -> dict[str, Any]:
    try:
        bank = get_workbank()
        ready = bank.best_ready(limit=5)
        needs_access = bank.needs_access()
        progress = bank.progress() if hasattr(bank, "progress") else {}
        return {
            "ready_to_deliver": [{"title": i.title, "platform": i.platform, "reward": i.reward} for i in ready],
            "needs_access": [
                {"title": i.title, "platform": i.platform, "requirement": i.requirement} for i in needs_access[:5]
            ],
            "targets": progress,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Work bank unavailable: %s", exc)
        return {"ready_to_deliver": [], "needs_access": [], "targets": {}}


def _opportunities() -> dict[str, Any]:
    try:
        radar = SourceIntelEngine().analyze()
        top = [s for s in radar["sources"] if s["recommendation"] == "DISCOVER"][:5]
        return {
            "scanned_sources": radar["total_curated_sources"],
            "best_sources": [
                {
                    "name": s["name"],
                    "category": s["category"],
                    "trust_score": s["trust_score"],
                    "earning_potential": s["earning_potential"],
                }
                for s in top
            ],
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Opportunity radar unavailable: %s", exc)
        return {"scanned_sources": 0, "best_sources": []}


def _improvements() -> list[dict[str, Any]]:
    """Highest-value improvement suggestions from the evolution layer."""
    try:
        profile = UserProfile(
            name="Adriel",
            country="Argentina",
            languages=["es", "en"],
            skills=["python", "go", "unity", "typescript"],
            remote_only=True,
        )
        from cores.direct_work_engine.evolution import CapabilityExpansionDetector, SkillEvolutionEngine

        lessons = SkillEvolutionEngine().learn_from_lost([], profile)
        proposals = CapabilityExpansionDetector().detect([], profile)
        out: list[dict[str, Any]] = []
        for p in proposals:
            out.append({"type": "capability", "name": p.name, "benefit": p.benefit, "priority": p.priority})
        for lsn in lessons[:3]:
            out.append({"type": "lesson", "name": lsn.category, "reason": lsn.reason, "priority": lsn.priority})
        return out[:6]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Improvements unavailable: %s", exc)
        return []


def _pending_approvals() -> list[dict[str, Any]]:
    try:
        integration = get_wear_os_integration()
        return [
            {"id": a.request_id, "message": a.message, "level": a.level.value if hasattr(a.level, "value") else a.level}
            for a in integration.get_pending_approvals()
        ]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Approvals unavailable: %s", exc)
        return []


def _setup_progress() -> dict[str, Any]:
    """Configuración progresiva: % completo + UNA tarea de config para hoy."""
    try:
        from core.setup.checklist import get_setup_checklist

        status = get_setup_checklist().status()
        return {
            "complete_pct": status["complete_pct"],
            "complete": status["complete"],
            "next_task": status["next_task"],
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Setup progress unavailable: %s", exc)
        return {"complete_pct": 0, "complete": False, "next_task": None}


@router.get("/good-morning")
def good_morning() -> dict[str, Any]:
    """GOOD MORNING — the single daily panel (protocol DAILY OPERATION MODE)."""

    def _safe(fn) -> Any:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Daily panel section failed: %s", exc)
            return None

    status = _safe(stability_status) or {}
    system = status.get("system", {})
    memory = _safe(_memory_stats) or {"healthy": False, "entries": 0, "namespaces": {}, "namespace_count": 0}
    work = _safe(_unfinished_work) or {"ready_to_deliver": [], "needs_access": [], "targets": {}}
    opps = _safe(_opportunities) or {"scanned_sources": 0, "best_sources": []}
    improvements = _safe(_improvements) or []
    approvals = _safe(_pending_approvals) or []
    setup = _safe(_setup_progress) or {"complete_pct": 0, "complete": False, "next_task": None}

    system_status = system.get("status", "unknown")
    system_score = system.get("score", 0)
    important_tasks = work["ready_to_deliver"] + work["needs_access"]
    summary_lines = [
        f"System: {'Ready' if system_status == 'ok' else system_status.upper()} (score {system_score}/100).",
        f"Memory: {memory['entries']} entries across {memory['namespace_count']} namespaces."
        if memory["healthy"]
        else "Memory: check failed.",
        f"Opportunities: {opps['scanned_sources']} sources scanned, {len(opps['best_sources'])} DISCOVER for today.",
        f"Unfinished work: {len(work['ready_to_deliver'])} ready to deliver, {len(work['needs_access'])} need access.",
        f"Improvements suggested: {len(improvements)}.",
        f"Pending approvals: {len(approvals)}.",
    ]
    next_task = setup.get("next_task")
    if next_task:
        summary_lines.append(
            f"Setup {setup['complete_pct']}% — today's config task: {next_task['title']} ({next_task['est_minutes']} min)."
        )

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "summary": " ".join(summary_lines),
        "system": {"status": system_status, "score": system_score},
        "memory": memory,
        "important_tasks": important_tasks,
        "opportunities": opps,
        "unfinished_work": work,
        "improvements_suggested": improvements,
        "pending_approvals": approvals,
        "setup_progress": setup,
    }
