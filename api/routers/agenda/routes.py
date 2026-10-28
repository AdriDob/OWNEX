"""Unified Agenda API Router.

Endpoints:
- GET /api/agenda/           — Agenda unificada (formato frontend AgendaView.vue)
- GET /api/agenda/items      — Lista de items con filtros
- GET /api/agenda/week       — Vista semanal (7 días)
- GET /api/agenda/month      — Vista mensual
- GET /api/agenda/day        — Vista día específico
- GET /api/agenda/timeline   — Proyecciones futuro (timeline)
- GET /api/agenda/deadlines  — Próximos deadlines
- POST /api/agenda/items     — Crear item manual
- PUT /api/agenda/items/{id} — Actualizar item
- POST /api/agenda/refresh   — Refrescar desde todas las fuentes
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from cores.agenda.engine import get_agenda_engine
from cores.agenda.models import (
    AgendaHorizon,
    AgendaItem,
    AgendaItemType,
    AgendaSource,
    calculate_horizon,
)

# Sub-router: sin prefix. El router padre (api/routers/agenda/__init__.py)
# aporta el prefix "/api/agenda" y hace include_router de este módulo.
#
# Por qué existe el sub-módulo: hasta 2026-10-22 este archivo era
# `api/routers/agenda.py` (módulo) y existía además `api/routers/agenda/`
# (paquete). En Python el PAQUETE sombrea al MÓDULO, así que main.py montaba
# el paquete (4 rutas) y estas 11 quedaban sin montar — código muerto.
router = APIRouter(tags=["agenda"])


# ──────────────────────────────────────────────────────────────────
# Request/Response Models
# ──────────────────────────────────────────────────────────────────


class AgendaItemCreate(BaseModel):
    title: str
    description: str = ""
    date: str  # YYYY-MM-DD
    horizon: str | None = None
    time_estimate_minutes: int | None = None
    source: str = "manual"
    source_id: str | None = None
    item_type: str = "task"
    category: str | None = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    reminder_enabled: bool = True
    reminder_days_before: list[int] = [1, 3, 7]


class AgendaItemUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    date: str | None = None
    horizon: str | None = None
    time_estimate_minutes: int | None = None
    progress_pct: float | None = None
    completed: bool | None = None
    category: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    reminder_enabled: bool | None = None
    reminder_days_before: list[int] | None = None


class AgendaItemResponse(BaseModel):
    success: bool
    item: dict[str, Any] | None = None
    items: list[dict[str, Any]] | None = None
    total: int | None = None
    message: str | None = None


class AgendaViewResponse(BaseModel):
    success: bool
    views: list[dict[str, Any]]
    total_items: int


class TimelineResponse(BaseModel):
    success: bool
    projections: list[dict[str, Any]]
    summary: dict[str, Any]


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────


def _validate_date(date_str: str) -> str:
    """Validate and normalize date string."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Use YYYY-MM-DD") from None


def _validate_horizon(horizon: str | None) -> AgendaHorizon | None:
    if horizon is None:
        return None
    try:
        return AgendaHorizon(horizon)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid horizon: {horizon}") from None


def _validate_source(source: str | None) -> AgendaSource | None:
    if source is None:
        return None
    try:
        return AgendaSource(source)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid source: {source}") from None


def _validate_item_type(item_type: str | None) -> AgendaItemType | None:
    if item_type is None:
        return None
    try:
        return AgendaItemType(item_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid item_type: {item_type}") from None


# ──────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────


@router.get("/")
async def get_unified_agenda() -> dict[str, Any]:
    """Get unified agenda in frontend-compatible format (AgendaView.vue).

    Returns:
        UnifiedAgendaState format:
        {
            generated_at, total_items,
            today: AgendaItem[],
            short_term: AgendaItem[],
            medium_term: AgendaItem[],
            long_term: AgendaItem[],
            counts: Record<string, number>,
            best_action: AgendaItem | null
        }
    """
    engine = get_agenda_engine()
    items = engine.get_items(include_completed=True)

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    today_items = [i for i in items if i.date == today]

    # Categorize by horizon
    short_term = [i for i in items if i.horizon == AgendaHorizon.SHORT and i.date != today]
    medium_term = [i for i in items if i.horizon == AgendaHorizon.MEDIUM]
    long_term = [i for i in items if i.horizon in (AgendaHorizon.LONG, AgendaHorizon.VISION)]

    # Convert to frontend format
    def to_frontend(item: AgendaItem) -> dict[str, Any]:
        return {
            "date": item.date,
            "horizon": item.horizon.value,
            "source": item.source.value,
            "title": item.title,
            "progress_pct": item.progress_pct,
            "reward": next((v for k, v in item.metadata.items() if k in ("expected_ev", "threshold_amount")), None),
            "url": item.metadata.get("url"),
            "action": item.metadata.get("action") or item.metadata.get("next_action"),
        }

    # Best action: highest EV item from today or short term
    all_actionable = today_items + short_term
    best_action = None
    if all_actionable:
        best = max(all_actionable, key=lambda i: i.metadata.get("expected_ev", 0) or 0)
        best_action = to_frontend(best)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "total_items": len(items),
        "today": [to_frontend(i) for i in today_items],
        "short_term": [to_frontend(i) for i in short_term],
        "medium_term": [to_frontend(i) for i in medium_term],
        "long_term": [to_frontend(i) for i in long_term],
        "counts": {
            "today": len(today_items),
            "short_term": len(short_term),
            "medium_term": len(medium_term),
            "long_term": len(long_term),
        },
        "best_action": best_action,
    }


