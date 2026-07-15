import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import PlainTextResponse

from api.middleware.auth_middleware import AuthMiddleware
from api.middleware.csrf_middleware import CSRFMiddleware
from api.middleware.error_handling import ErrorHandlingMiddleware, SecurityHeadersMiddleware
from api.middleware.rate_limit_middleware import RateLimitMiddleware
from api.routers import (
    accounts_hub,
    agents_router,
    assistant,
    attack,
    attack_surface,
    auth,
    auth_users,
    authhub,
    bank_payout,
    canonical,
    connections,
    contracts,
    crypto,
    daily,
    differential_intelligence,
    digest,
    discovery,
    economic,
    endpoints,
    evidence,
    evolution,
    execution,
    financial_sync,
    financial_truth,
    findings,
    hunt,
    hunter,
    hypotheses,
    identity,
    identity_center,
    idor,
    intelligence,
    investigations,
    license,
    micro,
    mission,
    mobile,
    notifications,
    offensive,
    operations,
    opportunities,
    opportunity_intelligence,
    orchestrator,
    orion,
    osint,
    overview,
    pipeline,
    platforms,
    project_dashboard,
    quick_wins,
    reports,
    reports_quality,
    revenue,
    roi,
    scans,
    screenshots,
    settings_ai,
    settings_runtime,
    settings_unified,
    sync,
    system,
    system_state,
    target_identity,
    targets,
    validation,
    verdicts,
    webhooks,
    ws,
    zap,
)
from cores.env.config import get_config
from cores.intelligence.adaptive_memory import get_memory
from cores.learning.router import router as learning_router
from cores.log_config import setup_logging
from cores.observability import get_metrics
from database import db

setup_logging()

logger = logging.getLogger("cateye.api")

