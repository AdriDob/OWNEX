"""Financial Sync Router — manual trigger and status for the auto-sync scheduler."""

from __future__ import annotations

from fastapi import APIRouter

from cores.financial.scheduler import get_financial_sync_scheduler

router = APIRouter(prefix="/api/financial/sync", tags=["financial-sync"])


@router.post("/platforms")
def sync_platforms_now():
    scheduler = get_financial_sync_scheduler()
    results = scheduler.sync_platforms()
    return {
        "status": "ok",
        "platforms": results,
        "total": len(results),
        "successful": sum(1 for r in results.values() if r.get("success")),
    }


@router.post("/crypto")
def sync_crypto_now():
    scheduler = get_financial_sync_scheduler()
    results = scheduler.sync_crypto()
    return {
        "status": "ok",
        "wallets": results,
        "total": len(results),
        "successful": sum(1 for r in results.values() if r.get("success")),
    }


@router.post("/all")
def sync_all_now():
    scheduler = get_financial_sync_scheduler()
    report = scheduler.sync_all()
    return {
        "status": "ok",
        "start_time": report.start_time,
        "end_time": report.end_time,
        "platforms": report.platforms,
        "crypto": report.crypto,
        "total_platforms": report.total_platforms,
        "successful_platforms": report.successful_platforms,
        "total_crypto": report.total_crypto,
        "successful_crypto": report.successful_crypto,
    }


@router.get("/status")
def sync_status():
    scheduler = get_financial_sync_scheduler()
    last = scheduler.get_last_sync()
    return {
        "is_running": scheduler.is_running,
        "interval_minutes": scheduler.interval_minutes,
        "last_sync": {
            "start_time": last.start_time,
            "end_time": last.end_time,
            "total_platforms": last.total_platforms,
            "successful_platforms": last.successful_platforms,
            "total_crypto": last.total_crypto,
            "successful_crypto": last.successful_crypto,
        }
        if last
        else None,
    }


@router.get("/history")
def sync_history(limit: int = 10):
    scheduler = get_financial_sync_scheduler()
    history = scheduler.get_sync_history(limit=limit)
    return {
        "history": [
            {
                "start_time": r.start_time,
                "end_time": r.end_time,
                "total_platforms": r.total_platforms,
                "successful_platforms": r.successful_platforms,
                "total_crypto": r.total_crypto,
                "successful_crypto": r.successful_crypto,
            }
            for r in history
        ],
        "total": len(history),
    }
