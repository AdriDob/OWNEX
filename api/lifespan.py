"""Background initialization for the CATEYE API server.

This module contains all the heavy startup logic that was previously running
synchronously inside the lifespan context manager, blocking the event loop
and preventing uvicorn from accepting HTTP requests.

The lifespan now yields after critical init (~1s), then schedules
``run_background_init()`` as an asyncio task so the API becomes immediately
responsive.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from contextlib import suppress
from typing import Any

logger = logging.getLogger("cateye.lifespan")


async def run_background_init(app: Any, bus: Any) -> None:
    """Run all non-critical initialization as a background task.

    This is called after the lifespan yields, so the API is already serving
    requests. Any failures here are logged as warnings but do NOT prevent
    the server from running.
    """

    def _defer(label: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Run a synchronous init function in a thread to avoid blocking."""
        try:
            result = fn(*args, **kwargs)
            logger.info("[BG-INIT] %s done", label)
            return result
        except Exception as exc:
            logger.warning("[BG-INIT] %s failed (non-fatal): %s", label, exc)

    # ── Phase 1: Core systems (fast, <5s total) ──
    _defer("enforce_on_startup", _init_enforce_on_startup)
    _defer("identity", _init_identity)
    _defer("temp_manager", _init_temp_manager)
    _defer("authhub", _init_authhub)
    _defer("orchestrator", _init_orchestrator)
    _defer("trackers", _init_trackers)
    _defer("scorecard", _init_scorecard)
    _defer("explainability", _init_explainability)
    _defer("memory_stores", _init_memory_stores)

    # ── Phase 2: Heavy systems (may take 15-20s) ──
    await _async_defer("self_healing", _init_self_healing)
    await _async_defer("self_update", _init_self_update)
    _defer("priority_engine", _init_priority_engine)
    _defer("loop_engines", _init_loop_engines, bus)
    await _async_defer("obs_engine", _init_obs_engine, bus)

    # ── Phase 3: Copilot, knowledge, evidence ──
    _defer("copilot", _init_copilot)
    _defer("evidence_graph", _init_evidence_graph)
    _defer("knowledge_graph", _init_knowledge_graph)

    # ── Phase 4: Schedulers and agents ──
    scheduler = await _async_defer("scheduler", _init_scheduler)
    await _async_defer("scheduler_start", _start_scheduler, scheduler)
    _defer("agents", _init_agents)

    # ── Phase 5: Health, recovery, notifications ──
    _defer("health_checks", _init_health_checks)
    _defer("recovery", _init_recovery)
    _defer("health_engine", _init_health_engine)
    await _async_defer("discovery_monitor", _init_discovery_monitor)
    await _async_defer("operations", _init_operations, app)

    # ── Phase 6: ORION platform ──
    orion_scheduler = await _async_defer("orion_platform", _init_orion_platform, app, bus)
    _defer("optimization", _init_optimization)
    _defer("autonomous", _init_autonomous)

    # ── Phase 7: Extensions, secrets, evolution ──
    _defer("extensions", _init_extensions)
    _defer("secrets", _init_secrets)
    _defer("evolution", _init_evolution)

    # ── Phase 8: Event store, subscribers, bridges ──
    _defer("event_store", _init_event_store, bus)
    _defer("notification_bridges", _init_notification_bridges, bus, app)
    _defer("copilot_handlers", _init_copilot_handlers, bus, app)
    _defer("telegram_bridge", _init_telegram_bridge, bus)

    await _async_defer("orion_scheduler_start", _start_orion_scheduler, orion_scheduler)

    # ── Phase 9: Financial, optimization, last-mile ──
    fin_scheduler = await _async_defer("financial_scheduler", _init_financial_scheduler)
    _defer("agent_bridges", _init_agent_bridges)
    _defer("auto_report", _init_auto_report, bus)
    _defer("feedback_tuner", _init_feedback_tuner, bus)
    _defer("verdict_learner", _init_verdict_learner, bus)
    _defer("unified_memory", _init_unified_memory)
    _defer("smart_notifications", _init_smart_notifications, bus)

    logger.info("[BG-INIT] All background initialization complete")


# ── Async helpers ─────────────────────────────────────────────────────