# Track background tasks to prevent silent crashes and allow cancellation
_background_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import all models before init_db() so SQLAlchemy metadata registers all tables
    from cores.learning import profile as _learning_models  # noqa: F401 — registers InvestigatorProfile, LearningEvent
    from cores.targets import models as _targets_models  # noqa: F401 — registers TargetIntel, Scope

    db.init_db()
    logger.info("Database initialized")

    # Initialize event bus and system state
    from cores.events.event_bus import get_event_bus
    from cores.system_state import get_system_state

    bus = get_event_bus()
    state = get_system_state()
    state.register_service("backend")
    state.register_service("frontend")
    state.register_service("intelligence")
    state.register_service("assistant")
    state.register_service("discovery")
    state.report_healthy("backend")
    bus.publish("system:boot:complete", service="backend")
    logger.info("Event bus and system state initialized")

    # Check product behavior rules
    from cores.product_rules import enforce_on_startup

    enforce_on_startup()
    logger.info("Product behavior rules checked")

    # Initialize identity system
    from cores.identity.identity_manager import get_identity_manager

    identity = get_identity_manager()
    identity.ensure_identity()
    user_identity = identity.get_identity()
    logger.info("Identity system initialized: %s", user_identity.user_id if user_identity else "unknown")

    # Initialize AuthHub
    try:
        from cores.authhub import get_authhub

        get_authhub().init_defaults()
        logger.info("AuthHub initialized with default providers")
    except Exception as exc:
        logger.warning("AuthHub init failed (non-fatal): %s", exc)

    # Initialize orchestrator
    from cores.orchestrator.assistant_orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    orchestrator.suppress_noise_items(threshold=0.15)
    logger.info("Assistant orchestrator initialized")

    # Initialize execution layer
    from cores.actions.execution_tracker import get_execution_tracker

    get_execution_tracker()
    logger.info("Execution tracker initialized")

    from cores.accountability.outcome_tracker import get_outcome_tracker

    get_outcome_tracker()
    logger.info("Outcome tracker initialized")

    from cores.accountability.system_scorecard import get_system_scorecard

    scorecard = get_system_scorecard()
    scorecard.generate()
    logger.info("System scorecard initialized")

    from cores.explainability.explanation_engine import get_explanation_engine

    get_explanation_engine()
    logger.info("Explanation engine initialized")

    from cores.explainability.decision_trace import get_decision_trace

    get_decision_trace()
    logger.info("Decision trace collector initialized")

    from cores.memory.memory_store import get_memory_store

    get_memory_store()
    logger.info("Memory store initialized")

    from cores.memory.decision_memory import get_decision_memory

    get_decision_memory()
    logger.info("Decision memory initialized")

    from cores.memory.insight_archive import get_insight_archive

    get_insight_archive()
    logger.info("Insight archive initialized")

    # Consume memory into priority engine
    from cores.intelligence.priority_engine import get_priority_engine

    pe = get_priority_engine()
    result = pe.consume_memory()
    logger.info("Priority engine memory consumption: %s", result.get("status", "unknown"))

    # Discover opportunities on startup (non-blocking)
    try:
        from cores.opportunity import get_engine

        opp_engine = get_engine()
        opp_count = len(await asyncio.to_thread(opp_engine.discover_all))
        logger.info("Opportunity engine initialized with %d opportunities", opp_count)
    except Exception as exc:
        logger.warning("Opportunity engine discovery failed (non-fatal): %s", exc)

    logger.info("Execution layer fully initialized")

    # Start background scan scheduler
    scheduler = None
    try:
        from api.scheduler import ScanScheduler

        scheduler = ScanScheduler(interval_minutes=get_config().scan_interval)
        t = asyncio.create_task(scheduler.start())
        t.add_done_callback(_background_tasks.discard)
        _background_tasks.add(t)
        logger.info("Scan scheduler started")
    except Exception as exc:
        logger.warning("Scan scheduler failed to start (non-fatal): %s", exc)

    # Start background notification poller
    try:
        from api.routers.operations import start_notification_poller

        start_notification_poller()
        logger.info("Notification poller started")
    except Exception as exc:
        logger.warning("Notification poller failed to start (non-fatal): %s", exc)

    # Start WebSocket event bus bridge
    try:
        from cores.ws.bridge import start_event_bridge

        start_event_bridge()
        logger.info("WS event bridge started")
    except Exception as exc:
        logger.warning("WS event bridge failed to start (non-fatal): %s", exc)

    # Register notification bridges
    try:
        from cores.notifications.bridges import (
            register_db_bridge,
            register_desktop_channel,
            register_discord_channel,
            register_email_channel,
            register_event_bridge,
            register_fcm_channel,
            register_gmail_channel,
            register_mobile_channel,
            register_whatsapp_channel,
            register_ws_forwarder,
        )

        register_db_bridge()
        register_desktop_channel()
        register_discord_channel()
        register_email_channel()
        register_fcm_channel()
        register_mobile_channel()
        register_whatsapp_channel()
        register_gmail_channel()
        register_ws_forwarder()
        logger.info("Notification bridges registered")
    except Exception as exc:
        logger.warning("Notification bridges failed (non-fatal): %s", exc)

    # Subscribe event bus -> notification bridge
    try:
        register_event_bridge()
        logger.info("Event -> notification bridge started")
    except Exception as exc:
        logger.warning("Event -> notification bridge failed (non-fatal): %s", exc)

    # Initialize Financial Event System
    try:
        from cores.financial.events import init_financial_events

        init_financial_events()
        logger.info("[BOOT] Financial event system initialized")
    except Exception as exc:
        logger.warning("Financial events init failed (non-fatal): %s", exc)

    # Auto-report: when a finding is confirmed, generate a report draft
    try:
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()

        def _auto_report(event_type, payload):
            if payload.get("new_status") != "confirmed":
                return
            from database import db as _db

            _db.init_db()
            session = _db.SessionLocal()
            try:
                from cores.pipeline.report_service import create_report_from_findings

                report = create_report_from_findings(
                    session=session,
                    finding_ids=[payload["id"]],
                    program="",
                    target=f"target_{payload.get('target_id')}",
                    vulnerability=payload.get("title", ""),
                    severity=payload.get("severity", "medium"),
                )
                if report:
                    logger.info("[AUTO] Report %s auto-generated for finding %s", report.get("id"), payload.get("id"))
            except Exception as exc:
                logger.warning("[AUTO] Auto-report failed for finding %s: %s", payload.get("id"), exc)
            finally:
                session.close()

        bus.subscribe("finding:status_changed", _auto_report)
        logger.info("[BOOT] Auto-report subscriber registered")

        # FeedbackTuner: accumulate human feedback, periodically tune ConfidenceScorer
        _tuner = None
        try:
            from cores.validation.feedback_tuner import FeedbackTuner

            _tuner = FeedbackTuner()
            logger.info("[BOOT] FeedbackTuner initialized — %s persisted events", len(_tuner.get_events()))
        except Exception as exc:
            logger.warning("[BOOT] FeedbackTuner init error: %s", exc)

        def _feedback_handler(event_type, payload):
            if payload.get("new_status") not in ("confirmed", "rejected"):
                return
            if _tuner is None:
                return
            try:
                from database import db as _db
                from database import models as _mdls

                enriched = dict(payload)
                if "vulnerability_type" not in enriched:
                    _db.init_db()
                    _session = _db.SessionLocal()
                    try:
                        _f = _session.query(_mdls.Finding).filter(_mdls.Finding.id == payload.get("id")).first()
                        if _f:
                            enriched["vulnerability_type"] = _f.vulnerability_type
                    finally:
                        _session.close()
                _tuner.record_feedback(enriched)
                result = _tuner.tune_if_ready()
                if result.get("status") == "tuned":
                    logger.info(
                        "[FEEDBACK] ConfidenceScorer weights adjusted after %s events — weights: %s",
                        result["events_analyzed"],
                        result["new_weights"],
                    )
                elif result.get("status") == "error":
                    logger.warning("[FEEDBACK] Tuning error: %s", result.get("reason"))
            except Exception as exc:
                logger.warning("[FEEDBACK] Handler error: %s", exc)

        bus.subscribe("finding:status_changed", _feedback_handler)
        logger.info("[BOOT] FeedbackTuner subscriber registered")

        # ── Unified Memory ────────────────────────────────────────────
        try:
            from core.memory.store import get_memory_store

            _store = get_memory_store()
            logger.info(
                "[BOOT] Unified Memory initialized: %d entries across %d namespaces",
                _store.count(),
                len(_store.list_namespaces()),
            )
        except Exception as exc:
            logger.warning("[BOOT] Unified Memory init error: %s", exc)

        # ── Senior Copilot Agent ───────────────────────────────────────
        _copilot = None
        try:
            from core.copilot.agent import CopilotAgent
            from core.copilot.permissions import AuthorityLevel

            _copilot = CopilotAgent(authority=AuthorityLevel.SENIOR_HUNTER)
            logger.info("[BOOT] Senior Copilot Agent initialized (authority=%s)", _copilot.authority.value)
        except Exception as exc:
            logger.warning("[BOOT] Copilot Agent init error: %s", exc)

        async def _copilot_analyze(finding: dict, verdict: dict):
            if _copilot is None:
                return
            try:
                result = await _copilot.analyze_finding(finding, verdict)
                if result.needs_human:
                    logger.info(
                        "[COPILOT] Finding %s needs human review (%d inconsistencies)",
                        finding["id"],
                        len(result.inconsistencies),
                    )
                else:
                    logger.info(
                        "[COPILOT] Finding %s analyzed: status=%s confidence=%.0f%%",
                        finding["id"],
                        result.status,
                        result.confidence * 100,
                    )
            except Exception as exc:
                logger.warning("[COPILOT] Analysis handler error: %s", exc)

        def _copilot_finding_handler(event_type, payload):
            if _copilot is None:
                return
            try:
                finding = {
                    "id": payload.get("id"),
                    "vulnerability_type": payload.get("vulnerability_type") or payload.get("type", ""),
                    "severity": payload.get("severity"),
                    "description": payload.get("title") or payload.get("description", ""),
                    "status": payload.get("new_status") or payload.get("status"),
                }
                verdict = {"confidence": payload.get("confidence", 0.0)}
                loop = asyncio.get_running_loop()
                loop.create_task(_copilot_analyze(finding, verdict))
            except RuntimeError:
                logger.warning("[COPILOT] No running event loop for copilot analysis")
            except Exception as exc:
                logger.warning("[COPILOT] Analysis handler error: %s", exc)

        bus.subscribe("finding:created", _copilot_finding_handler)
        bus.subscribe("finding:status_changed", _copilot_finding_handler)

        def _copilot_target_handler(event_type, payload):
            if _copilot is None:
                return
            target_name = payload.get("name", "unknown")
            domain = payload.get("domain", "")
            logger.info(
                "[COPILOT] New target: %s (domain=%s) — generating engagement plan",
                target_name,
                domain or "none",
            )
            try:
                copilot = _copilot
                plan = copilot.create_plan(finding=None)
                if plan:
                    copilot.remember(
                        namespace="cateye",
                        key=f"plan:target:{payload.get('id', 'unknown')}",
                        content=f"Engagement plan for {target_name}",
                        tags=["plan", "engagement", target_name],
                        priority=7.0,
                    )
            except Exception as exc:
                logger.warning("[COPILOT] Target handler error: %s", exc)

        bus.subscribe("target:created", _copilot_target_handler)
        logger.info("[BOOT] Senior Copilot Agent subscribers registered (finding + target)")

        # ── Evidence Graph ──────────────────────────────────────────────
        _eg = None
        try:
            from core.evidence_graph.graph import get_evidence_graph

            _eg = get_evidence_graph()
            stats = _eg.get_stats()
            logger.info(
                "[BOOT] Evidence Graph initialized: %d nodes, %d hypotheses", stats["total_nodes"], stats["hypotheses"]
            )
        except Exception as exc:
            logger.warning("[BOOT] Evidence Graph init error: %s", exc)

        def _evidence_graph_handler(event_type, payload):
            if _eg is None:
                return
            new_status = payload.get("new_status")
            if new_status not in ("confirmed", "rejected", "inconclusive"):
                return
            hypothesis_id = payload.get("id", "unknown")
            confidence = payload.get("confidence", 0.5)
            try:
                _eg.record_from_verdict(
                    hypothesis_id=hypothesis_id,
                    verdict_status=new_status,
                    confidence=confidence,
                )
                balance = _eg.get_balance(hypothesis_id)
                logger.debug(
                    "[EVIDENCE] Recorded %s for %s (net=%.2f, for=%d, against=%d)",
                    new_status,
                    hypothesis_id,
                    balance["net_score"],
                    balance["for_count"],
                    balance["against_count"],
                )
            except Exception as exc:
                logger.warning("[EVIDENCE] Handler error: %s", exc)

        bus.subscribe("finding:status_changed", _evidence_graph_handler)
        logger.info("[BOOT] Evidence Graph subscriber registered")

        # ── Knowledge Graph Event Bridge ───────────────────────────
        try:
            from core.knowledge.graph import get_knowledge_graph

            _kg = get_knowledge_graph()
            stats = _kg.get_stats()
            logger.info(
                "[BOOT] Knowledge Graph initialized: %d nodes, %d edges",
                stats["total_nodes"],
                stats["total_edges"],
            )

            def _knowledge_graph_handler(event_type: str, payload: dict) -> None:
                try:
                    if event_type.startswith("finding:"):
                        finding_id = payload.get("id", "unknown")
                        target_id = payload.get("target_id") or payload.get("target", {}).get("id")
                        _kg.record_finding(
                            target_id=target_id or "orphan",
                            finding_id=finding_id,
                            finding_name=payload.get("name", event_type),
                            severity=payload.get("severity", "medium"),
                        )
                    elif event_type.startswith("target:"):
                        target_id = payload.get("id", "unknown")
                        _kg.add_node(
                            "target",
                            payload.get("name", event_type),
                            {"domain": payload.get("domain", "")},
                            node_id=target_id,
                            source="scheduler",
                        )
                    elif event_type.startswith("copilot:") and "decision" in event_type:
                        _kg.record_decision(payload)
                except Exception as exc:
                    logger.debug("[KG] Handler error: %s", exc)

            for event_pattern in ("finding:created", "finding:confirmed", "finding:status_changed", "target:created"):
                bus.subscribe(event_pattern, _knowledge_graph_handler)
            logger.info("[BOOT] Knowledge Graph event bridge registered")
        except Exception as exc:
            logger.warning("[BOOT] Knowledge Graph bridge error: %s", exc)

        # ── Copilot API Router ─────────────────────────────────────
        try:
            from api.routers.copilot import _set_copilot
            from api.routers.copilot import router as copilot_router

            _set_copilot(_copilot)
            app.include_router(copilot_router)
            logger.info("[BOOT] Copilot API router registered")
        except Exception as exc:
            logger.warning("[BOOT] Copilot API router error: %s", exc)
    except Exception as exc:
        logger.warning("Auto-report/Copilot/Evidence Graph setup failed: %s", exc)

    # Start Multi-Agent system
    try:
        from cores.agents import start_all_agents

        agents = start_all_agents()
        logger.info("[BOOT] %d agents started", len(agents))
    except Exception as exc:
        logger.warning("Multi-Agent system failed to start (non-fatal): %s", exc)

    # Start Financial Auto-Sync Scheduler
    fin_scheduler = None
    try:
        from cores.financial.scheduler import get_financial_sync_scheduler

        fin_scheduler = get_financial_sync_scheduler()
        import os

        fin_scheduler.interval_minutes = int(os.environ.get("CATEYE_SYNC_INTERVAL", "30"))
        t = asyncio.create_task(fin_scheduler.start())
        t.add_done_callback(_background_tasks.discard)
        _background_tasks.add(t)
        logger.info("[BOOT] Financial auto-sync scheduler started (interval=%dmin)", fin_scheduler.interval_minutes)
    except Exception as exc:
        logger.warning("Financial auto-sync scheduler failed (non-fatal): %s", exc)

    # Bridge AgentBus → EventBus
    try:
        from cores.agents.bus import bridge_agent_bus_to_eventbus

        bridge_agent_bus_to_eventbus()
        logger.info("[BOOT] AgentBus → EventBus bridge started")
    except Exception as exc:
        logger.warning("AgentBus bridge failed (non-fatal): %s", exc)

    # Start Discovery Monitor
    discovery_monitor = None
    try:
        from cores.bounty_scraper.monitor import get_discovery_monitor

        discovery_monitor = get_discovery_monitor()
        await discovery_monitor.start()
        logger.info("[BOOT] Discovery monitor started")
    except Exception as exc:
        logger.warning("Discovery monitor failed to start (non-fatal): %s", exc)

    # Start Recovery Engine and Health Monitor
    try:
        from cores.recovery import get_health_monitor, get_recovery_engine

        recovery = get_recovery_engine()
        recovery.start()
        monitor = get_health_monitor()
        monitor.start()
        logger.info("[BOOT] Recovery engine and health monitor started")
    except Exception as exc:
        logger.warning("Recovery engine failed to start (non-fatal): %s", exc)

    # Start RC7 Autonomous Intelligence Layer
    try:
        from cores.health import get_system_health_engine

        health_engine = get_system_health_engine()
        health_engine.start()
        logger.info("[BOOT] System health engine started")
    except Exception as exc:
        logger.warning("System health engine failed to start (non-fatal): %s", exc)

    # ── ORION Platform: initialize app registry, databases, scheduler ──
    orion_scheduler = None
    try:
        from core.app_registry import get_app_registry
        from core.database.manager import get_db_manager
        from core.events.event_bus import get_core_event_bus
        from core.scheduler.scheduler import JobDefinition, get_core_scheduler

        registry = get_app_registry()
        registry.discover()
        dbm = get_db_manager()

        # Register databases for each app
        for app_id, app in registry._apps.items():
            if app.db_path:
                dbm.register(app_id, app.db_path)
                if app.models:
                    from sqlalchemy.orm import declarative_base

                    base = declarative_base()
                    dbm.run_migrations(app_id, base)

        # Register and start core scheduler
        core_bus = get_core_event_bus()
        orion_scheduler = get_core_scheduler()
        orion_scheduler.set_job_handler(
            lambda job: core_bus.publish("scheduler:job_due", job_id=job.job_id, app_id=job.app_id)
        )
        for job_def in registry.get_scheduler_jobs():
            jd = JobDefinition(
                job_id=job_def["job_id"],
                app_id=job_def["app_id"],
                handler=job_def["handler"],
                trigger=job_def.get("trigger", "interval"),
                seconds=job_def.get("seconds", 3600),
            )
            orion_scheduler.add_job(jd)
        await orion_scheduler.start()

        logger.info(
            "[ORION] App registry initialized: %d apps, %d databases, %d jobs",
            len(registry._apps),
            len(dbm.list_databases()),
            orion_scheduler.job_count,
        )
    except Exception as exc:
        logger.warning("[ORION] App registry init failed (non-fatal): %s", exc)

    try:
        from cores.optimization import get_optimization_engine

        opt_engine = get_optimization_engine()
        opt_engine.start()
        logger.info("[BOOT] Auto-optimization engine started")
    except Exception as exc:
        logger.warning("Auto-optimization engine failed to start (non-fatal): %s", exc)

    try:
        from cores.autonomous import get_autonomous_engine

        auto_engine = get_autonomous_engine()
        auto_engine.start()
        auto_engine.enable()
        logger.info("[BOOT] AUTONOMOUS+ mode engine started and enabled")
    except Exception as exc:
        logger.warning("AUTONOMOUS+ engine failed to start (non-fatal): %s", exc)

    # ── ORION Platform: extensions, secrets, health ──
    try:
        from core.app_registry import get_app_registry

        registry = get_app_registry()
        from core.extension.registry import get_extension_registry

        ext_reg = get_extension_registry()
        ext_reg.discover()
        results = ext_reg.load_all()
        loaded = sum(1 for v in results.values() if v)
        logger.info(
            "[ORION] Extensions: %d discovered, %d loaded",
            ext_reg.count,
            loaded,
        )
    except Exception as exc:
        logger.warning("[ORION] Extension discovery failed (non-fatal): %s", exc)

    try:
        from core.secrets.manager import get_secrets_manager

        sm = get_secrets_manager()
        logger.info("[ORION] Secrets manager initialized (%d keys cached)", len(sm.list_keys()))
    except Exception as exc:
        logger.warning("[ORION] Secrets manager init failed (non-fatal): %s", exc)

    try:
        from core.health.checks import register_default_checks
        from core.health.engine import get_health_center

        center = get_health_center()
        center.enable_persistence()
        register_default_checks(center)
        snapshot = center.run_all()
        logger.info(
            "[ORION] Health center initialized: %s (%d/%d checks passed)",
            snapshot.status.upper(),
            sum(1 for v in snapshot.checks.values() if v),
            len(snapshot.checks),
        )

        # Register ORION specific checks
        def check_extension_health() -> bool:
            try:
                from core.extension.registry import get_extension_registry

                er = get_extension_registry()
                return er.failed_count == 0
            except Exception:
                return False

        def check_secrets_health() -> bool:
            try:
                from core.secrets.manager import get_secrets_manager

                sm = get_secrets_manager()
                h = sm.health()
                return h.get("vault_available", False) or h.get("cached_keys", 0) > 0
            except Exception:
                return False

        center.register("extensions", check_extension_health, "integration")
        center.register("secrets", check_secrets_health, "integration")
        logger.info("[ORION] Extension + secrets health checks registered")
    except Exception as exc:
        logger.warning("[ORION] Health center init failed (non-fatal): %s", exc)

    # ── Evolution Engine boot ──
    try:
        from core.evolution.engine import init_evolution_engine

        engine = init_evolution_engine()
        logger.info("[EVOLUTION] Engine ready — Observe layer accepting metrics")
    except Exception as exc:
        logger.warning("[EVOLUTION] Engine init failed (non-fatal): %s", exc)

    # ── Event Store + Pipeline Subscribers ─────────────────────
    try:
        # 1. Init Event Store
        from core.events.store import get_event_store

        _event_store = get_event_store()
        logger.info("[EVENT] Event Store initialized (%d events)", _event_store.count())

        # 2. Register capabilities for connectors (late init for early-boot connectors)
        from core.capabilities.registry import get_capability_registry

        _creg = get_capability_registry()
        logger.info(
            "[CAP] Capability Registry: %d capabilities from %d modules", len(_creg.list_capabilities()), _creg.count()
        )

        # 3. Subscribers for orphan events
        bus = get_event_bus()

        def _opportunity_handler(event_type, payload):
            """When a new opportunity is found, refresh COPILOT recommendations."""
            if _copilot is not None:
                with suppress(Exception):
                    _copilot.recommend_for_system(extra_state={"new_opportunity": payload.get("id")})

        bus.subscribe("opportunity:found", _opportunity_handler)
        bus.subscribe("opportunity:updated", _opportunity_handler)

        def _recovery_handler(event_type, payload):
            """When recovery happens, log to Event Store."""
            with suppress(Exception):
                _event_store.store_dict(
                    event_type=event_type,
                    correlation_id=payload.get("correlation_id", ""),
                    source="recovery",
                    payload=payload,
                )

        bus.subscribe("recovery:started", _recovery_handler)
        bus.subscribe("recovery:success", _recovery_handler)
        bus.subscribe("recovery:failed", _recovery_handler)

        logger.info("[EVENT] Event subscribers registered (opportunity, recovery)")
    except Exception as exc:
        logger.warning("[BOOT] Event pipeline init failed (non-fatal): %s", exc)

    yield

    # Stop RC7 Autonomous Intelligence Layer
    try:
        from cores.autonomous import get_autonomous_engine

        auto_engine = get_autonomous_engine()
        auto_engine.disable()
        auto_engine.stop()
        logger.info("[BOOT] AUTONOMOUS+ engine stopped")
    except Exception as exc:
        logger.warning("AUTONOMOUS+ engine stop error: %s", exc)

    try:
        from cores.health import get_system_health_engine

        health_engine = get_system_health_engine()
        health_engine.stop()
        logger.info("[BOOT] System health engine stopped")
    except Exception as exc:
        logger.warning("System health engine stop error: %s", exc)

    try:
        from cores.optimization import get_optimization_engine

        opt_engine = get_optimization_engine()
        opt_engine.stop()
        logger.info("[BOOT] Auto-optimization engine stopped")
    except Exception as exc:
        logger.warning("Auto-optimization engine stop error: %s", exc)

    # Stop Recovery Engine and Health Monitor
    try:
        from cores.recovery import get_health_monitor, get_recovery_engine

        monitor = get_health_monitor()
        monitor.stop()
        engine = get_recovery_engine()
        engine.stop()
        logger.info("[BOOT] Recovery engine and health monitor stopped")
    except Exception as exc:
        logger.warning("Recovery engine stop error: %s", exc)

    # Stop Multi-Agent system
    try:
        from cores.agents import stop_all_agents

        stop_all_agents()
        logger.info("[BOOT] All agents stopped")
    except Exception as exc:
        logger.warning("Multi-Agent system stop error: %s", exc)

    # Graceful shutdown of background tasks
    if scheduler is not None:
        try:
            await scheduler.stop()
            logger.info("Scan scheduler stopped")
        except Exception as exc:
            logger.warning("Scan scheduler stop error: %s", exc)

    # Stop Financial Auto-Sync Scheduler
    if fin_scheduler is not None:
        try:
            await fin_scheduler.stop()
            logger.info("[BOOT] Financial auto-sync scheduler stopped")
        except Exception as exc:
            logger.warning("Financial auto-sync scheduler stop error: %s", exc)

    # Stop ORION Core Scheduler
    if orion_scheduler is not None:
        try:
            await orion_scheduler.stop()
            logger.info("[ORION] Core scheduler stopped")
        except Exception as exc:
            logger.warning("[ORION] Core scheduler stop error: %s", exc)

    # Stop Discovery Monitor
    if discovery_monitor is not None:
        try:
            await discovery_monitor.stop()
            logger.info("[BOOT] Discovery monitor stopped")
        except Exception as exc:
            logger.warning("Discovery monitor stop error: %s", exc)

    # Stop Notification Poller
    try:
        from api.routers.operations import stop_notification_poller

        stop_notification_poller()
        logger.info("[BOOT] Notification poller stopped")
    except Exception as exc:
        logger.warning("Notification poller stop error: %s", exc)

    # Cancel any remaining background tasks
    for task in list(_background_tasks):
        if not task.done():
            task.cancel()
    _background_tasks.clear()
    logger.info("[BOOT] Background tasks cancelled")


