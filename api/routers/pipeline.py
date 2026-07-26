from fastapi import APIRouter

from api.scheduler import get_scheduler_stats
from api.services.data_service import get_pipeline_stages

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.get("")
def get_pipeline():
    return get_pipeline_stages()


@router.get("/stages")
def get_stages():
    """Return current pipeline stage + scheduler stats for frontend progress display."""
    stats = get_scheduler_stats()
    return {
        "current_stage": stats.get("current_stage", "idle"),
        "stage_started_at": stats.get("stage_started_at", 0),
        "scheduler_running": stats.get("running", False),
        "targets_in_cooldown": stats.get("targets_in_cooldown", 0),
        "last_run": stats.get("last_run"),
    }
