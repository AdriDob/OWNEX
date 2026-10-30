"""5-Pillar API — Dashboard, startup plan, pillar details, performance tracking, high-value programs, and earnings optimizer."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/pillars", tags=["5-Pillar Income"])


@router.get("/dashboard")
async def pillars_dashboard():
    """Complete 5-pillar dashboard with totals and recommendations."""
    from cores.pillars.orchestrator import get_five_pillar_orchestrator

    orch = get_five_pillar_orchestrator()
    return orch.get_dashboard().to_dict()


@router.get("/startup-plan")
async def startup_plan():
    """Day-by-day plan for the first week."""
    from cores.pillars.orchestrator import get_five_pillar_orchestrator

    orch = get_five_pillar_orchestrator()
    return orch.get_startup_plan()


@router.get("/{pillar_id}")
async def pillar_detail(pillar_id: int):
    """Get details for a specific pillar."""
    from cores.pillars.orchestrator import get_five_pillar_orchestrator

    orch = get_five_pillar_orchestrator()
    pillar = orch.get_pillar(pillar_id)
    if not pillar:
        return {"error": f"Pillar {pillar_id} not found"}
    return pillar.to_dict()


@router.get("/ai-tasks/summary")
async def ai_tasks_summary():
    """AI Tasks orchestrator summary."""
    from cores.opportunity.adapters.ai_tasks import get_ai_tasks_orchestrator

    orch = get_ai_tasks_orchestrator()
    return orch.get_summary()


@router.get("/qa/summary")
async def qa_summary():
    """QA/Crowdtesting orchestrator summary."""
    from cores.opportunity.adapters.qa_crowdtest import get_qa_orchestrator

    orch = get_qa_orchestrator()
    return orch.get_summary()


@router.get("/data-annotation/summary")
async def data_annotation_summary():
    """Data Annotation orchestrator summary."""
    from cores.opportunity.adapters.data_annotation import get_data_annotation_orchestrator

    orch = get_data_annotation_orchestrator()
    return orch.get_summary()


@router.get("/performance")
async def performance_dashboard():
    """REAL performance dashboard — actual $/hour, not estimates."""
    from cores.pillars.performance import get_performance_tracker

    tracker = get_performance_tracker()
    return tracker.get_dashboard()


@router.post("/performance/action")
async def record_action(body: dict):
    """Record a new action for tracking."""
    from cores.pillars.performance import get_performance_tracker

    tracker = get_performance_tracker()
    action = tracker.record_action(
        pillar=body.get("pillar", "unknown"),
        platform=body.get("platform", "unknown"),
        title=body.get("title", "Untitled"),
        status=body.get("status", "discovered"),
        human_minutes=body.get("human_minutes", 0),
        expected_value=body.get("expected_value", 0),
        actual_revenue=body.get("actual_revenue", 0),
        notes=body.get("notes", ""),
    )
    return action.to_dict()


@router.post("/performance/{action_id}/status")
async def update_action_status(action_id: str, body: dict):
    """Update an action's status (applied → accepted → paid)."""
    from cores.pillars.performance import get_performance_tracker

    tracker = get_performance_tracker()
    success = tracker.update_status(
        action_id=action_id,
        status=body.get("status", "pending"),
        revenue=body.get("revenue", 0),
    )
    if not success:
        return {"error": f"Action {action_id} not found"}
    return {"ok": True, "action_id": action_id}


@router.get("/performance/forecast")
async def personal_forecast():
    """Personal forecast based on YOUR real data."""
    from cores.pillars.performance import get_performance_tracker

    tracker = get_performance_tracker()
    return tracker.generate_forecast().to_dict()


@router.get("/high-value")
async def high_value_programs():
    """Top 50 highest-paying public programs."""
    from cores.pillars.high_value_programs import get_summary

    return get_summary()


@router.get("/high-value/top")
async def top_programs(limit: int = 10):
    """Top N programs by max bounty."""
    from cores.pillars.high_value_programs import get_top_programs

    return [p.to_dict() for p in get_top_programs(limit)]


@router.get("/high-value/web3")
async def web3_programs():
    """Web3/DeFi programs with highest payouts."""
    from cores.pillars.high_value_programs import get_programs_by_category

    return [p.to_dict() for p in get_programs_by_category("web3")]


@router.get("/optimizer")
async def earnings_optimizer():
    """Earnings optimization strategies and learning path."""
    from cores.pillars.earnings_optimizer import get_earnings_optimizer

    return get_earnings_optimizer().to_dict()