@router.post("/refresh")
async def refresh_agenda() -> AgendaItemResponse:
    """Refresh agenda items from all connected sources."""
    engine = get_agenda_engine()
    items = engine.refresh_all()
    return AgendaItemResponse(
        success=True,
        items=[i.to_dict() for i in items],
        total=len(items),
        message=f"Refreshed {len(items)} items from all sources",
    )


@router.get("/items")
async def get_agenda_items(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    horizon: str | None = Query(None, description="Filter by horizon: short|medium|long|vision"),
    source: str | None = Query(None, description="Filter by source"),
    item_type: str | None = Query(None, description="Filter by item type"),
    include_completed: bool = Query(False, description="Include completed items"),
) -> AgendaItemResponse:
    """Get filtered agenda items."""
    engine = get_agenda_engine()

    if start_date:
        start_date = _validate_date(start_date)
    if end_date:
        end_date = _validate_date(end_date)
    horizon_enum = _validate_horizon(horizon)
    source_enum = _validate_source(source)
    item_type_enum = _validate_item_type(item_type)

    items = engine.get_items(
        start_date=start_date,
        end_date=end_date,
        horizon=horizon_enum,
        source=source_enum,
        item_type=item_type_enum,
        include_completed=include_completed,
    )

    return AgendaItemResponse(
        success=True,
        items=[i.to_dict() for i in items],
        total=len(items),
    )


@router.get("/day")
async def get_day_view(date: str = Query(..., description="Date (YYYY-MM-DD)")) -> AgendaItemResponse:
    """Get agenda view for a specific day."""
    engine = get_agenda_engine()
    date = _validate_date(date)
    view = engine.get_view_for_date(date)
    return AgendaItemResponse(
        success=True,
        items=[i.to_dict() for i in view.items],
        total=view.total_items,
    )


@router.get("/week")
async def get_week_view(
    start_date: str = Query(..., description="Start date of week (YYYY-MM-DD)"),
) -> AgendaViewResponse:
    """Get agenda views for a week (7 days)."""
    engine = get_agenda_engine()
    start_date = _validate_date(start_date)
    views = engine.get_week_view(start_date)

    views_data = []
    total = 0
    for view in views:
        views_data.append(
            {
                "date": view.date,
                "total_items": view.total_items,
                "completed_items": view.completed_items,
                "pending_items": view.pending_items,
                "items": [i.to_dict() for i in view.items],
                "by_horizon": {h.value: [i.to_dict() for i in items] for h, items in view.by_horizon.items()},
                "by_source": {s.value: [i.to_dict() for i in items] for s, items in view.by_source.items()},
                "by_type": {t.value: [i.to_dict() for i in items] for t, items in view.by_type.items()},
            }
        )
        total += view.total_items

    return AgendaViewResponse(success=True, views=views_data, total_items=total)


@router.get("/month")
async def get_month_view(
    year: int = Query(..., ge=2020, le=2030),
    month: int = Query(..., ge=1, le=12),
) -> AgendaViewResponse:
    """Get agenda views for a month."""
    engine = get_agenda_engine()
    views = engine.get_month_view(year, month)

    views_data = []
    total = 0
    for view in views:
        views_data.append(
            {
                "date": view.date,
                "total_items": view.total_items,
                "completed_items": view.completed_items,
                "pending_items": view.pending_items,
                "items": [i.to_dict() for i in view.items],
            }
        )
        total += view.total_items

    return AgendaViewResponse(success=True, views=views_data, total_items=total)