# Read version from VERSION file (single source of truth)
_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
_APP_VERSION = _VERSION_FILE.read_text().strip() if _VERSION_FILE.is_file() else "0.0.0"

app = FastAPI(
    title="CATEYE API",
    description="Bug Bounty Intelligence Platform — automated reconnaissance, analysis, and reporting.",
    version=_APP_VERSION,
    lifespan=lifespan,
    contact={"name": "CATEYE Team", "url": "https://github.com/AdriDob/rastrohunteralpha"},
    license_info={"name": "Proprietary"},
    swagger_ui_parameters={"deepLinking": True, "displayRequestDuration": True},
)

# Production: restrict to local origins + pywebview app:// protocol.
# Dev mode (CATEYE_DESKTOP not set) uses * but without credentials per Fetch spec.
_allow_all = not get_config().desktop
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if _allow_all
    else [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "app://",
    ],
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(ErrorHandlingMiddleware)


def _custom_openapi() -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        contact=app.contact,
        license_info=app.license_info,
    )
    openapi_schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from POST /api/auth/login or /api/auth/register",
        }
    }
    for path in openapi_schema.get("paths", {}).values():
        for method in path.values():
            if method.get("operationId") != "login_register" and "/api/auth" not in (method.get("tags") or []):
                method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = _custom_openapi

