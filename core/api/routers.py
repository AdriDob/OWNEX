"""ORION Core — platform-level FastAPI routers.

These endpoints are mounted by the ORION Platform shell and
are independent of any specific app.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.app_registry import get_app_registry
from core.database.manager import get_db_manager
from core.decision_journal import get_decisions as dj_get
from core.decision_journal import record_outcome as dj_outcome
from core.extension.hooks import get_hook_registry
from core.extension.registry import get_extension_registry
from core.health.engine import get_health_center
from core.integrations import init_integration_registry
from core.scheduler.scheduler import get_core_scheduler
from core.secrets.manager import get_secrets_manager

logger = logging.getLogger("orion.core.api")
router = APIRouter(prefix="/api/core", tags=["core"])


@router.get("/apps")
async def list_apps():
    """List all registered ORION Platform apps."""
    registry = get_app_registry()
    apps = registry.list_apps()
    return [
        {
            "id": app.id,
            "name": app.name,
            "version": app.version,
            "description": app.description,
            "icon": app.icon,
            "order": app.order,
            "has_agent": app.agent_class is not None,
            "has_db": bool(app.db_path),
            "frontend_routes": [{"path": r["path"], "name": r["name"]} for r in app.frontend_routes],
            "widgets": app.widgets,
            "providers": app.providers,
            "requires_auth": app.requires_auth,
            "hidden": app.hidden,
        }
        for app in apps
    ]


@router.get("/status")
async def core_status():
    """Platform-wide health status."""
    registry = get_app_registry()
    db = get_db_manager()
    scheduler = get_core_scheduler()
    ext_registry = get_extension_registry()

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "apps": registry.status(),
        "extensions": ext_registry.status(),
        "databases": db.list_databases(),
        "scheduler_jobs": len(scheduler._jobs) if hasattr(scheduler, "_jobs") else 0,
    }


# ── Extension endpoints ──────────────────────────────


@router.get("/extensions")
async def list_extensions():
    """List all discovered extensions and their status."""
    registry = get_extension_registry()
    return registry.status()


@router.post("/extensions/{extension_id}/load")
async def load_extension(extension_id: str):
    """Load (activate) an extension."""
    registry = get_extension_registry()
    ok = registry.load(extension_id)
    return {"extension_id": extension_id, "loaded": ok}


@router.post("/extensions/{extension_id}/unload")
async def unload_extension(extension_id: str):
    """Unload (deactivate) an extension."""
    registry = get_extension_registry()
    ok = registry.unload(extension_id)
    return {"extension_id": extension_id, "unloaded": ok}


@router.get("/hooks")
async def list_hooks():
    """List all registered hook points and their handlers."""
    registry = get_hook_registry()
    return {"hooks": registry.list_hooks()}


@router.get("/capabilities")
async def list_capabilities():
    """List all registered capabilities."""
    from core.extension.capabilities import get_capability_registry

    registry = get_capability_registry()
    return {"capabilities": registry.list_capabilities()}


# ── Secrets endpoints ────────────────────────────────


class SecretRequest(BaseModel):
    value: str


@router.get("/secrets")
async def list_secrets():
    """List secret keys (not values)."""
    manager = get_secrets_manager()
    return {"keys": manager.list_keys()}


@router.get("/secrets/health")
async def secrets_health():
    """Check if secrets backend is available."""
    manager = get_secrets_manager()
    return {"secrets": manager.health()}


@router.get("/secrets/{key}")
async def get_secret(key: str):
    """Get a secret value."""
    manager = get_secrets_manager()
    try:
        value = manager.get_or_raise(key)
        return {"key": key, "value": value, "found": True}
    except KeyError:
        return JSONResponse({"key": key, "found": False, "error": "Secret not found"}, status_code=404)


@router.put("/secrets/{key}")
async def set_secret(key: str, body: SecretRequest):
    """Store a secret."""
    manager = get_secrets_manager()
    ok = manager.set(key, body.value)
    return {"key": key, "stored": ok}


@router.delete("/secrets/{key}")
async def delete_secret(key: str):
    """Delete a secret."""
    manager = get_secrets_manager()
    ok = manager.delete(key)
    return {"key": key, "deleted": ok}


# ── Health endpoints ─────────────────────────────────


@router.get("/health")
async def platform_health():
    """Unified health status — green / yellow / red."""
    center = get_health_center()
    summary = center.summary()
    return summary


@router.post("/health/run")
async def run_health_check():
    """Run all health checks now."""
    center = get_health_center()
    snapshot = center.run_all()
    return {
        "status": snapshot.status,
        "timestamp": snapshot.timestamp.isoformat(),
        "checks": snapshot.checks,
        "details": snapshot.details,
    }


@router.get("/health/checks")
async def list_health_checks():
    """List all registered health checks."""
    center = get_health_center()
    return {"checks": center.list_checks()}


# ── Integration Center endpoints ─────────────────────


@router.get("/integrations")
async def list_integrations():
    """List all discovered integrations with current status."""
    registry = init_integration_registry()
    registry.refresh()
    return registry.summary()


@router.get("/integrations/{name}")
async def get_integration_status(name: str):
    """Get status for a single integration."""
    registry = init_integration_registry()
    status = registry.check(name)
    if status is None:
        return JSONResponse({"error": f"Integration '{name}' not found"}, status_code=404)
    return status.to_dict()


@router.post("/integrations/{name}/test")
async def test_integration(name: str):
    """Test a specific integration connection."""
    registry = init_integration_registry()
    status = registry.check(name)
    if status is None:
        return JSONResponse({"error": f"Integration '{name}' not found"}, status_code=404)
    return {
        "name": status.name,
        "status": status.status,
        "error": status.error,
        "checked_at": status.checked_at,
    }


# ── Decision Journal endpoints ──────────────────────


@router.get("/decisions")
async def list_decisions(
    app_id: str | None = None,
    agent_id: str | None = None,
    outcome: str | None = None,
    limit: int = 100,
):
    """Query the decision journal with optional filters."""
    return {"decisions": dj_get(app_id=app_id, agent_id=agent_id, outcome=outcome, limit=limit)}


@router.get("/decisions/{decision_id}")
async def get_decision(decision_id: str):
    """Get a single decision by ID."""
    decisions = dj_get(limit=1000)
    for d in decisions:
        if d["decision_id"] == decision_id:
            return d
    return JSONResponse({"error": f"Decision '{decision_id}' not found"}, status_code=404)


class OutcomeRequest(BaseModel):
    outcome: str
    reward: float = 0.0
    notes: str = ""


@router.post("/decisions/{decision_id}/outcome")
async def record_decision_outcome(decision_id: str, body: OutcomeRequest):
    """Record the outcome of a previous decision."""
    ok = dj_outcome(decision_id, outcome=body.outcome, reward=body.reward, notes=body.notes)
    if not ok:
        return JSONResponse({"error": f"Decision '{decision_id}' not found"}, status_code=404)
    return {"decision_id": decision_id, "outcome": body.outcome, "recorded": True}


# ── Learning / Feedback endpoints ────────────────────


@router.get("/learning/stats")
async def learning_stats():
    """FeedbackLearner stats — weights, events, tuning history."""
    try:
        from cores.validation.feedback_tuner import FeedbackTuner

        tuner = FeedbackTuner()
        status = tuner.status()
        status["confidence_history"] = tuner._tuning_history[-5:] if tuner._tuning_history else []

        # Per-vuln-type accuracy from Decision Journal
        from core.decision_journal import get_decisions

        decisions = get_decisions(app_id="cateye", outcome="success", limit=200)
        success_count = len(decisions)
        decisions_fail = get_decisions(app_id="cateye", outcome="failure", limit=200)
        fail_count = len(decisions_fail)
        total_decisions = success_count + fail_count

        from cores.validation.confidence import get_confidence_scorer

        scorer = get_confidence_scorer()

        return {
            "weights": status["current_weights"],
            "llm_bias": scorer.get_bias(),
            "total_feedback_events": status["total_feedback_events"],
            "total_tunings": status["total_tunings"],
            "ready_for_analysis": status["ready_for_analysis"],
            "last_tuning": status["last_tuning"],
            "recent_tunings": status["confidence_history"],
            "validation_accuracy": {
                "success": success_count,
                "failure": fail_count,
                "total": total_decisions,
                "rate": round(success_count / total_decisions, 4) if total_decisions > 0 else 0,
            },
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/learning/trigger")
async def trigger_learning():
    """Manually trigger FeedbackLearner analysis and weight tuning."""
    try:
        from cores.validation.feedback_tuner import FeedbackTuner

        tuner = FeedbackTuner()
        result = tuner.tune_if_ready()
        return result
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.get("/learning/weights")
async def learning_weights():
    """Current ConfidenceScorer weights."""
    try:
        from cores.validation.confidence import get_confidence_scorer

        scorer = get_confidence_scorer()
        return {"weights": scorer.get_weights()}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.post("/learning/weights")
async def update_learning_weights(body: dict):
    """Manually adjust ConfidenceScorer weights (for testing/fine-tuning)."""
    try:
        from cores.validation.confidence import get_confidence_scorer

        scorer = get_confidence_scorer()
        old = scorer.get_weights()
        adjustments = {k: v for k, v in body.items() if k in old}
        scorer.adjust_weights(adjustments)
        return {"old": old, "new": scorer.get_weights(), "adjustments": adjustments}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


# ── Backup endpoints ─────────────────────────────────


@router.post("/backup/create")
async def backup_create():
    """Create a full ORION system backup."""
    from core.backup import create_backup as do_backup

    return do_backup()


@router.get("/backup/list")
async def backup_list():
    """List all available ORION backups."""
    from core.backup import list_backups

    return {"backups": list_backups()}


@router.get("/backup/status")
async def backup_st():
    """Backup system status."""
    from core.backup import backup_status

    return backup_status()


@router.post("/backup/verify")
async def backup_verify(path: str):
    """Verify integrity of a backup archive."""
    from core.backup import verify_backup

    return verify_backup(path)


@router.post("/backup/prune")
async def backup_prune(keep: int = 10):
    """Remove old backups, keeping only the N most recent."""
    from core.backup import prune_backups

    return prune_backups(keep=keep)


@router.post("/backup/restore")
async def backup_restore(path: str, target: str | None = None):
    """Restore ORION from a backup archive."""
    from core.backup import restore_backup

    return restore_backup(path, target_dir=target)


# ── Maintenance endpoints ──────────────────────────────


def _maint_to_dict(r):
    return {
        "operation": r.operation,
        "db_name": r.db_name,
        "status": r.status,
        "message": r.message,
        "duration_ms": r.duration_ms,
    }


@router.post("/maintenance/vacuum")
async def maintenance_vacuum():
    """Run VACUUM on all known databases."""
    from core.maintenance.engine import MaintenanceEngine

    return {"results": [_maint_to_dict(r) for r in MaintenanceEngine().vacuum()]}


@router.post("/maintenance/analyze")
async def maintenance_analyze():
    """Run ANALYZE on all known databases."""
    from core.maintenance.engine import MaintenanceEngine

    return {"results": [_maint_to_dict(r) for r in MaintenanceEngine().analyze()]}


@router.post("/maintenance/integrity")
async def maintenance_integrity():
    """Run integrity_check on all known databases."""
    from core.maintenance.engine import MaintenanceEngine

    return {"results": [_maint_to_dict(r) for r in MaintenanceEngine().integrity_check()]}


@router.post("/maintenance/reindex")
async def maintenance_reindex():
    """Rebuild all indexes on all known databases."""
    from core.maintenance.engine import MaintenanceEngine

    return {"results": [_maint_to_dict(r) for r in MaintenanceEngine().reindex()]}


@router.post("/maintenance/wal")
async def maintenace_wal():
    """WAL checkpoint (TRUNCATE) on all known databases."""
    from core.maintenance.engine import MaintenanceEngine

    return {"results": [_maint_to_dict(r) for r in MaintenanceEngine().wal_checkpoint()]}


@router.post("/maintenance/full")
async def maintenance_full():
    """Run all maintenance operations on all databases."""
    from core.maintenance.engine import run_maintenance

    return run_maintenance()


@router.get("/maintenance/summary")
async def maintenance_summary():
    """DB file sizes and status summary."""
    from core.maintenance.engine import MaintenanceEngine

    return MaintenanceEngine().summary()


# ── Update endpoints ──────────────────────────────────


@router.get("/update/status")
async def update_status():
    """Current version and update availability."""
    from core.update.engine import UpdateManager

    return UpdateManager().status()


@router.post("/update/check")
async def update_check():
    """Check remote for updates."""
    from core.update.engine import UpdateManager

    return UpdateManager().check_remote()


@router.post("/update/prepare")
async def update_prepare():
    """Prepare for update: backup + download."""
    from core.update.engine import UpdateManager

    return UpdateManager().prepare_update()


@router.post("/update/rollback")
async def update_rollback(backup_path: str | None = None):
    """Rollback to the last backup."""
    from core.update.engine import UpdateManager

    return UpdateManager().rollback(backup_path)


@router.get("/update/history")
async def update_history(limit: int = 10):
    """Update history log."""
    from core.update.engine import UpdateManager

    return {"history": UpdateManager().get_history(limit=limit)}


# ── Version info ──────────────────────────────────────


@router.get("/version")
async def version_info():
    """ORION Platform version and API contract versions."""
    from core.version import DECISION_JOURNAL, EVENT_SCHEMA, MEMORY_SCHEMA, NORMALIZER_API, ORION_VERSION, PLUGIN_API

    return {
        "orion_version": ORION_VERSION,
        "plugin_api": PLUGIN_API,
        "event_schema": EVENT_SCHEMA,
        "memory_schema": MEMORY_SCHEMA,
        "decision_journal": DECISION_JOURNAL,
        "normalizer_api": NORMALIZER_API,
    }
