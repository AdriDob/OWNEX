from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter

from cores.intelligence.reward_learning import RewardLearner
from database import db, models

logger = logging.getLogger("cateye.api.hunter")

router = APIRouter(prefix="/api/hunter", tags=["hunter"])


@router.get("/summary")
def hunter_summary():
    """Return a single daily bug bounty overview."""
    db.init_db()
    session = db.SessionLocal()
    try:
        target_count = session.query(models.Target).count()
        pending = session.query(models.Finding).filter(
            models.Finding.status == "open"
        ).count()
        confirmed = session.query(models.Finding).filter(
            models.Finding.status == "confirmed"
        ).count()

        month_ago = datetime.utcnow() - timedelta(days=30)
        monthly_reports = session.query(models.Report).filter(
            models.Report.created_at >= month_ago
        ).count() if hasattr(models, "Report") else 0

        learner = RewardLearner()
        reward_report = learner.analyze()
        total_confirmed = reward_report.total_confirmed_value if reward_report else 0.0
        total_estimated = 0.0
        if hasattr(models, "Report"):
            total_estimated = sum(
                float(r.estimated_reward or 0.0)
                for r in session.query(models.Report).all()
            )

        return {
            "active_targets": target_count,
            "pending_findings": pending,
            "confirmed_findings": confirmed,
            "reports_this_month": monthly_reports,
            "total_confirmed_payout": round(total_confirmed, 2),
            "total_estimated_payout": round(total_estimated, 2),
            "currency": "USD",
        }
    except Exception as e:
        logger.warning("Hunter summary failed: %s", e)
        return {
            "active_targets": 0,
            "pending_findings": 0,
            "confirmed_findings": 0,
            "reports_this_month": 0,
            "total_confirmed_payout": 0.0,
            "total_estimated_payout": 0.0,
            "currency": "USD",
            "error": str(e),
        }
    finally:
        session.close()
