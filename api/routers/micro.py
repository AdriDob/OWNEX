"""CATEYE Micro‑Functions Router — compact dashboard endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from cores.financial.micro import (
    _batch_operation,
    _get_entity_by_type,
    compute_real_exposure,
    detect_sync_anomalies,
    export_account_snapshot,
    get_minimal_dashboard_state,
    get_pending_actions,
    get_sync_health,
    quick_sync_all,
    retry_failed_syncs,
    sync_source_now,
    trace_balance_origin,
)

router = APIRouter(prefix="/api/micro", tags=["micro"])


@router.post("/quick-sync-all")
def post_quick_sync_all():
    return quick_sync_all()


@router.post("/sync-source/{source_id}")
def post_sync_source(source_id: str):
    return sync_source_now(source_id)


@router.get("/sync-health")
def get_sync_health_endpoint():
    return get_sync_health()


@router.get("/trace-balance/{account_id}")
def get_trace_balance(account_id: str):
    return trace_balance_origin(account_id)


@router.get("/anomalies")
def get_anomalies():
    return detect_sync_anomalies()


@router.get("/pending-actions")
def get_pending_actions_endpoint():
    return get_pending_actions()


@router.get("/real-exposure")
def get_real_exposure():
    return compute_real_exposure()


@router.get("/snapshot/{account_id}")
def get_snapshot(account_id: str):
    return export_account_snapshot(account_id)


@router.post("/retry-failed")
def post_retry_failed():
    return retry_failed_syncs()


@router.get("/dashboard-state")
def get_dashboard_state():
    return get_minimal_dashboard_state()


# ── Batch operations ──────────────────────────────────────────────


@router.post("/batch/export")
def post_batch_export(body: dict):
    return _batch_operation(
        ids=body["ids"],
        type_=body["type"],
        operation="export",
        format=body.get("format", "json"),
    )


@router.post("/batch/sync")
def post_batch_sync(body: dict):
    return _batch_operation(
        ids=body["ids"],
        type_=body["type"],
        operation="sync",
    )


@router.post("/batch/delete")
def post_batch_delete(body: dict):
    return _batch_operation(
        ids=body["ids"],
        type_=body["type"],
        operation="delete",
    )


@router.post("/batch/tag")
def post_batch_tag(body: dict):
    return _batch_operation(
        ids=body["ids"],
        type_=body["type"],
        operation="tag",
        tag=body.get("tag", ""),
    )


# ── Entity fetch ──────────────────────────────────────────────────


@router.get("/entity/{type_}/{id_}")
def get_entity(type_: str, id_: str):
    return _get_entity_by_type(type_, id_)