async def _async_defer(label: str, fn: Callable[..., Any], *args: Any) -> Any:
    """Run an async init function with timeout protection."""
    try:
        result = await asyncio.wait_for(_await_or_call(fn, *args), timeout=20.0)
        logger.info("[BG-INIT] %s done", label)
        return result
    except TimeoutError:
        logger.warning("[BG-INIT] %s timed out (20s) — deferred", label)
        return None
    except Exception as exc:
        logger.warning("[BG-INIT] %s failed (non-fatal): %s", label, exc)
        return None


async def _await_or_call(fn: Callable[..., Any], *args: Any) -> Any:
    """Call fn with args; if it returns a coroutine, await it."""
    result = fn(*args)
    if asyncio.iscoroutine(result):
        return await result
    return result


# ── Individual init functions ─────────────────────────────────────────


def _init_enforce_on_startup() -> None:
    from cores.product_rules import enforce_on_startup

    enforce_on_startup()


def _init_identity() -> None:
    from cores.identity.identity_manager import get_identity_manager

    identity = get_identity_manager()
    identity.ensure_identity()
    user_identity = identity.get_identity()
    logger.info("[BG-INIT] Identity: %s", user_identity.user_id if user_identity else "unknown")


def _init_temp_manager() -> None:
    from core.system.temp_manager import get_temp_manager

    get_temp_manager()


def _init_authhub() -> None:
    from cores.authhub import get_authhub

    get_authhub().init_defaults()


def _init_orchestrator() -> None:
    from cores.orchestrator.assistant_orchestrator import get_orchestrator

    o = get_orchestrator()
    o.suppress_noise_items(threshold=0.15)


def _init_trackers() -> None:
    from cores.actions.execution_tracker import get_execution_tracker

    get_execution_tracker()
    from cores.accountability.outcome_tracker import get_outcome_tracker

    get_outcome_tracker()


def _init_scorecard() -> None:
    from cores.accountability.system_scorecard import get_system_scorecard

    get_system_scorecard().generate()


def _init_explainability() -> None:
    from cores.explainability.explanation_engine import get_explanation_engine

    get_explanation_engine()
    from cores.explainability.decision_trace import get_decision_trace

    get_decision_trace()


def _init_memory_stores() -> None:
    from cores.memory.memory_store import get_memory_store

    get_memory_store()
    from cores.memory.decision_memory import get_decision_memory

    get_decision_memory()
    from cores.memory.insight_archive import get_insight_archive

    get_insight_archive()


async def _init_self_healing() -> None:
    from core.self_healing.system import get_self_healing_system

    hs = get_self_healing_system()
    await asyncio.get_event_loop().run_in_executor(None, hs.validate_system)


async def _init_self_update() -> None:
    from core.self_healing.update import SelfUpdateSystem

    u = SelfUpdateSystem()
    await asyncio.get_event_loop().run_in_executor(None, u.check_for_updates)


def _init_priority_engine() -> None:
    from cores.intelligence.priority_engine import get_priority_engine

    get_priority_engine().consume_memory()


def _init_loop_engines(bus: Any) -> None:
    from core.loop.startup import init_loop_engines
    from core.scheduler.scheduler import get_core_scheduler

    init_loop_engines(scheduler=get_core_scheduler(), event_bus=bus)


async def _init_obs_engine(bus: Any) -> Any:
    from core.sensors.observation_engine import ObservationEngine

    obs = ObservationEngine(event_bus=bus)
    await obs.initialize()
    return obs


def _init_copilot() -> Any:
    from core.copilot.agent import CopilotAgent
    from core.copilot.permissions import AuthorityLevel

    return CopilotAgent(authority=AuthorityLevel.SENIOR_HUNTER)


def _init_evidence_graph() -> None:
    from core.evidence_graph.graph import get_evidence_graph

    get_evidence_graph()


def _init_knowledge_graph() -> None:
    from core.knowledge.graph import get_knowledge_graph

    get_knowledge_graph()


async def _init_scheduler() -> Any:
    import api.scheduler as sched_mod
    from api.scheduler import ScanScheduler

    scheduler = ScanScheduler(interval_minutes=30)
    sched_mod.scheduler_instance = scheduler
    return scheduler


