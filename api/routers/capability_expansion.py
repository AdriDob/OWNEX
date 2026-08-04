"""Capability Expansion API — OWNEX self-improvement surface.

- GET  /api/capability-expansion/report        — what OWNEX can do / is missing / should improve
- GET  /api/capability-expansion/gaps          — missing capabilities per layer
- GET  /api/capability-expansion/suggestions   — self-improvement suggestions
- POST /api/capability-expansion/evaluate      — score a candidate (Smart Installation Rules)
- POST /api/capability-expansion/install       — integrate + register (dry_run default; critical → approval)
- GET  /api/capability-expansion/approvals     — pending approvals
- POST /api/capability-expansion/approvals/{approval_id}/decide — approve/deny a queued change
- POST /api/capabilities/{capability}/usage    — record a usage event (metrics)
- GET  /api/capabilities/stats                 — registry aggregate stats
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from core.capabilities.expansion import (
    CapabilityCandidate,
    CapabilityExpansionEngine,
    get_expansion_engine,
)
from core.capabilities.registry import get_capability_registry

logger = logging.getLogger("ownex.api.capability_expansion")

router = APIRouter(prefix="/api/capability-expansion", tags=["capability-expansion"])

capabilities_router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


def _engine() -> CapabilityExpansionEngine:
    return get_expansion_engine()


@router.get("/report")
def get_report() -> dict[str, Any]:
    """Full capability report: what OWNEX can do, what's missing, what to improve."""
    try:
        return _engine().registry_report()
    except Exception as exc:  # noqa: BLE001
        logger.error("Capability report failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Capability report failed: {exc}") from exc


@router.get("/marketplace")
def get_marketplace() -> dict[str, Any]:
    """Internal capability marketplace: category coverage bars."""
    try:
        return {"categories": _engine().marketplace_coverage()}
    except Exception as exc:  # noqa: BLE001
        logger.error("Marketplace report failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Marketplace report failed: {exc}") from exc


@router.get("/daily-report")
def get_daily_report() -> dict[str, Any]:
    """Daily Evolution Mode: discoveries, integrations, performance and upgrades."""
    try:
        return _engine().daily_evolution_report()
    except Exception as exc:  # noqa: BLE001
        logger.error("Daily evolution report failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Daily evolution report failed: {exc}") from exc


@router.get("/gaps")
def get_gaps() -> dict[str, Any]:
    """Missing capabilities per layer."""
    try:
        gaps = _engine().detect_gaps()
        return {"count": sum(g["count"] for g in gaps), "layers": gaps}
    except Exception as exc:  # noqa: BLE001
        logger.error("Gap detection failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {exc}") from exc


@router.get("/suggestions")
def get_suggestions() -> dict[str, Any]:
    """Self-improvement suggestions with recommended actions."""
    try:
        suggestions = _engine().suggest_improvements()
        return {"count": len(suggestions), "suggestions": suggestions}
    except Exception as exc:  # noqa: BLE001
        logger.error("Suggestions failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Suggestions failed: {exc}") from exc


@router.post("/evaluate")
def evaluate(body: dict[str, Any]) -> dict[str, Any]:
    """Score a candidate capability using the Smart Installation Rules."""
    try:
        candidate = CapabilityCandidate(
            capability=str(body.get("capability", "")),
            category=str(body.get("category", "ai")),
            name=str(body.get("name", body.get("capability", ""))),
            description=str(body.get("description", "")),
            providers=[str(p) for p in body.get("providers", [])],
            install_hint=str(body.get("install_hint", "")),
            benefits=[str(b) for b in body.get("benefits", [])],
            requires_approval=bool(body.get("requires_approval", False)),
        )
        return _engine().evaluate_candidate(candidate)
    except Exception as exc:  # noqa: BLE001
        logger.error("Evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc


@router.post("/install")
def install(body: dict[str, Any]) -> dict[str, Any]:
    """Integrate + register a capability.

    dry_run defaults to True (safe). Critical changes (permissions,
    accounts, financial, security) are queued for approval regardless.
    """
    try:
        capability = str(body.get("capability", ""))
        if not capability:
            raise HTTPException(status_code=422, detail="capability is required")
        return _engine().install_candidate(
            capability=capability,
            module=str(body.get("module", "expansion_engine")),
            metadata=body.get("metadata") or {},
            description=str(body.get("description", "")),
            dry_run=bool(body.get("dry_run", True)),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error("Install failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Install failed: {exc}") from exc


@router.get("/approvals")
def list_approvals() -> dict[str, Any]:
    """List pending critical-change approvals."""
    try:
        pending = _engine().pending_approvals()
        return {"count": len(pending), "pending": pending}
    except Exception as exc:  # noqa: BLE001
        logger.error("Approvals list failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Approvals failed: {exc}") from exc


@router.post("/approvals/{approval_id}/decide")
def decide_approval(approval_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Approve or deny a queued critical change."""
    try:
        granted = bool(body.get("granted", True))
        return _engine().approve(approval_id, granted=granted)
    except Exception as exc:  # noqa: BLE001
        logger.error("Approval decision failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Approval decision failed: {exc}") from exc


# ── Registry metrics surface ────────────────────────────────────────


@capabilities_router.get("/stats")
def get_capabilities_stats() -> dict[str, Any]:
    """Aggregate registry statistics."""
    try:
        return get_capability_registry().stats()
    except Exception as exc:  # noqa: BLE001
        logger.error("Capability stats failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Capability stats failed: {exc}") from exc


@capabilities_router.get("")
def list_capabilities() -> dict[str, Any]:
    """List all registered capabilities with operational metrics."""
    try:
        reg = get_capability_registry()
        entries = []
        for e in reg._entries:  # noqa: SLF001 — registry report surface
            entries.append(
                {
                    "capability": e.capability,
                    "module": e.module,
                    "category": e.category,
                    "version": e.version,
                    "dependencies": e.dependencies,
                    "status": e.status,
                    "health": e.health,
                    "avg_performance_ms": e.avg_performance_ms,
                    "usage_count": e.usage_count,
                    "last_used_at": e.last_used_at,
                    "improvement_potential": e.improvement_potential,
                    "description": e.description,
                }
            )
        return {"stats": reg.stats(), "entries": entries}
    except Exception as exc:  # noqa: BLE001
        logger.error("Capability list failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Capability list failed: {exc}") from exc


@capabilities_router.post("/{capability}/usage")
def record_usage(capability: str, body: dict[str, Any]) -> dict[str, Any]:
    """Record a usage event for a capability (metrics for improvement potential)."""
    try:
        reg = get_capability_registry()
        reg.record_usage(
            capability=capability,
            module=body.get("module"),
            duration_ms=body.get("duration_ms"),
        )
        return {"ok": True, "capability": capability, "recorded_at": time.time()}
    except Exception as exc:  # noqa: BLE001
        logger.error("Usage recording failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Usage recording failed: {exc}") from exc
