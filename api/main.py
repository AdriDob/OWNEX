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
    ai_security,
    assistant,
    atlas_app,
    attack,
    attack_surface,
    auth,
    auth_users,
    authhub,
    bank_payout,
    canonical,
    commands,
    connections,
    contracts,
    crypto,
    cycles,
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
    forge_app,
    hunt,
    hunter,
    hypotheses,
    identity,
    identity_center,
    idor,
    intel,
    intelligence,
    investigations,
    investment,
    license,
    market_intelligence,
    merlin,
    micro,
    mission,
    mobile,
    notifications,
    offensive,
    offensive_web3,
    operations,
    opportunities,
    opportunity_intelligence,
    opportunity_score,
    orchestrator,
    orion,
    orion_cli,
    osint,
    overview,
    pipeline,
    platforms,
    project_dashboard,
    pulse_app,
    quick_wins,
    recon,
    report_pipeline,
    reports,
    reports_acceptance,
    reports_quality,
    revenue,
    revenue_app,
    revenue_multiplier,
    roi,
    scans,
    screenshots,
    security_cycle,
    settings_ai,
    settings_runtime,
    settings_unified,
    sync,
    system,
    system_state,
    target_identity,
    targets,
    telegram_bot,
    terminal_ws,
    validation,
    vault_app,
    verdicts,
    version,
    voice,
    webhooks,
    ws,
    zap,
    opensource,
    zero_barrier,
    version_backup,
)
from api.routers.investment import register_investment_capabilities as _reg_inv_caps
from cores.env.config import get_config
from cores.learning.router import router as learning_router
from cores.log_config import setup_logging
from database import db

setup_logging()