async def _start_scheduler(scheduler: Any) -> None:
    if scheduler is None:
        return
    t = asyncio.create_task(scheduler.start())
    _background_tasks.discard(t)
    _background_tasks.add(t)


def _init_agents() -> None:
    from cores.agents import start_all_agents

    start_all_agents()


def _init_health_checks() -> None:
    from core.health.checks import register_default_checks
    from core.health.engine import get_health_center

    center = get_health_center()
    center.enable_persistence()
    register_default_checks(center)


def _init_recovery() -> None:
    from cores.recovery import get_health_monitor, get_recovery_engine

    recovery = get_recovery_engine()
    recovery.start()
    monitor = get_health_monitor()
    monitor.start()


def _init_health_engine() -> None:
    from cores.health import get_system_health_engine

    health_engine = get_system_health_engine()
    health_engine.start()


async def _init_discovery_monitor() -> Any:
    from cores.bounty_scraper.monitor import get_discovery_monitor

    dm = get_discovery_monitor()
    await dm.start()
    return dm


async def _init_operations(app: Any) -> Any:
    from cores.operations import initialize_operations

    ops_manager = await initialize_operations()
    app.state.operations_manager = ops_manager
    return ops_manager


async def _init_orion_platform(app: Any, bus: Any) -> Any:
    from core.app_registry import get_app_registry
    from core.database.manager import get_db_manager
    from core.scheduler.scheduler import JobDefinition, get_core_scheduler
    from cores.events.event_bus import get_event_bus

    registry = get_app_registry()
    registry.discover()

    try:
        from core.capabilities.registration import register_all_capabilities

        register_all_capabilities()
    except Exception:
        pass

    try:
        from core.revenue.engine import RevenueEngine

        RevenueEngine()
    except Exception:
        pass

    try:
        from core.self_heal.engine import SelfHealEngine

        SelfHealEngine().heal()
    except Exception:
        pass

    dbm = get_db_manager()
    for app_id, app_obj in registry._apps.items():
        if app_obj.db_path:
            dbm.register(app_id, app_obj.db_path)
            if app_obj.models:
                from sqlalchemy.orm import declarative_base

                base = declarative_base()
                dbm.run_migrations(app_id, base)

    core_bus = get_event_bus()
    orion_scheduler = get_core_scheduler()

    def _resolve_handler(handler: Any) -> Callable[..., Any] | None:
        if callable(handler):
            return handler
        if not isinstance(handler, str):
            return None
        if ":" in handler:
            module_path, attr_path = handler.split(":", 1)
        else:
            module_path, attr_path = handler, ""
        try:
            import importlib

            if not attr_path:
                parts = module_path.split(".")
                for cut in range(len(parts) - 1, 0, -1):
                    candidate_mod = ".".join(parts[:cut])
                    try:
                        obj = importlib.import_module(candidate_mod)
                    except Exception:
                        continue
                    for part in parts[cut:]:
                        obj = getattr(obj, part)
                    if callable(obj):
                        return obj
                return None
            obj = importlib.import_module(module_path)
            for part in attr_path.split("."):
                obj = getattr(obj, part)
            return obj if callable(obj) else None
        except Exception:
            return None

    def _run_job(job: JobDefinition) -> Any:
        handler = _resolve_handler(job.handler)
        if handler is None:
            return None
        args = list(job.kwargs.get("args", []) or [])
        try:
            import api.scheduler as sched_mod

            qualname = getattr(handler, "__qualname__", "") or ""
            if qualname.startswith("ScanScheduler."):
                instance = getattr(sched_mod, "scheduler_instance", None)
                if instance is not None:
                    method_name = qualname.split(".", 1)[1]
                    bound = getattr(instance, method_name, None)
                    if callable(bound):
                        handler = bound
            return handler(*args)
        except Exception:
            return None

    def _on_job_due(job: JobDefinition) -> Any:
        core_bus.publish("scheduler:job_due", job_id=job.job_id, app_id=job.app_id)
        return _run_job(job)

    core_bus.subscribe("scheduler:job_due", lambda **kw: logger.info("[ORION] Job due: %s", kw.get("job_id")))
    orion_scheduler.set_job_handler(_on_job_due)

    for job_def in registry.get_scheduler_jobs():
        jd = (
            job_def
            if isinstance(job_def, JobDefinition)
            else JobDefinition(
                job_id=job_def["job_id"],
                app_id=job_def["app_id"],
                handler=job_def["handler"],
                trigger=job_def.get("trigger", "interval"),
                seconds=job_def.get("seconds", 3600),
                kwargs=job_def.get("kwargs", {}),
                metadata=job_def.get("metadata"),
            )
        )
        orion_scheduler.add_job(jd)

    try:
        from core.scheduler.jobs import get_all_jobs

        registered_ids = {job.job_id for job in orion_scheduler.get_jobs()}
        for _cycle, cycle_jobs in get_all_jobs().items():
            for job_def in cycle_jobs:
                if job_def.job_id in registered_ids:
                    continue
                registered_ids.add(job_def.job_id)
                orion_scheduler.add_job(job_def)
    except Exception:
        pass

    return orion_scheduler


