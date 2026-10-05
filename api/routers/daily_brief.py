"""Daily Brief API — Answers the question: "What should I do now?"

Generates a ranked list of actions with:
- Expected value (USD)
- Time estimate
- Probability of success
- Next concrete action (button)

Plus a full-day plan (morning/afternoon/evening) and system warnings so the
user knows everything they need to do today, not just the next action.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger("ownex.api.daily_brief")

router = APIRouter(prefix="/api/daily-brief", tags=["daily-brief"])


def _get_recommender() -> Any:  # type: ignore[no-untyped-def]
    """Get the Direct Work Engine recommender."""
    try:
        from cores.direct_work_engine import get_direct_work_engine

        dwe = get_direct_work_engine()
        return dwe.recommender
    except Exception:
        return None


def _get_workbank() -> Any:  # type: ignore[no-untyped-def]
    """Get the WorkBank."""
    try:
        from cores.direct_work_engine.workbank import get_workbank

        return get_workbank()
    except Exception:
        return None


def _get_revenue_tracker() -> Any:  # type: ignore[no-untyped-def]
    """Get the RevenueTracker."""
    try:
        from cores.revenue_tracker.tracker import get_revenue_tracker

        return get_revenue_tracker()
    except Exception:
        return None


@router.get("")
async def daily_brief() -> dict[str, Any]:
    """Generate the Daily Brief — ranked actions for today.

    Returns:
    - actions: List of ranked actions with EV, time, probability, next step
    - summary: Quick stats (total EV, pending work, revenue today)
    - blocked: Items waiting for human approval
    - completed_today: Items completed today
    """
    actions: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    completed_today: list[dict[str, Any]] = []

    # 1. Get recommendations from Direct Work Engine
    ranked: list[Any] = []
    try:
        from cores.direct_work_engine.models import UserProfile

        recommender = _get_recommender()
        if recommender:
            profile = UserProfile(name="OWNEX User")
            # Get top opportunities ranked by EV
            engine = None
            try:
                from cores.direct_work_engine import get_direct_work_engine

                engine = get_direct_work_engine()
                opps = await engine.discovery.discover_all() if engine else []
            except Exception:
                opps = []

            if opps:
                ranked = recommender.recommend(opps, profile, limit=10) or []
                for r in ranked[:10]:
                    opp = r.opportunity if hasattr(r, "opportunity") else r
                    score = getattr(r, "final_score", getattr(r, "score", 0))
                    # SSOT: el recommender ya calcula htroi (compute_htroi). El
                    # campoopp.expected_value_usd_per_hour nunca existió y dejaba
                    # este bloque siempre en 0.0.
                    htroi = getattr(r, "htroi", None) or {}
                    ev_hr = htroi.get("usd_per_hour") if isinstance(htroi, dict) else None
                    prob = getattr(opp, "acceptance_probability", 0.5)
                    reward = getattr(opp, "payment", getattr(opp, "estimated_reward_usd", 0))
                    hours = getattr(opp, "estimated_time_hours", 2.0)

                    actions.append(
                        {
                            "id": getattr(opp, "id", "unknown"),
                            "title": getattr(opp, "title", "Untitled"),
                            "platform": getattr(opp, "platform", "unknown"),
                            "category": getattr(opp, "category", "unknown"),
                            "expected_value_usd": round(reward * prob, 2),
                            "expected_value_per_hour": round(ev_hr, 2) if isinstance(ev_hr, (int, float)) else None,
                            "probability": round(prob, 2),
                            "estimated_hours": round(hours, 1),
                            "reward_usd": round(reward, 2),
                            "score": round(score, 3),
                            "url": getattr(opp, "url", ""),
                            "next_action": _determine_next_action(opp),
                            "action_type": "opportunity",
                        }
                    )
    except Exception as exc:
        logger.debug("Daily brief opportunity scan failed: %s", exc)

    # 1b. Cross-category lens (additive, never alters `actions`): the same
    # opportunities re-ranked through registered funnels with honest
    # P_SUCCESS (product of funnel probabilities) + HIGH_CONFIDENCE_90 flags.
    ranked_cross_category: list[dict[str, Any]] = []
    try:
        from cores.direct_work_engine.universal_probability import get_universal_probability_engine

        ueng = get_universal_probability_engine()
        opps_only = [r.opportunity if hasattr(r, "opportunity") else r for r in ranked[:10]]
        for entry in ueng.rank_cross_category(opps_only, mode="BALANCED"):
            o = entry["opportunity"]
            ranked_cross_category.append(
                {
                    "id": getattr(o, "id", "unknown"),
                    "title": getattr(o, "title", "Untitled"),
                    "category": entry["category"],
                    "funnel": entry["funnel"],
                    "p_success": entry["p_success"],
                    "ev_per_hour": entry["ev_per_hour"],
                    "time_to_money_days": entry["time_to_money_days"],
                    "is_high_confidence_90": entry["is_high_confidence_90"],
                }
            )
    except Exception as exc:
        logger.debug("Daily brief cross-category lens failed: %s", exc)

    # 2. Get work bank items ready for delivery
    try:
        bank = _get_workbank()
        if bank:
            if hasattr(bank, "best_ready"):
                items = bank.best_ready(5)
            elif hasattr(bank, "get_items_by_status"):
                items = bank.get_items_by_status("ready_to_deliver")
            else:
                items = [
                    i
                    for i in getattr(bank, "_items", {}).values()
                    if getattr(i, "ready_to_deliver", False) or getattr(i, "status", "") == "ready_to_deliver"
                ][:5]
            for item in (items or [])[:5]:
                actions.append(
                    {
                        "id": getattr(item, "id", "unknown"),
                        "title": f"Deliver: {getattr(item, 'title', 'Untitled')}",
                        "platform": getattr(item, "platform", "unknown"),
                        "category": "delivery",
                        "expected_value_usd": getattr(item, "estimated_reward_usd", 0),
                        "probability": 0.9,
                        "next_action": "Submit delivery",
                        "action_type": "delivery",
                    }
                )
    except Exception as exc:
        logger.debug("Daily brief workbank scan failed: %s", exc)

    # 3. Get pending approvals (from WorkerCore)
    try:
        from cores.worker_core import get_worker_core

        worker = get_worker_core()
        for wid, witem in worker.work_items.items():
            if witem.human_action_required:
                blocked.append(
                    {
                        "id": wid,
                        "title": witem.title,
                        "phase": witem.phase.value,
                        "description": witem.human_action_description or "Approval needed",
                        "platform": witem.platform,
                    }
                )
            elif witem.state.value == "running":
                completed_today.append(
                    {
                        "id": wid,
                        "title": witem.title,
                        "phase": witem.phase.value,
                    }
                )
    except Exception:
        pass

    # 4. Sort actions by expected value
    actions.sort(key=lambda a: a.get("expected_value_usd", 0), reverse=True)

    # 4b. Full-day plan + warnings (daily guidance beyond the next action)
    bank = _get_workbank()
    plan = _build_plan(actions, bank)
    warnings = _build_warnings(bank, len(blocked))

    # 5. Build summary
    total_ev = sum(a.get("expected_value_usd", 0) for a in actions)
    today_revenue = 0.0
    try:
        tracker = _get_revenue_tracker()
        if tracker and hasattr(tracker, "get_today_summary"):
            today_revenue = tracker.get_today_summary().get("total_usd", 0)
    except Exception:
        pass

    return {
        "actions": actions,
        "ranked_cross_category": ranked_cross_category,
        "blocked": blocked,
        "completed_today": completed_today,
        "plan": plan,
        "warnings": warnings,
        "summary": {
            "total_expected_usd": round(total_ev, 2),
            "action_count": len(actions),
            "blocked_count": len(blocked),
            "completed_count": len(completed_today),
            "revenue_today_usd": round(today_revenue, 2),
        },
        "greeting": _greeting(),
    }


def _determine_next_action(opp: Any) -> dict[str, str]:
    """Determine the next concrete action for an opportunity — always actionable."""
    platform = getattr(opp, "platform", "").lower()
    category = getattr(opp, "category", "").lower()
    url = getattr(opp, "url", "") or ""

    platform_urls: dict[str, str] = {
        "outlier": "https://outlier.ai",
        "mindrift": "https://mindrift.ai",
        "dataannotation": "https://dataannotation.tech",
        "alignerr": "https://alignerr.com",
        "mercor": "https://work.mercor.com",
        "fiverr": "https://www.fiverr.com",
        "algora": "https://algora.io",
        "opire": "https://opire.dev",
        "kaggle": "https://www.kaggle.com/competitions",
        "dework": "https://app.dework.xyz",
        "github_bounty": "https://github.com/search?q=label%3Abounty",
        "hackerone": "https://hackerone.com/opportunities",
        "bugcrowd": "https://bugcrowd.com/programs",
    }
    p_url = platform_urls.get(platform, url)

    if "bug_bounty" in category or "security" in category:
        return {"label": "Start reconnaissance", "url": p_url, "command": "POST /api/direct-work/workbank/cycle"}
    elif (
        "software_engineering" in category
        or "backend" in category
        or "frontend" in category
        or "dev_bounty" in category
    ):
        return {
            "label": "Analyze issue and generate fix",
            "url": url or p_url,
            "command": "POST /direct-work/workbank/{id}/deliver/prepare",
        }
    elif platform in ("outlier", "mindrift", "dataannotation", "alignerr", "mercor"):
        return {"label": "Open platform and start task", "url": p_url, "command": f"Open {p_url}"}
    elif platform in ("fiverr", "workana"):
        return {
            "label": "Review requirements and prepare proposal",
            "url": p_url,
            "command": "GET /api/client-acquisition/leads",
        }
    elif "ai_training" in category or "ai_evaluation" in category:
        return {"label": "Open platform and begin evaluation", "url": p_url, "command": f"Open {p_url}"}
    else:
        return {"label": "Review opportunity details", "url": url or p_url, "command": "GET /api/direct-work/recommend"}


def _greeting() -> str:
    """Generate a time-appropriate greeting."""
    from datetime import UTC, datetime

    hour = datetime.now(UTC).hour
    if hour < 6:
        return "Night owl mode — focus on high-EV opportunities"
    elif hour < 12:
        return "Good morning — let's find today's best opportunity"
    elif hour < 18:
        return "Good afternoon — time to execute and deliver"
    else:
        return "Evening wrap-up — review completed work and plan tomorrow"


# ── Full-day plan + warnings ─────────────────────────────────────────


def _current_phase() -> str:
    """Local hour bucket: morning (5-12), afternoon (12-19), evening (19-24/0-5)."""
    from datetime import datetime

    h = datetime.now().hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 19:
        return "afternoon"
    return "evening"


def _build_warnings(workbank, blocked_count: int) -> list[dict[str, str]]:
    """System warnings the user must see today (setup, access, AI, stale scans)."""
    warnings: list[dict[str, str]] = []

    if blocked_count:
        warnings.append(
            {
                "level": "warning",
                "title": f"{blocked_count} entrega(s) esperan tu aprobación",
                "hint": "Sin tu aprobación el pipeline queda bloqueado.",
                "path": "/operations/work-queue",
            }
        )

    if workbank is not None:
        try:
            needs = list(workbank.needs_access()) if hasattr(workbank, "needs_access") else []
            if needs:
                warnings.append(
                    {
                        "level": "warning",
                        "title": f"{len(needs)} trabajo(s) bloqueado(s) por acceso a plataforma",
                        "hint": "Conectá la plataforma para desbloquear entregas.",
                        "path": "/integrations/accounts",
                    }
                )
        except Exception:
            pass

    try:
        from cores.setup.checklist import get_setup_checklist

        status = get_setup_checklist().status()
        if not status.get("complete", True):
            task = status.get("next_task") or {}
            warnings.append(
                {
                    "level": "info",
                    "title": f"Setup al {status.get('complete_pct', 0)}% — tarea de hoy pendiente",
                    "hint": str(task.get("title", "completar checklist")),
                    "path": "/setup/checklist",
                }
            )
    except Exception:
        pass

    try:
        from cores.ai.provider import get_registry

        if not get_registry().get_provider().is_available():
            warnings.append(
                {
                    "level": "error",
                    "title": "IA no disponible",
                    "hint": "El análisis automático está en fallback. Revisá el proveedor en Settings → IA.",
                    "path": "/operations/settings",
                }
            )
    except Exception:
        pass

    return warnings


def _build_plan(actions: list[dict[str, Any]], workbank) -> dict[str, Any]:
    """Structure today's actions into morning/afternoon/evening phases."""
    current = _current_phase()

    def _bucket(kind: str) -> list[dict[str, Any]]:
        return [a for a in actions if a.get("action_type") == kind]

    deliveries = _bucket("delivery")
    opportunities = _bucket("opportunity")

    morning = deliveries[:2] + opportunities[:2]
    afternoon = opportunities[2:6]
    evening = deliveries[2:4]

    def _pack(items: list[dict[str, Any]], note: str) -> dict[str, Any]:
        return {
            "items": items[:4],
            "note": note,
            "total_ev_usd": round(sum(i.get("expected_value_usd", 0) for i in items[:4]), 2),
        }

    return {
        "current_phase": current,
        "morning": _pack(morning, "Enviar entregas listas + arrancar la oportunidad con mayor EV/h"),
        "afternoon": _pack(afternoon, "Ejecutar y completar tareas de oportunidad en curso"),
        "evening": _pack(evening, "Segundas entregas + revisar qué bloqueó el día"),
    }