app.include_router(targets.router)
app.include_router(endpoints.router)
app.include_router(findings.router)
app.include_router(evidence.router)
app.include_router(evolution.router)
app.include_router(opportunities.router)
app.include_router(attack_surface.router)
app.include_router(pipeline.router)
app.include_router(quick_wins.router)
app.include_router(reports.router)
app.include_router(reports_quality.router)
app.include_router(revenue.router)
app.include_router(hypotheses.router)
app.include_router(roi.router)
app.include_router(overview.router)
app.include_router(assistant.router)
app.include_router(scans.router)
app.include_router(digest.router)
app.include_router(verdicts.router)
app.include_router(attack.router)
app.include_router(validation.router)
app.include_router(differential_intelligence.router)
app.include_router(canonical.router)
app.include_router(intelligence.router)
app.include_router(system.router)
app.include_router(screenshots.router)
app.include_router(operations.router)
app.include_router(opportunity_intelligence.router)
app.include_router(auth.router)
app.include_router(auth_users.router)
app.include_router(sync.router)
app.include_router(notifications.router)
app.include_router(mobile.router)
app.include_router(contracts.router)
app.include_router(system_state.router)
app.include_router(daily.router)
app.include_router(discovery.router)
app.include_router(orchestrator.router)
app.include_router(identity.router)
app.include_router(identity_center.router)
app.include_router(target_identity.router)
app.include_router(execution.router)
app.include_router(license.router)
app.include_router(learning_router)
app.include_router(project_dashboard.router)
app.include_router(ws.router)
app.include_router(idor.router)
app.include_router(offensive.router)
app.include_router(investigations.router)
app.include_router(settings_ai.router)
app.include_router(settings_runtime.router)
app.include_router(settings_unified.router)
app.include_router(webhooks.router)
app.include_router(orion.router)
app.include_router(economic.router)
app.include_router(agents_router.router)
app.include_router(zap.router)
app.include_router(connections.router)
app.include_router(platforms.router)
app.include_router(financial_sync.router)
app.include_router(financial_truth.router)
app.include_router(mission.router)
app.include_router(crypto.router)
app.include_router(accounts_hub.router)
app.include_router(authhub.router)
app.include_router(bank_payout.router)
app.include_router(micro.router)
app.include_router(osint.router)
app.include_router(hunt.router)
app.include_router(hunter.router)

