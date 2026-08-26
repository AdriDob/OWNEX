import argparse
import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import PlainTextResponse

from api.middleware.auth_middleware import AuthMiddleware
from api.middleware.csrf_middleware import CSRFMiddleware
from api.middleware.error_handling import ErrorHandlingMiddleware, SecurityHeadersMiddleware, http_exception_handler
from api.middleware.rate_limit_middleware import RateLimitMiddleware
from api.routers import (
    accounts_hub,
    activity,
    agent_coordinator,
    agents_router,
    ai_security,
    alerts,
    assistant,
    atlas_app,
    atlas_cycle,
    attack,
    attack_surface,
    auth,
    auth_user,
    auth_users,
    authhub,
    auto_apply,
    auto_submit,
    bank_payout,
    bounty_pipeline,
    canonical,
    capability_expansion,
    career,
    commands,
    connections,
    contracts,
    control,
    copilot,
    credentials_rotation,
    crypto,
    cycles,
    daily,
    daily_mode,
    decision,
    device,
    devin,
    differential_intelligence,
    digest,
    direct_work,
    discovery,
    dispute,
    economic,
    endpoints,
    enhanced_personalization,
    evidence,
    evolution,
    execution,
    execution_queue,
    files,
    finance,
    financial_sync,
    financial_truth,
    findings,
    fiverr,
    forge_app,
    forge_cycle,
    hunt,
    hunter,
    hypotheses,
    identity,
    identity_center,
    idor,
    infinite_sources,
    intel,
    intelligence,
    investigations,
    investment,
    knowledge_bridge,
    license,
    life,
    life_management,
    market_intelligence,
    mercenary_filter,
    merlin,
    micro,
    mission,
    mobile,
    mobile_approvals,
    modes,
    notifications,
    oar,
    obsidian_sync,
    offensive,
    offensive_web3,
    onboarding,
    opensource,
    operations,
    opportunities,
    opportunity_feedback,
    opportunity_intelligence,
    opportunity_score,
    orchestrator,
    orion,
    orion_cli,
    osint,
    outlook,
    overview,
    payment_compat,
    personal_infrastructure,
    pipeline,
    platforms,
    productivity,
    profile_kit,
    progressive_scaling,
    project_dashboard,
    pulse_app,
    pulse_cycle,
    qa_cycle,
    quick_wins,
    recon,
    remote_control,
    report_pipeline,
    reports,
    reports_acceptance,
    reports_quality,
    result_based,
    revenue,
    revenue_app,
    revenue_multiplier,
    revenue_timeline,
    roi,
    sandbox,
    scans,
    screenshots,
    security_cycle,
    self_improvement,
    settings_ai,
    settings_runtime,
    settings_unified,
    setup,
    stability,
    supabase,
    sync,
    system,
    system_state,
    target_identity,
    targets,
    telegram_bot,
    terminal_ws,
    trading,
    ultra_fast_income,
    validation,
    vault_app,
    vault_cycle,
    verdicts,
    version,
    version_backup,
    voice,
    voice_commands,
    wear_os,
    webhooks,
    ws,
    zap,
    zero_barrier,
)
from api.routers.investment import register_investment_capabilities as _reg_inv_caps
from cores.env.config import get_config
from cores.learning.router import router as learning_router
from cores.log_config import setup_logging
from database import db


# ── CLI Argument Parsing ─────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(description="OWNEX Backend - FastAPI Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on (default: 8000)")
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Data directory for database and logs (default: %%LOCALAPPDATA%%\\OWNEX on Windows, ~/.ownex on Linux)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level (default: INFO)",
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    return parser.parse_known_args()


# Parse args immediately on module load.
# parse_known_args(): this module is imported by tooling whose argv is NOT
# ours (pytest, IDE runners) — unknown flags must be ignored, never fatal.
_ARGS, _UNKNOWN_ARGS = parse_args()

# Configure data directory BEFORE any imports that might use it
if _ARGS.data_dir:
    data_dir = Path(_ARGS.data_dir)
else:
    # Platform-specific default
    if sys.platform == "win32":
        data_dir = Path(os.path.expandvars(r"%LOCALAPPDATA%\OWNEX"))
    else:
        data_dir = Path.home() / ".ownex"

# Set environment variables for downstream code
os.environ["CATEYE_DATA_DIR"] = str(data_dir)
_DB_PATH = data_dir / "database" / "cateye.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

# Configure logging
logging.basicConfig(
    level=getattr(logging, _ARGS.log_level),
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
    stream=sys.stdout,
)

setup_logging()

logger = logging.getLogger("ownex.api")
logger.info(f"[BOOT] Data directory: {data_dir}")
logger.info(f"[BOOT] Database path: {_DB_PATH}")

