import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import PlainTextResponse

from api.middleware.auth_middleware import AuthMiddleware
from api.middleware.error_handling import ErrorHandlingMiddleware
from api.middleware.rate_limit_middleware import RateLimitMiddleware
from api.routers import (
    accounts_hub,
    agents_router,
    assistant,
    attack,
    attack_surface,
    auth,
    auth_users,
    canonical,
    connections,
    contracts,
    crypto,
    daily,
    differential_intelligence,
    digest,
    economic,
    endpoints,
    evidence,
    execution,
    financial_truth,
    findings,
    hunt,
    hypotheses,
    identity,
    identity_center,
    idor,
    intelligence,
    investigations,
    license,
    mobile,
    notifications,
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

logger = logging.getLogger("catseye.api")


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

    # Discover opportunities on startup
    try:
        from cores.opportunity import get_engine
        opp_engine = get_engine()
        opp_count = len(opp_engine.discover_all())
        logger.info("Opportunity engine initialized with %d opportunities", opp_count)
    except Exception as exc:
        logger.warning("Opportunity engine discovery failed (non-fatal): %s", exc)

    logger.info("Execution layer fully initialized")

    # Start background scan scheduler
    scheduler = None
    try:
        from api.scheduler import ScanScheduler
        scheduler = ScanScheduler(interval_minutes=get_config().scan_interval)
        asyncio.create_task(scheduler.start())
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
            register_email_channel,
            register_event_bridge,
            register_fcm_channel,
            register_gmail_channel,
            register_whatsapp_channel,
            register_ws_forwarder,
        )
        register_db_bridge()
        register_desktop_channel()
        register_email_channel()
        register_fcm_channel()
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

    # Start Multi-Agent system
    try:
        from cores.agents import start_all_agents
        agents = start_all_agents()
        logger.info("[BOOT] %d agents started", len(agents))
    except Exception as exc:
        logger.warning("Multi-Agent system failed to start (non-fatal): %s", exc)

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
# Dev mode (CATEYE_DESKTOP not set) also keeps * for hot-reload.
_allow_all = not get_config().desktop
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "app://",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(opportunities.router)
app.include_router(attack_surface.router)
app.include_router(pipeline.router)
app.include_router(quick_wins.router)
app.include_router(reports.router)
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
app.include_router(financial_truth.router)
app.include_router(crypto.router)
app.include_router(accounts_hub.router)
app.include_router(osint.router)
app.include_router(hunt.router)


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
    summary = state.get_summary() if hasattr(state, "get_summary") else None
    boot_time_val = getattr(state, "boot_time", None) or 0.0

    return {
        "status": summary.state if summary else "unknown",
        "version": APP_VERSION,
        "pid": pid,
        "uptime_seconds": time.time() - boot_time_val,
        "watchdog": watchdog.get_status() if watchdog and watchdog.is_running else {"running": False},
        "system": {
            "memory_percent": proc.memory_percent(),
            "memory_rss_mb": mem.rss / 1024 / 1024,
            "cpu_percent": proc.cpu_percent(interval=0.3),
            "num_threads": proc.num_threads(),
        },
        "pipeline": {
            "total_pipelines": len(health_data.get("pipelines", [])) if health_data else 0,
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
    except Exception:
        pass
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
    lines.append('# HELP CATEYE_intelligence Intelligence layer metrics')
    lines.append('# TYPE CATEYE_intelligence gauge')
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

    lines.append('# HELP CATEYE_system System hardening layer metrics')
    lines.append('# TYPE CATEYE_system gauge')
    lines.append(f'CATEYE_system{{stat="timeline_events"}} {timeline_count}')
    lines.append(f'CATEYE_system{{stat="replays_generated"}} {replay_targets}')
    lines.append(f'CATEYE_system{{stat="confidence_audits"}} {confidence_count}')
    lines.append(f'CATEYE_system{{stat="review_queue_items"}} {review_count}')

    # ── Opportunity Intelligence metrics ────────────────────────────
    try:
        from cores.opportunity import get_engine
        engine = get_engine()
        opp_metrics = engine.get_metrics()
        lines.append('# HELP CATEYE_opportunity Opportunity intelligence layer metrics')
        lines.append('# TYPE CATEYE_opportunity gauge')
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
        lines.append('# HELP CATEYE_execution Execution layer metrics')
        lines.append('# TYPE CATEYE_execution gauge')
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