logger = logging.getLogger("ownex.api")

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
    # ── Initialize Event Bus (persistent core) ─────────────────────────────────
    from cores.events.event_bus import get_event_bus

    bus = get_event_bus()

    # Legacy bridge: disable for unified EventBus (CoreEventBus is deprecated)
    if hasattr(bus, "disable_bridge"):
        bus.disable_bridge()

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

    # Initialize TempManager
    try:
        from core.system.temp_manager import get_temp_manager

        get_temp_manager()
        logger.info("TempManager initialized")
    except Exception as exc:
        logger.warning("TempManager init failed (non-fatal): %s", exc)

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

    # Initialize Self-Healing System
    try:
        from core.self_healing.system import get_self_healing_system

        healing_system = get_self_healing_system()
        results = healing_system.validate_system()
        logger.info("Self-healing system initialized: %s", results["overall_status"])
    except Exception as exc:
        logger.warning("Self-healing system init failed (non-fatal): %s", exc)

    # Initialize Self-Update System
    try:
        from core.self_healing.update import SelfUpdateSystem

        update_system = SelfUpdateSystem()
        update_available, update_msg = update_system.check_for_updates()
        logger.info("Self-update check: %s", update_msg)
        if update_available and os.getenv("AUTO_UPDATE_ENABLED", "false").lower() == "true":  # noqa: F823
            logger.info("Auto-update enabled, performing update...")
            success, msg, logs = update_system.perform_update()
            for log in logs:
                logger.info("[UPDATE] %s", log)
            if success:
                logger.info("Auto-update completed: %s", msg)
            else:
                logger.warning("Auto-update failed: %s", msg)
    except Exception as exc:
        logger.warning("Self-update system init failed (non-fatal): %s", exc)

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
        import api.scheduler as sched_mod
        from api.scheduler import ScanScheduler

        scheduler = ScanScheduler(interval_minutes=get_config().scan_interval)
        sched_mod.scheduler_instance = scheduler
        t = asyncio.create_task(scheduler.start())
        t.add_done_callback(_background_tasks.discard)
        _background_tasks.add(t)
        logger.info("Scan scheduler started")
    except Exception as exc:
        logger.warning("Scan scheduler failed to start (non-fatal): %s", exc)

    # Initialize Operations System (24/7 watchdog, recovery, backups, cleanup, doctor)
    try:
        from cores.operations import initialize_operations

        ops = await initialize_operations()
        logger.info("Operations system initialized (watchdog, recovery, backups, cleanup, doctor)")
    except Exception as exc:
        logger.warning("Operations system init failed (non-fatal): %s", exc)

    # ── Initialize loop engines ──
    try:
        from core.loop.startup import init_loop_engines

        result = init_loop_engines(scheduler=scheduler, event_bus=bus)
        logger.info(
            "Loop engines: %d registered, %d errors",
            len(result["registered"]),
            len(result["errors"]),
        )
    except Exception as exc:
        logger.warning("Loop engines init failed (non-fatal): %s", exc)

    # ── Initialize Universal Sensor Network ──
    try:
        from core.sensors.observation_engine import ObservationEngine

        obs_engine = ObservationEngine(event_bus=bus)
        await obs_engine.initialize()

        # Register PlaywrightSensor
        try:
            from extensions.playwright.playwright_sensor import PlaywrightSensor

            pw_sensor = PlaywrightSensor()
            await pw_sensor.initialize()
            obs_engine.register(pw_sensor)
            logger.info("[SENSORS] PlaywrightSensor registered")
        except Exception as exc:
            logger.warning("[SENSORS] PlaywrightSensor registration failed (non-fatal): %s", exc)

        # Register other extensions as sensors
        for ext in ("ai_assist", "mcp", "git_connector", "aider_connector"):
            try:
                mod = __import__(f"extensions.{ext}", fromlist=["register_sensors"])
                if hasattr(mod, "register_sensors"):
                    mod.register_sensors(obs_engine)
            except Exception:
                pass

        app.state.observation_engine = obs_engine
        logger.info("[SENSORS] ObservationEngine initialized with %d sensors", len(obs_engine.sensors))
    except Exception as exc:
        logger.warning("[SENSORS] ObservationEngine init failed (non-fatal): %s", exc)

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
            register_telegram_channel,
            register_whatsapp_channel,
            register_ws_forwarder,
        )

        register_db_bridge()
        register_desktop_channel()
        register_discord_channel()
        register_email_channel()
        register_fcm_channel()
        register_mobile_channel()
        register_telegram_channel()
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

    # Wire IntelligentNotificationManager -> EventBus
    try:
        from core.notifications.intelligent import get_intelligent_notifier
        from cores.events.event_bus import get_event_bus

        bus = get_event_bus()
        notifier = get_intelligent_notifier()

        def _smart_notify(event_type: str, data: dict | None = None) -> None:
            notifier.route_to_user(event_type, data or {})

        key_events = [
            "finding:created",
            "finding:confirmed",
            "finding:status_changed",
            "opportunity:found",
            "report:generated",
            "report:accepted",
            "report:rejected",
            "system:error",
            "system:degraded",
            "system:alert",
            "financial:payout_received",
            "financial:payout_confirmed",
            "revenue:payout_recorded",
            "acceptance:outcome:recorded",
        ]
        for evt in key_events:
            bus.subscribe(evt, _smart_notify)
        logger.info("Smart notification bridge started (%d events)", len(key_events))
    except Exception as exc:
        logger.warning("Smart notification bridge failed (non-fatal): %s", exc)

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
            try:
                from core.auto_submit.pipeline import get_auto_submit_pipeline

                pipeline = get_auto_submit_pipeline()
                result = pipeline.process_finding(payload["id"])
                action = result.get("action", "unknown")
                logger.info("[AUTO-SUBMIT] Finding %s → %s (score=%.1f)", payload["id"], action, result.get("score", 0))
            except Exception as exc:
                logger.warning("[AUTO-SUBMIT] Pipeline failed for finding %s: %s", payload.get("id"), exc)

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

        # VerdictAutoLearner: bridge FeedbackTuner -> AcceptanceLearner
        try:
            from core.learning.verdict_learner import get_verdict_learner

            _vl = get_verdict_learner()

            def _verdict_handler(event_type, payload):
                _vl.handle_finding_status_changed(payload)

            bus.subscribe("finding:status_changed", _verdict_handler)
            logger.info("[BOOT] VerdictAutoLearner subscriber registered")
        except Exception as exc:
            logger.warning("[BOOT] VerdictAutoLearner init error: %s", exc)

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
            from core.copilot.orion_context import get_orion_context

            _set_copilot(_copilot)
            from database import db as _db

            get_orion_context(db_factory=_db.SessionLocal)
            app.include_router(copilot_router)
            logger.info("[BOOT] Copilot API router + OrionContext registered")
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

    # Bridge EventBus → AgentBus (scheduler pipeline → coordinator)
    try:
        from cores.agents.bus import bridge_eventbus_to_agent_bus

        bridge_eventbus_to_agent_bus()
        logger.info("[BOOT] EventBus → AgentBus bridge started")
    except Exception as exc:
        logger.warning("EventBus → AgentBus bridge failed (non-fatal): %s", exc)

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
        from core.scheduler.scheduler import JobDefinition, get_core_scheduler
        from cores.events.event_bus import get_event_bus

        registry = get_app_registry()
        registry.discover()

        # Register built-in capabilities so COPILOT and agents can discover them
        try:
            from core.capabilities.registration import register_all_capabilities

            registered = register_all_capabilities()
            logger.info("[BOOT] Registered %d capability entries", registered)
        except Exception as exc:
            logger.warning("Capability registration failed (non-fatal): %s", exc)

        # ── OWNEX Revenue Engine: startup ──
        try:
            from core.revenue.engine import RevenueEngine

            revenue_engine = RevenueEngine()
            logger.info("[BOOT] Revenue Engine ready")
        except Exception as exc:
            logger.warning("Revenue Engine init failed (non-fatal): %s", exc)

        # ── OWNEX Self-Heal: validate and repair ──
        try:
            from core.self_heal.engine import SelfHealEngine

            healer = SelfHealEngine()
            heal_report = healer.heal()
            if heal_report.fixed > 0:
                logger.info("[BOOT] Self-heal applied %d fixes", heal_report.fixed)
        except Exception as exc:
            logger.warning("Self-heal init failed (non-fatal): %s", exc)

        # ── OWNEX Self-Update: check for updates ──
        try:
            from core.self_update.engine import SelfUpdateEngine

            updater = SelfUpdateEngine()
            update_info = updater.check_for_update()
            if update_info.has_update:
                logger.info("[BOOT] Update available: %d commits behind", update_info.commits_behind)
        except Exception as exc:
            logger.warning("Self-update check failed (non-fatal): %s", exc)

        # ── OWNEX Self-Healing System (comprehensive validation) ──
        try:
            from core.self_healing.system import get_self_healing_system

            self_healing = get_self_healing_system()
            heal_results = self_healing.validate_system()
            if heal_results["overall_status"] == "degraded":
                logger.warning(
                    "[BOOT] Self-healing: system degraded, %d repairs attempted",
                    heal_results.get("repairs_attempted", 0),
                )
            else:
                logger.info("[BOOT] Self-healing: system healthy")
        except Exception as exc:
            logger.warning("Self-healing system init failed (non-fatal): %s", exc)

        # ── OWNEX Self-Update System (auto-update on startup if enabled) ──
        try:
            from core.self_update.system import get_self_update_system

            self_update = get_self_update_system()
            update_check = self_update.check_for_updates()
            if update_check.get("update_available"):
                logger.info("[BOOT] Self-update: %s", "Updates available")
                if update_check.get("auto_update", False):
                    update_result = self_update.perform_full_update()
                    logger.info("[BOOT] Self-update result: %s", update_result.get("success"))
        except Exception as exc:
            logger.warning("Self-update system init failed (non-fatal): %s", exc)

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
        core_bus = get_event_bus()
        orion_scheduler = get_core_scheduler()

        def _on_job_due(job: JobDefinition) -> None:
            core_bus.publish("scheduler:job_due", job_id=job.job_id, app_id=job.app_id)

        orion_scheduler.set_job_handler(_on_job_due)
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
        from core.integrations.registry import init_integration_registry

        init_integration_registry(ext_reg)
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
        from cores.events.store import get_event_store

        _event_store = get_event_store()
        logger.info("[EVENT] Event Store initialized (%d events)", _event_store.count())

        # 2. Register capabilities for connectors (late init for early-boot connectors)
        from core.capabilities.registry import get_capability_registry

        _creg = get_capability_registry()
        logger.info(
            "[CAP] Capability Registry: %d capabilities from %d modules", len(_creg.list_capabilities()), _creg.count()
        )

        # 2b. Register hunter bridge capabilities (claude-bug-bounty, web3, MCP)
        try:
            from core.integrations.ext.hunter_bridge import HUNTER_TO_RASTRO_VULN, WEB3_VULN_CLASSES, status_summary

            _hunter_status = status_summary()
            for name, info in _hunter_status.items():
                if name == "checked_at":
                    continue
                _creg.register(
                    "hunt_vulnerability",
                    f"core.integrations.ext.hunter_bridge.{name}",
                    {
                        "vuln_classes": len(HUNTER_TO_RASTRO_VULN) if "claude" in name else len(WEB3_VULN_CLASSES),
                        "installed": info.get("installed", False),
                    },
                    description=f"{name}: bug bounty hunting bridge",
                )
                logger.info(
                    "[HUNTER] Registered capability: hunt_vulnerability from %s (installed=%s)",
                    name,
                    info.get("installed", False),
                )
            _creg.register(
                "scan_web3_contracts",
                "core.integrations.ext.hunter_bridge.web3_bug_bounty_skills",
                {"vuln_classes": WEB3_VULN_CLASSES},
                description="Web3 smart contract vulnerability scanning via Immunefi-derived skills",
            )
            logger.info(
                "[HUNTER] Hunter bridge initialized: %d integrations",
                sum(1 for k, v in _hunter_status.items() if k != "checked_at"),
            )
        except Exception as exc:
            logger.warning("[HUNTER] Hunter bridge init error: %s", exc)

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

        # ── Telegram Bridge ──────────────────────────────────────────
        def _telegram_handler(event_type, payload):
            from core.notifications.telegram.bridge import handle_event

            handle_event(event_type, **payload)

        for _ev in (
            "finding:created",
            "finding:confirmed",
            "finding:status_changed",
            "report:generated",
            "report:accepted",
            "report:rejected",
            "revenue:payout_recorded",
            "revenue:report_submitted",
            "revenue:status_changed",
            "revenue:sync_completed",
            "system:error",
            "system:degraded",
            "system:alert",
            "opportunity:found",
            "opportunity:updated",
            "quick_win:detected",
            "execution:approval:requested",
            "execution:workflow:completed",
            "execution:workflow:failed",
            "hermes:security:blocked",
            "hermes:permission:required",
            "hermes:action:completed",
            "hermes:action:failed",
            "recovery:started",
            "recovery:success",
            "recovery:failed",
            "anomaly:detected",
            "f1:alert",
            "f1:question",
            "financial:payout_received",
            "intel:signal:detected",
            "intel:opportunity:assessed",
            "intel:brief:generated",
        ):
            bus.subscribe(_ev, _telegram_handler)
        logger.info("[TELEGRAM] Bridge subscriber registered for %d event types", 33)

        logger.info("[EVENT] Event subscribers registered (opportunity, recovery, telegram)")
    except Exception as exc:
        logger.warning("[BOOT] Event pipeline init failed (non-fatal): %s", exc)

    # ── Initialize 24/7 Operations System ──
    try:
        from cores.operations import initialize_operations

        ops_manager = await initialize_operations()
        app.state.operations_manager = ops_manager
        logger.info("[OPS] Operations system initialized (watchdog, backups, cleanup, doctor)")
    except Exception as exc:
        logger.warning("[OPS] Operations system init failed (non-fatal): %s", exc)

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

    # Stop 24/7 Operations System
    try:
        from cores.operations import get_operations_manager

        ops_manager = get_operations_manager()
        await ops_manager.stop()
        logger.info("[OPS] Operations system stopped")
    except Exception as exc:
        logger.warning("[OPS] Operations system stop error: %s", exc)

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
app.include_router(reports_acceptance.router)
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
app.include_router(commands.router)
app.include_router(canonical.router)
app.include_router(intelligence.router)
app.include_router(market_intelligence.router)
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
app.include_router(cycles.router)
app.include_router(forge_app.router)
app.include_router(pulse_app.router)
app.include_router(vault_app.router)
app.include_router(atlas_app.router)
app.include_router(revenue_app.router)
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
app.include_router(terminal_ws.router)
app.include_router(idor.router)
app.include_router(offensive.router)
app.include_router(offensive_web3.router)
app.include_router(investigations.router)
app.include_router(settings_ai.router)
app.include_router(settings_runtime.router)
app.include_router(settings_unified.router)
app.include_router(webhooks.router)
app.include_router(orion.router)
app.include_router(orion_cli.router)
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
app.include_router(merlin.router)
app.include_router(revenue_multiplier.router)
app.include_router(investment.router)
_reg_inv_caps()
app.include_router(osint.router)
app.include_router(hunt.router)
app.include_router(hunter.router)
app.include_router(recon.router)
app.include_router(telegram_bot.router)
app.include_router(version.router)
app.include_router(intel.router)
app.include_router(ai_security.router)
app.include_router(opportunity_score.router)
app.include_router(report_pipeline.router)
app.include_router(voice.router)
app.include_router(opensource.router)
app.include_router(zero_barrier.router)
app.include_router(version_backup.router)

# Security Cycle router
app.include_router(security_cycle.router)

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
    return {"version": APP_VERSION, "app": "OWNEX API", "build": "4.6.0"}


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
    """Prometheus-style metrics endpoint using prometheus-client."""
    from prometheus_client import generate_latest

    from cores.prometheus_registry import get_registry

    return generate_latest(get_registry())