# Track background tasks to prevent silent crashes and allow cancellation
_background_tasks: set[asyncio.Task] = set()
_shutdown_requested = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import all models before init_db() so SQLAlchemy metadata registers all tables
    from cores.learning import profile as _learning_models  # noqa: F401 — registers InvestigatorProfile, LearningEvent
    from cores.targets import models as _targets_models  # noqa: F401 — registers TargetIntel, Scope
    from database import models as _core_models  # noqa: F401 — registers User, MemoryRecord, etc.

    db.init_db()
    logger.info("[BOOT] Database initialized")

    # Stale-scan recovery at boot (audit P1-2): scans 'running' >6h de un
    # proceso muerto se marcan failed ANTES de que arranque cualquier loop.
    try:
        from cores.orchestrator.scan_service import recover_stale_scans

        recovered = recover_stale_scans()
        if recovered:
            logger.warning("[BOOT] Recovered %d stale scans (running > 6h)", recovered)
    except Exception as exc:
        logger.warning("[BOOT] Stale scan recovery skipped: %s", exc)

    # Initialize event bus (required for everything else)
    from cores.events.event_bus import get_event_bus

    bus = get_event_bus()
    if hasattr(bus, "disable_bridge"):
        bus.disable_bridge()
    logger.info("[BOOT] EventBus ready")

    # ── SCHEDULE BACKGROUND INIT ──
    # All heavy initialization runs as a background task so the API
    # becomes immediately responsive. ~16s of sync init moved here.
    from api.lifespan import _background_tasks, run_background_init

    bg_task = asyncio.create_task(run_background_init(app, bus))
    _background_tasks.add(bg_task)
    logger.info("[BOOT] Background initialization scheduled")

    yield

    logger.info("[SHUTDOWN] Starting graceful shutdown...")

    # Cancel background init task
    for task in list(_background_tasks):
        if not task.done():
            task.cancel()
    _background_tasks.clear()

    # Quick exit if shutdown was requested via API (sidecar mode)
    if _shutdown_requested:
        logger.info("[SHUTDOWN] Quick exit for sidecar shutdown")
        return

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
        recovery_engine = get_recovery_engine()
        recovery_engine.stop()
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

    # Stop schedulers via module singletons
    try:
        import api.scheduler as _sm

        if getattr(_sm, "scheduler_instance", None) is not None:
            await _sm.scheduler_instance.stop()
    except Exception:
        pass

    # Stop Notification Poller
    try:
        from api.routers.operations import stop_notification_poller

        stop_notification_poller()
    except Exception:
        pass

    logger.info("[SHUTDOWN] Complete")


# Read version from VERSION file (single source of truth)
_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
_APP_VERSION = _VERSION_FILE.read_text().strip() if _VERSION_FILE.is_file() else "0.0.0"

app = FastAPI(
    title="OWNEX API",
    description="Bug Bounty Intelligence Platform — automated reconnaissance, analysis, and reporting.",
    version=_APP_VERSION,
    lifespan=lifespan,
    contact={"name": "CATEYE Team", "url": "https://github.com/AdriDob/rastrohunteralpha"},
    license_info={"name": "Proprietary"},
    swagger_ui_parameters={"deepLinking": True, "displayRequestDuration": True},
)

# Production: restrict to local origins + Tauri bundle origins.
# Dev mode (OWNEX_DESKTOP/CATEYE_DESKTOP not set) uses * but without
# credentials per Fetch spec. The packaged sidecar always sets
# OWNEX_DESKTOP=1 (start_backend.py), so the restrictive branch below is
# what the Windows bundle actually runs.
_TAURI_ORIGINS = (
    "http://tauri.localhost",  # WebView2 production origin (Windows)
    "https://tauri.localhost",  # https variant of the same
    "tauri://localhost",  # custom-scheme variant (non-Windows builds)
    "app://",  # legacy pywebview protocol (Gen1 launcher)
)


def configure_cors(app: FastAPI) -> None:
    """Single source of truth for CORS wiring (see tests/test_cors_tauri.py)."""
    _allow_all = not get_config().desktop
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"]
        if _allow_all
        else [
            "http://127.0.0.1",
            "http://localhost",
            *_TAURI_ORIGINS,
        ],
        allow_credentials=not _allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )


configure_cors(app)


@app.get("/", include_in_schema=False)
async def root() -> dict:
    """API-only root (owner directive 2026-08-25).

    The UI never lives here: it ships inside the Tauri bundle
    (tauri://localhost) or runs via the Vite dev server. This route
    exists so hitting the bare port returns an unambiguous JSON answer
    instead of a 404 that could be mistaken for a missing frontend.
    """
    return {
        "service": "OWNEX API",
        "version": _APP_VERSION,
        "ui": "not-served-here (desktop bundle / vite dev)",
        "docs": "/api/docs",
        "health": "/api/health",
    }


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