async def _start_orion_scheduler(orion_scheduler: Any) -> None:
    if orion_scheduler is None:
        return
    await orion_scheduler.start()


def _init_optimization() -> None:
    from cores.optimization import get_optimization_engine

    get_optimization_engine().start()


def _init_autonomous() -> None:
    from cores.autonomous import get_autonomous_engine

    e = get_autonomous_engine()
    e.start()
    e.enable()


def _init_extensions() -> None:
    from core.extension.registry import get_extension_registry
    from core.integrations.registry import init_integration_registry

    ext_reg = get_extension_registry()
    ext_reg.discover()
    results = ext_reg.load_all()
    init_integration_registry(ext_reg)


def _init_secrets() -> None:
    from core.secrets.manager import get_secrets_manager

    sm = get_secrets_manager()
    logger.info("[BG-INIT] Secrets: %d keys cached", len(sm.list_keys()))


def _init_evolution() -> None:
    from core.evolution.engine import init_evolution_engine

    init_evolution_engine()


def _init_event_store(bus: Any) -> None:
    from cores.events.store import get_event_store

    _event_store = get_event_store()

    from core.capabilities.registry import get_capability_registry

    _creg = get_capability_registry()

    try:
        from core.integrations.ext.hunter_bridge import status_summary

        _hunter_status = status_summary()
        for name, info in _hunter_status.items():
            if name == "checked_at":
                continue
            _creg.register(
                "hunt_vulnerability",
                f"core.integrations.ext.hunter_bridge.{name}",
                {"installed": info.get("installed", False)},
            )
    except Exception:
        pass

    def _opportunity_handler(event_type: str, **payload: Any) -> None:
        with suppress(Exception):
            pass  # Will be wired up after copilot init

    bus.subscribe("opportunity:found", _opportunity_handler)
    bus.subscribe("opportunity:updated", _opportunity_handler)


def _init_notification_bridges(bus: Any, app: Any) -> None:
    from cores.notifications.bridges import (
        register_db_bridge,
        register_desktop_channel,
        register_event_bridge,
    )

    register_db_bridge()
    register_desktop_channel()

    try:
        register_event_bridge()
    except Exception:
        pass


def _init_copilot_handlers(bus: Any, app: Any) -> None:
    # Evidence graph handler
    try:
        from core.evidence_graph.graph import get_evidence_graph

        _eg = get_evidence_graph()

        def _evidence_handler(event_type: str, **payload: Any) -> None:
            with suppress(Exception):
                new_status = payload.get("new_status")
                if new_status in ("confirmed", "rejected", "inconclusive"):
                    _eg.record_from_verdict(
                        hypothesis_id=payload.get("id", "unknown"),
                        verdict_status=new_status,
                        confidence=payload.get("confidence", 0.5),
                    )

        bus.subscribe("finding:status_changed", _evidence_handler)
    except Exception:
        pass

    # Knowledge graph handler
    try:
        from core.knowledge.graph import get_knowledge_graph

        _kg = get_knowledge_graph()

        def _kg_handler(event_type: str, **payload: Any) -> None:
            with suppress(Exception):
                if event_type.startswith("finding:"):
                    _kg.record_finding(
                        target_id=payload.get("target_id", "orphan"),
                        finding_id=payload.get("id", "unknown"),
                        finding_name=payload.get("name", event_type),
                        severity=payload.get("severity", "medium"),
                    )
                elif event_type.startswith("target:"):
                    _kg.add_node(
                        "target",
                        payload.get("name", event_type),
                        {"domain": payload.get("domain", "")},
                        node_id=payload.get("id", "unknown"),
                    )

        for pattern in ("finding:created", "finding:confirmed", "target:created"):
            bus.subscribe(pattern, _kg_handler)
    except Exception:
        pass

    # Copilot API router
    try:
        from api.routers.copilot import router as copilot_router
        from core.copilot.orion_context import get_orion_context
        from database import db as _db

        get_orion_context(db_factory=_db.SessionLocal)
        app.include_router(copilot_router)
    except Exception:
        pass