# ── ORION Platform: core + app routers ──
try:
    from core.api.routers import router as core_router

    app.include_router(core_router)
    from core.app_registry import get_app_registry

    registry = get_app_registry()
    registry.mount_routers(app)
    logger.info("[ORION] Core + app routers mounted")
except Exception as exc:
    logger.warning("[ORION] Router mounting failed (non-fatal): %s", exc)


APP_VERSION = _APP_VERSION


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "CATEYE API", "version": APP_VERSION}


@app.get("/api/system/status")
async def system_status():
    """Enhanced system health dashboard — includes watchdog, pipeline, agents."""
    import psutil

    from cores.system_health import collect_health
    from cores.system_state import get_system_state
    from desktop.watchdog import get_watchdog

    state = get_system_state()
    health_data = collect_health()
    watchdog = get_watchdog()

    pid = os.getpid()
    proc = psutil.Process(pid)
    mem = proc.memory_info()
    summary = state.get_summary() if hasattr(state, "get_summary") else {}

    return {
        "status": summary.get("system_state", "unknown") if summary else "unknown",
        "version": APP_VERSION,
        "pid": pid,
        "uptime_seconds": state.get_uptime() if hasattr(state, "get_uptime") else 0.0,
        "watchdog": watchdog.get_status() if watchdog and watchdog.is_running else {"running": False},
        "system": {
            "memory_percent": proc.memory_percent(),
            "memory_rss_mb": mem.rss / 1024 / 1024,
            "cpu_percent": proc.cpu_percent(interval=0.3),
            "num_threads": proc.num_threads(),
        },
        "pipeline": {
            "total_pipelines": health_data.pipeline_latency_count if health_data else 0,
        },
        "agents": state.get_agent_status() if hasattr(state, "get_agent_status") else {},
        "database": {
            "file_size_mb": _get_db_size_mb(),
        },
    }