app.add_exception_handler(HTTPException, http_exception_handler)


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
app.include_router(sandbox.router)
app.include_router(dispute.router)
app.include_router(obsidian_sync.router)
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
app.include_router(opportunity_feedback.router)
app.include_router(opportunity_intelligence.router)
app.include_router(mercenary_filter.router)
app.include_router(auto_submit.router)
app.include_router(bounty_pipeline.router)
app.include_router(agent_coordinator.router)
app.include_router(auth.router)
app.include_router(auth_users.router)
app.include_router(auth_user.router)
app.include_router(sync.router)
app.include_router(notifications.router)
app.include_router(outlook.router)
app.include_router(mobile.router)
app.include_router(mobile_approvals.router)
app.include_router(contracts.router)
app.include_router(cycles.router)
app.include_router(forge_app.router)
app.include_router(pulse_app.router)
app.include_router(vault_app.router)
app.include_router(atlas_app.router)
app.include_router(revenue_app.router)
app.include_router(system_state.router)
app.include_router(stability.router)
app.include_router(daily_mode.router)
app.include_router(daily.router)
app.include_router(discovery.router)
app.include_router(orchestrator.router)
app.include_router(identity.router)
app.include_router(identity_center.router)
app.include_router(target_identity.router)

app.include_router(files.router)
app.include_router(life.router)
app.include_router(control.router)
app.include_router(copilot.router)
app.include_router(execution.router)
app.include_router(execution_queue.router)
app.include_router(license.router)
app.include_router(learning_router)
app.include_router(project_dashboard.router)
app.include_router(ws.router)
app.include_router(terminal_ws.router)
app.include_router(trading.router)
app.include_router(idor.router)
app.include_router(offensive.router)
app.include_router(offensive_web3.router)
app.include_router(investigations.router)
app.include_router(settings_ai.router)
app.include_router(personal_infrastructure.router)
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
app.include_router(progressive_scaling.router)
app.include_router(ultra_fast_income.router)
app.include_router(infinite_sources.router)
app.include_router(auto_apply.router)
app.include_router(alerts.router)
app.include_router(modes.router)
app.include_router(activity.router)
app.include_router(crypto.router)
app.include_router(credentials_rotation.router)
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
app.include_router(voice_commands.router)
app.include_router(opensource.router)
app.include_router(zero_barrier.router)
app.include_router(direct_work.router)
app.include_router(revenue_timeline.router)
app.include_router(fiverr.router)
app.include_router(decision.router)
app.include_router(device.router)
app.include_router(result_based.router)
app.include_router(career.router)
app.include_router(oar.router)
app.include_router(remote_control.router)
app.include_router(capability_expansion.router)
app.include_router(capability_expansion.capabilities_router)
app.include_router(version_backup.router)
app.include_router(finance.router)  # Personal Finance Command Center

# Setup router
app.include_router(setup.router)
app.include_router(supabase.router)
app.include_router(enhanced_personalization.router)

# Productivity router
app.include_router(productivity.router)

# Life Management router
app.include_router(life_management.router)

# Devin Tool router
app.include_router(devin.router)

# Onboarding router
app.include_router(onboarding.router)

# Wear OS router
app.include_router(wear_os.router)

# Security Cycle router
app.include_router(security_cycle.router)
app.include_router(self_improvement.router)
app.include_router(forge_cycle.router)
app.include_router(pulse_cycle.router)
app.include_router(vault_cycle.router)
app.include_router(atlas_cycle.router)
app.include_router(qa_cycle.router)
app.include_router(profile_kit.router)
from api.routers.daily_digest import router as daily_digest_router
app.include_router(daily_digest_router)
app.include_router(knowledge_bridge.router)
app.include_router(payment_compat.router)
# ── ORION Platform: core + app routers ──
# NOT fail-fast silencioso: si esto explota, el backend arranca sin sus rutas
# (404 masivos intermitentes). El error debe ser visible en boot.
from core.api.routers import router as core_router  # noqa: E402

app.include_router(core_router)
from core.app_registry import get_app_registry  # noqa: E402

registry = get_app_registry()
registry.mount_routers(app)
logger.info("[ORION] Core + app routers mounted")


APP_VERSION = _APP_VERSION


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "OWNEX API", "version": APP_VERSION}


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
async def get_version():
    return {"version": APP_VERSION, "app": "OWNEX API", "build": APP_VERSION}


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


@app.post("/api/shutdown")
async def shutdown():
    """Graceful shutdown endpoint for sidecar management."""
    global _shutdown_requested
    _shutdown_requested = True
    logger.info("[SHUTDOWN] Shutdown requested via API")
    # Give lifespan time to cleanup, then exit
    asyncio.create_task(_delayed_exit())
    return {"status": "shutting_down"}


async def _delayed_exit():
    """Delay exit to allow response to be sent."""
    await asyncio.sleep(0.5)
    logger.info("[SHUTDOWN] Exiting process")
    sys.exit(0)


def main():
    """Entry point for standalone backend execution."""
    import uvicorn

    logger.info(f"[BOOT] Starting OWNEX Backend on {_ARGS.host}:{_ARGS.port}")
    uvicorn.run(
        "api.main:app",
        host=_ARGS.host,
        port=_ARGS.port,
        log_level=_ARGS.log_level.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