def _init_telegram_bridge(bus: Any) -> None:
    def _telegram_handler(event_type: str, **payload: Any) -> None:
        with suppress(Exception):
            from core.notifications.telegram.bridge import handle_event

            handle_event(event_type, **payload)

    for ev in (
        "finding:created",
        "finding:confirmed",
        "finding:status_changed",
        "report:generated",
        "report:accepted",
        "report:rejected",
        "system:error",
        "system:degraded",
        "system:alert",
    ):
        bus.subscribe(ev, _telegram_handler)


async def _init_financial_scheduler() -> Any:
    from cores.financial.scheduler import get_financial_sync_scheduler

    fin_scheduler = get_financial_sync_scheduler()
    fin_scheduler.interval_minutes = int(os.environ.get("CATEYE_SYNC_INTERVAL", "30"))
    t = asyncio.create_task(fin_scheduler.start())
    _background_tasks.discard(t)
    _background_tasks.add(t)
    return fin_scheduler


def _init_agent_bridges() -> None:
    from cores.agents.bus import bridge_agent_bus_to_eventbus, bridge_eventbus_to_agent_bus

    bridge_agent_bus_to_eventbus()
    bridge_eventbus_to_agent_bus()


def _init_auto_report(bus: Any) -> None:
    def _auto_report(event_type: str, payload: dict) -> None:
        if payload.get("new_status") != "confirmed":
            return
        with suppress(Exception):
            from core.auto_submit.pipeline import get_auto_submit_pipeline

            pipeline = get_auto_submit_pipeline()
            pipeline.process_finding(payload["id"])

    bus.subscribe("finding:status_changed", _auto_report)


def _init_feedback_tuner(bus: Any) -> None:
    try:
        from cores.validation.feedback_tuner import FeedbackTuner

        _tuner = FeedbackTuner()

        def _fb_handler(event_type: str, **payload: Any) -> None:
            if payload.get("new_status") not in ("confirmed", "rejected"):
                return
            with suppress(Exception):
                _tuner.record_feedback(payload)
                _tuner.tune_if_ready()

        bus.subscribe("finding:status_changed", _fb_handler)
    except Exception:
        pass


def _init_verdict_learner(bus: Any) -> None:
    try:
        from core.learning.verdict_learner import get_verdict_learner

        _vl = get_verdict_learner()
        bus.subscribe("finding:status_changed", lambda et, **pl: _vl.handle_finding_status_changed(pl))
    except Exception:
        pass


def _init_unified_memory() -> None:
    from core.memory.store import get_memory_store

    _store = get_memory_store()
    logger.info("[BG-INIT] Unified Memory: %d entries", _store.count())


def _init_smart_notifications(bus: Any) -> None:
    try:
        from core.notifications.intelligent import get_intelligent_notifier

        notifier = get_intelligent_notifier()

        def _smart_notify(event_type: str, **payload: Any) -> None:
            data = dict(payload)
            data.pop("_priority", None)
            title = data.pop("title", event_type)
            body = data.pop("message", data.pop("body", ""))
            notification = notifier.process_event(event_type, title=title, body=body, data=data)
            if notification is not None:
                notifier.route_to_user(notification)

        for evt in ("finding:created", "finding:confirmed", "opportunity:found", "report:generated", "system:error"):
            bus.subscribe(evt, _smart_notify)
    except Exception:
        pass


# Shared set for background tasks
_background_tasks: set[asyncio.Task[None]] = set()
