"""Daily Decision Digest — ONE endpoint that answers "what needs my attention today?"

Aggregates from ALL systems:
- WorkBank items needing review
- Execution Queue items in WAITING_HUMAN
- Security findings queued for human review
- Best opportunity right now (from EconomicEngine)
- Capital snapshot summary
- AI health status

The user should open this ONE thing and know everything.
Max 5 decisions shown, sorted by money impact.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api/daily-digest", tags=["daily-digest"])
logger = logging.getLogger("ownex.daily_digest")


@router.get("")
async def daily_digest() -> dict[str, Any]:
    """The ONE call that answers: what matters today?"""
    digest: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "decisions": [],
        "money": {},
        "best_action": None,
        "system_health": {},
        "counts": {},
    }

    # ── Money ──
    try:
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()
        ready = [i for i in wb._items.values() if i.status == "ready_to_deliver"]
        public_ready = [i for i in ready if i.access_status == "public"]
        best = max(ready, key=lambda x: x.reward) if ready else None
        digest["money"] = {
            "ready_to_deliver": len(ready),
            "public_ready": len(public_ready),
            "total_potential_usd": round(sum(i.reward for i in ready), 0),
            "best_target": {"title": best.title[:60], "reward": best.reward} if best else None,
        }
    except Exception as e:
        logger.debug("workbank digest error: %s", e)

    # ── Pending decisions ──
    decisions: list[dict] = []

    # Work Bank review queue
    try:
        from cores.direct_work_engine.workbank import get_workbank

        wb = get_workbank()
        for i in list(wb._items.values())[:3]:
            if i.status == "ready_to_deliver" and i.access_status == "public":
                decisions.append(
                    {
                        "type": "opportunity",
                        "title": i.title[:70],
                        "platform": i.platform,
                        "reward": i.reward,
                        "action": f"Ejecutar en {i.platform}",
                        "url": i.url,
                        "priority": i.reward,
                    }
                )
    except Exception:
        pass

    # Execution Queue WAITING_HUMAN
    try:
        from core.execution_queue.models import ExecutionQueueStore

        eq = ExecutionQueueStore()
        waiting = eq.pending_by_state("waiting_human")
        for item_id in waiting[:3]:
            item = eq.get(item_id)
            if item and item.get("payload"):
                p = item["payload"]
                decisions.append(
                    {
                        "type": "execution_review",
                        "title": str(p.get("title", item_id))[:70],
                        "reward": p.get("reward"),
                        "action": "Revisar y aprobar ejecución",
                        "url": "/operations/work-queue",
                        "priority": float(p.get("reward", 0)),
                    }
                )
    except Exception:
        pass

    # Security findings in review
    try:
        from database import db, models

        session = db.SessionLocal()
        try:
            confirmed = (
                session.query(models.Finding)
                .filter(models.Finding.status == "confirmed")
                .order_by(models.Finding.id.desc())
                .limit(3)
                .all()
            )
            for f in confirmed:
                decisions.append(
                    {
                        "type": "security_finding",
                        "title": getattr(f, "title", "")[:70] or f"Finding #{f.id}",
                        "severity": getattr(f, "severity", "medium"),
                        "action": "Validar y aprobar submission",
                        "url": "/intelligence/findings",
                        "priority": {"critical": 5000, "high": 2000}.get(getattr(f, "severity", ""), 500),
                    }
                )
        finally:
            session.close()
    except Exception:
        pass

    # Sort by priority desc, take top 5
    decisions.sort(key=lambda d: -float(d.get("priority", 0)))
    digest["decisions"] = decisions[:5]
    digest["counts"] = {"pending_decisions": len(decisions)}

    # ── Best Action (the ONE thing to do) ──
    if decisions:
        top = decisions[0]
        digest["best_action"] = {
            **top,
            "why": "Mayor recompensa esperada entre tus decisiones pendientes",
        }

    # ── System Health ──
    health_items = []
    try:
        import httpx

        r = httpx.get("http://localhost:8000/api/system/health", timeout=2)
        if r.status_code == 200:
            data = r.json()
            health_items = [
                {"name": k, "status": v if isinstance(v, str) else str(v)}
                for k, v in data.items()
                if isinstance(v, (str, bool))
            ]
    except Exception:
        pass
    digest["system_health"] = {"services": health_items[:6]}

    return digest