@router.get("/timeline")
async def get_timeline(
    months: int = Query(24, ge=1, le=36, description="Number of months to project"),
) -> TimelineResponse:
    """Get future timeline projections."""
    engine = get_agenda_engine()
    projections = engine.get_timeline_projections(months)

    # Summary
    total_income = sum(p.projected_income_usd for p in projections)
    avg_income = total_income / len(projections) if projections else 0
    max_income = max((p.projected_income_usd for p in projections), default=0)

    milestones_all = []
    for p in projections:
        milestones_all.extend(p.key_milestones)

    summary = {
        "months_projected": len(projections),
        "total_projected_income": round(total_income, 2),
        "average_monthly_income": round(avg_income, 2),
        "peak_monthly_income": round(max_income, 2),
        "key_milestones": list(dict.fromkeys(milestones_all)),  # Deduplicate
    }

    return TimelineResponse(
        success=True,
        projections=[
            {
                "month": p.month,
                "label": p.label,
                "projected_income_usd": p.projected_income_usd,
                "projected_capital_usd": p.projected_capital_usd,
                "key_milestones": p.key_milestones,
                "confidence": p.confidence,
            }
            for p in projections
        ],
        summary=summary,
    )


@router.get("/deadlines")
async def get_upcoming_deadlines(
    days: int = Query(30, ge=1, le=90, description="Days ahead to check"),
) -> AgendaItemResponse:
    """Get items with approaching deadlines."""
    engine = get_agenda_engine()
    items = engine.get_upcoming_deadlines(days)
    return AgendaItemResponse(
        success=True,
        items=[i.to_dict() for i in items],
        total=len(items),
    )


@router.post("/items")
async def create_agenda_item(payload: AgendaItemCreate) -> AgendaItemResponse:
    """Create a manual agenda item."""
    engine = get_agenda_engine()

    date = _validate_date(payload.date)
    horizon = _validate_horizon(payload.horizon) or calculate_horizon(date)
    source_enum = _validate_source(payload.source) or AgendaSource.MANUAL
    item_type_enum = _validate_item_type(payload.item_type)

    item_id = f"manual_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    item = AgendaItem(
        id=item_id,
        title=payload.title,
        description=payload.description,
        date=date,
        horizon=horizon,
        time_estimate_minutes=payload.time_estimate_minutes,
        source=source_enum,
        source_id=payload.source_id,
        item_type=item_type_enum or AgendaItemType.TASK,
        category=payload.category,
        tags=payload.tags,
        metadata=payload.metadata,
        reminder_enabled=payload.reminder_enabled,
        reminder_days_before=payload.reminder_days_before,
    )

    # Add to engine cache
    engine._items_cache.append(item)

    return AgendaItemResponse(success=True, item=item.to_dict(), message="Agenda item created")


@router.put("/items/{item_id}")
async def update_agenda_item(item_id: str, payload: AgendaItemUpdate) -> AgendaItemResponse:
    """Update an agenda item."""
    engine = get_agenda_engine()

    # Find item in cache
    item = next((i for i in engine._items_cache if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Agenda item not found")

    # Update fields
    if payload.title is not None:
        item.title = payload.title
    if payload.description is not None:
        item.description = payload.description
    if payload.date is not None:
        item.date = _validate_date(payload.date)
    if payload.horizon is not None:
        validated_horizon = _validate_horizon(payload.horizon)
        if validated_horizon is not None:
            item.horizon = validated_horizon
    if payload.time_estimate_minutes is not None:
        item.time_estimate_minutes = payload.time_estimate_minutes
    if payload.progress_pct is not None:
        item.progress_pct = max(0.0, min(100.0, payload.progress_pct))
    if payload.completed is not None:
        item.completed = payload.completed
        if payload.completed and not item.completed_at:
            item.completed_at = datetime.now(UTC).isoformat()
        elif not payload.completed:
            item.completed_at = None
    if payload.category is not None:
        item.category = payload.category
    if payload.tags is not None:
        item.tags = payload.tags
    if payload.metadata is not None:
        item.metadata = payload.metadata
    if payload.reminder_enabled is not None:
        item.reminder_enabled = payload.reminder_enabled
    if payload.reminder_days_before is not None:
        item.reminder_days_before = payload.reminder_days_before

    item.updated_at = datetime.now(UTC).isoformat()

    return AgendaItemResponse(success=True, item=item.to_dict(), message="Agenda item updated")


@router.post("/items/{item_id}/complete")
async def complete_agenda_item(item_id: str) -> AgendaItemResponse:
    """Mark agenda item as completed."""
    engine = get_agenda_engine()

    item = next((i for i in engine._items_cache if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Agenda item not found")

    item.completed = True
    item.completed_at = datetime.now(UTC).isoformat()
    item.progress_pct = 100.0
    item.updated_at = datetime.now(UTC).isoformat()

    return AgendaItemResponse(success=True, item=item.to_dict(), message="Agenda item completed")