def _get_db_size_mb() -> float:
    try:
        from cores.platform.system import get_db_path

        p = get_db_path()
        if p.exists():
            return p.stat().st_size / 1024 / 1024
    except Exception as exc:
        logger.warning("Failed to get database size: %s", exc)
    return 0.0


@app.get("/api/version")
async def version():
    return {"version": APP_VERSION, "app": "CATEYE API", "build": None}


@app.get("/api/stats")
async def stats():
    from database import db, models

    session = db.SessionLocal()
    try:
        targets = session.query(models.Target).count()
        endpoints = session.query(models.Endpoint).count()
        findings = session.query(models.Finding).count()
        verdicts = session.query(models.Verdict).count()
        evidence = session.query(models.Evidence).count()
        scan_runs = session.query(models.ScanRun).count()
        return {
            "targets": targets,
            "endpoints": endpoints,
            "findings": findings,
            "verdicts": verdicts,
            "evidence": evidence,
            "scan_runs": scan_runs,
            "status": "ok",
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}
    finally:
        session.close()


@app.get("/api/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus-style metrics endpoint."""
    lines = ["# HELP CATEYE_pipeline_timing Pipeline stage timing in ms", "# TYPE CATEYE_pipeline_timing gauge"]
    for name, stats in get_metrics().items():
        safe = name.replace(".", "_").replace(" ", "_")
        lines.append(f'CATEYE_{safe}{{stat="avg_ms"}} {stats["avg_ms"]}')
        lines.append(f'CATEYE_{safe}{{stat="count"}} {stats["count"]}')
        lines.append(f'CATEYE_{safe}{{stat="total_ms"}} {stats["total_ms"]}')

    memory = get_memory()
    state = memory.get_state()
    lines.append("# HELP CATEYE_intelligence Intelligence layer metrics")
    lines.append("# TYPE CATEYE_intelligence gauge")
    lines.append(f'CATEYE_intelligence{{stat="patterns_learned"}} {state.get("total_patterns_learned", 0)}')
    lines.append(
        f'CATEYE_intelligence{{stat="recommendations_generated"}} {state.get("total_recommendations_generated", 0)}'
    )
    lines.append(f'CATEYE_intelligence{{stat="snapshots_created"}} {state.get("total_snapshots_created", 0)}')
    lines.append(f'CATEYE_intelligence{{stat="analysis_time_ms"}} {state.get("total_analysis_time_ms", 0.0)}')

    from cores.confidence import audit_verdicts
    from cores.replay import list_replay_targets
    from cores.review_queue import build_review_queue
    from cores.timeline import build_timeline

    try:
        tl = build_timeline(limit=1)
        timeline_count = tl.to_dict().get("total_events", 0)
        replay_targets = len(list_replay_targets())
        conf = audit_verdicts(limit=1)
        confidence_count = conf.total_audited
        rq = build_review_queue(limit=1)
        review_count = rq.total_items
    except Exception:
        timeline_count = replay_targets = confidence_count = review_count = 0

    lines.append("# HELP CATEYE_system System hardening layer metrics")
    lines.append("# TYPE CATEYE_system gauge")
    lines.append(f'CATEYE_system{{stat="timeline_events"}} {timeline_count}')
    lines.append(f'CATEYE_system{{stat="replays_generated"}} {replay_targets}')
    lines.append(f'CATEYE_system{{stat="confidence_audits"}} {confidence_count}')
    lines.append(f'CATEYE_system{{stat="review_queue_items"}} {review_count}')

    # ── Opportunity Intelligence metrics ────────────────────────────
    try:
        from cores.opportunity import get_engine

        engine = get_engine()
        opp_metrics = engine.get_metrics()
        lines.append("# HELP CATEYE_opportunity Opportunity intelligence layer metrics")
        lines.append("# TYPE CATEYE_opportunity gauge")
        lines.append(f'CATEYE_opportunity{{stat="total"}} {opp_metrics.get("opportunities_total", 0)}')
        lines.append(f'CATEYE_opportunity{{stat="providers_active"}} {opp_metrics.get("providers_active", 0)}')
        lines.append(f'CATEYE_opportunity{{stat="average_score"}} {opp_metrics.get("average_score", 0)}')
        for prio, count in opp_metrics.get("by_priority", {}).items():
            lines.append(f'CATEYE_opportunity{{stat="priority",category="{prio}"}} {count}')
        for cat, count in opp_metrics.get("by_category", {}).items():
            lines.append(f'CATEYE_opportunity{{stat="category",category="{cat}"}} {count}')
    except Exception as exc:
        logger.warning("Failed to collect opportunity metrics: %s", exc)

    # ── Execution Layer metrics ─────────────────────────────────────
    try:
        from cores.actions.execution_tracker import get_execution_tracker

        et = get_execution_tracker()
        estats = et.get_stats()
        lines.append("# HELP CATEYE_execution Execution layer metrics")
        lines.append("# TYPE CATEYE_execution gauge")
        lines.append(f'CATEYE_execution{{stat="total"}} {estats.get("total_executions", 0)}')
        for atype, astats in estats.get("by_type", {}).items():
            safe_t = atype.replace(" ", "_").replace("-", "_")
            lines.append(f'CATEYE_execution{{stat="avg_score",type="{safe_t}"}} {astats.get("avg_score", 0)}')
            lines.append(f'CATEYE_execution{{stat="avg_duration_ms",type="{safe_t}"}} {astats.get("avg_duration", 0)}')
            lines.append(f'CATEYE_execution{{stat="errors",type="{safe_t}"}} {astats.get("errors", 0)}')

        from cores.accountability.system_scorecard import get_system_scorecard

        sc = get_system_scorecard()
        latest = sc.get_latest()
        if latest:
            lines.append(f'CATEYE_execution{{stat="success_rate"}} {latest.get("success_rate", 0)}')
            lines.append(f'CATEYE_execution{{stat="avg_outcome_score"}} {latest.get("avg_outcome_score", 0)}')
            lines.append(f'CATEYE_execution{{stat="active_decisions"}} {latest.get("active_decisions", 0)}')
            lines.append(f'CATEYE_execution{{stat="memory_usage"}} {latest.get("memory_usage", 0)}')

        from cores.memory.insight_archive import get_insight_archive

        ia = get_insight_archive()
        lines.append(f'CATEYE_execution{{stat="insights_total"}} {ia.total_count()}')

        from cores.explainability.explanation_engine import get_explanation_engine

        ee = get_explanation_engine()
        lines.append(f'CATEYE_execution{{stat="explanations"}} {ee.count()}')

        from cores.explainability.decision_trace import get_decision_trace

        dt = get_decision_trace()
        lines.append(f'CATEYE_execution{{stat="decision_traces"}} {dt.count()}')
    except Exception as exc:
        logger.warning("Failed to collect execution metrics: %s", exc)

    return "\n".join(lines) + "\n"
