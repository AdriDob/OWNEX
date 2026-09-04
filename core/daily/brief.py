"""Daily Brief Engine — Generates actionable daily briefing for the user.

Consolidates: critical actions, high-value opportunities, autonomous work status,
waiting items, completed work, and revenue summary into a single actionable briefing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from database.db import SessionLocal

logger = logging.getLogger("ownex.daily.brief")


# ── Data Classes ────────────────────────────────────────────────


@dataclass
class ActionItem:
    """An actionable item for the user."""

    title: str
    why: str
    exact_steps: list[str] = field(default_factory=list)
    files_needed: list[str] = field(default_factory=list)
    url: str | None = None
    deadline: str | None = None
    estimated_time_min: int | None = None
    priority: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    category: str = "ACTION"  # CRITICAL, HIGH_VALUE, WAITING, DONE


@dataclass
class AutonomousWork:
    """Currently running autonomous work."""

    mission_id: str
    mission_type: str
    current_stage: str
    progress_pct: float
    eta_minutes: int | None
    expected_value_usd: float = 0.0


@dataclass
class WaitingItem:
    """Work waiting for user/external action."""

    mission_id: str
    reason: str
    waiting_for: str  # "human_approval", "external_api", "platform_response"
    blocked_since: str
    expected_value_usd: float = 0.0


@dataclass
class CompletedWork:
    """Recently completed work."""

    mission_id: str
    title: str
    completed_at: str
    actual_value_usd: float
    platform: str | None = None


@dataclass
class RevenueSummary:
    """Revenue summary for the briefing."""

    potential_usd: float = 0.0
    committed_usd: float = 0.0
    in_progress_usd: float = 0.0
    delivered_usd: float = 0.0
    submitted_usd: float = 0.0
    accepted_usd: float = 0.0
    awarded_usd: float = 0.0
    pending_payout_usd: float = 0.0
    paid_usd: float = 0.0
    net_usd: float = 0.0


@dataclass
class DailyBrief:
    """Complete daily briefing for the user."""

    generated_at: str
    critical: list[ActionItem] = field(default_factory=list)
    high_value: list[ActionItem] = field(default_factory=list)
    autonomous: list[dict[str, Any]] = field(default_factory=list)
    waiting: list[dict[str, Any]] = field(default_factory=list)
    completed: list[dict[str, Any]] = field(default_factory=list)
    revenue: dict[str, float] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)


# ── Daily Brief Engine ────────────────────────────────────────


class DailyBriefEngine:
    """Generates the daily actionable briefing for the user."""

    def __init__(self, session_factory: Any = None) -> None:
        self._session_factory = session_factory or SessionLocal

    def _get_session(self):
        return self._session_factory()

    def generate(self) -> dict[str, Any]:
        """Generate the complete daily briefing."""
        brief = DailyBrief(generated_at=datetime.now(UTC).isoformat())

        # 1. CRITICAL - Immediate actions required
        brief.critical = self._get_critical_actions()

        # 2. HIGH_VALUE - Best opportunities to act on
        brief.high_value = self._get_high_value_opportunities()

        # 3. AUTONOMOUS - Work running without intervention
        brief.autonomous = self._get_autonomous_work()

        # 4. WAITING - Blocked on user/external
        brief.waiting = self._get_waiting_items()

        # 5. COMPLETED - Recently finished
        brief.completed = self._get_completed_work()

        # 6. REVENUE - Financial summary
        brief.revenue = self._get_revenue_summary()

        # 7. ALERTS - Calibration drift, system issues
        brief.alerts = self._get_alerts()

        return asdict(brief)

    # ── Critical Actions ────────────────────────────────────────

    def _get_critical_actions(self) -> list[ActionItem]:
        """Get actions that require immediate user attention."""
        actions = []
        session = self._get_session()

        try:
            # Missions waiting for human approval
            from core.mission.controller import get_mission_controller

            mission_ctrl = get_mission_controller()

            waiting_human = mission_ctrl.get_waiting_human_missions()
            for mission in waiting_human:
                context = json.loads(mission.context_json) if mission.context_json else {}
                platform = context.get("platform", "unknown")
                opportunity = context.get("opportunity_id", "unknown")

                actions.append(
                    ActionItem(
                        title=f"Aprobar submission: {platform} / {opportunity}",
                        why=f"Mission {mission.mission_id} está esperando tu aprobación para enviar",
                        exact_steps=[
                            f"1. Revisa el deliverable en OWNEX/artifacts/{mission.mission_id}/",
                            "2. Verifica que el reporte/entrega esté completo",
                            f"3. Ejecuta POST /api/mission/{mission.mission_id}/unblock para aprobar",
                            f"4. O ejecuta POST /api/mission/{mission.mission_id}/fail si hay problemas",
                        ],
                        files_needed=[f"OWNEX/artifacts/{mission.mission_id}/*"],
                        deadline=(
                            datetime.fromisoformat(mission.last_heartbeat.replace("Z", "+00:00")) + timedelta(hours=4)
                        ).isoformat()
                        if mission.last_heartbeat
                        else None,
                        estimated_time_min=5,
                        priority="CRITICAL",
                        category="CRITICAL",
                    )
                )

            # Missions that failed and need retry decision
            from core.mission.store import MissionModel, MissionStatus, get_mission_store

            store = get_mission_store()
            session = store._get_session()
            try:
                failed_missions = (
                    session.query(MissionModel)
                    .filter(MissionModel.status == MissionStatus.FAILED.value)
                    .order_by(MissionModel.updated_at.desc())
                    .limit(3)
                    .all()
                )
                for mission in failed_missions:
                    if mission.retry_count < mission.max_retries:
                        actions.append(
                            ActionItem(
                                title=f"Decidir retry: {mission.mission_id} (fallo #{mission.retry_count})",
                                why=f"Mission falló: {mission.error_message or 'error desconocido'}",
                                exact_steps=[
                                    f"1. Revisa error: {mission.error_message}",
                                    f"2. Ejecuta POST /api/mission/{mission.mission_id}/advance para reintentar",
                                    f"3. O ejecuta POST /api/mission/{mission.mission_id}/cancel si es irrecuperable",
                                ],
                                estimated_time_min=3,
                                priority="CRITICAL",
                                category="CRITICAL",
                            )
                        )
            finally:
                session.close()

            # Jobs that failed > 3 retries

            try:
                # Check for jobs with high failure rates
                pass
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"[DAILY_BRIEF] Error getting critical actions: {e}")

        return actions[:5]  # Limit to top 5

    # ── High Value Opportunities ────────────────────────────────

    def _get_high_value_opportunities(self) -> list[ActionItem]:
        """Get top 3 opportunities by expected net value."""
        actions = []

        try:
            # Note: Direct Work Engine is in cores/, not core/
            from cores.direct_work_engine.engine import get_direct_work_engine
            from cores.direct_work_engine.workbank import get_workbank

            dwe = get_direct_work_engine()
            workbank = get_workbank()

            # Get best ready-to-deliver items
            best = workbank.best_ready()
            for item in best[:3]:
                # WorkItem may have different attribute names
                reward = getattr(item, "reward", getattr(item, "reward_usd", 0))
                est_hours = getattr(item, "estimated_time_hours", getattr(item, "estimated_hours", 0))
                acceptance = getattr(item, "acceptance_probability", getattr(item, "acceptance", 0))
                item_id = getattr(item, "item_id", getattr(item, "id", "unknown"))
                platform = getattr(item, "platform", "unknown")
                title = getattr(item, "title", "Unknown")

                actions.append(
                    ActionItem(
                        title=f"Entregar: {platform} - {title}",
                        why=f"${reward:.0f} | {est_hours}h | probabilidad aceptación: {acceptance:.0%}",
                        exact_steps=[
                            f"1. Ejecuta POST /api/direct-work/workbank/{item_id}/deliver/prepare",
                            "2. Revisa los archivos generados en OWNEX/artifacts/",
                            f"3. Sube el deliverable a {platform}",
                            f"4. Ejecuta POST /api/direct-work/workbank/{item_id}/deliver/approve",
                        ],
                        files_needed=[f"OWNEX/artifacts/{platform}/{item_id}/*"],
                        deadline=getattr(item, "deadline", None),
                        estimated_time_min=int(est_hours * 60) if est_hours else None,
                        priority="HIGH",
                        category="HIGH_VALUE",
                    )
                )

            # If no ready items, check for new opportunities
            if not actions:
                result = dwe.run_cycle()
                for item in result.get("ranked", [])[:3]:
                    platform = getattr(item, "platform", "unknown")
                    title = getattr(item, "title", "Unknown")
                    reward = getattr(item, "reward", getattr(item, "reward_usd", 0))
                    evh = getattr(item, "evh", getattr(item, "ev_per_hour", 0))
                    zbs = getattr(item, "zero_barrier_score", getattr(item, "barrier_score", 0))
                    access_req = getattr(item, "access_requirements", "Verificar en plataforma")

                    actions.append(
                        ActionItem(
                            title=f"Nueva oportunidad: {platform} - {title}",
                            why=f"${reward:.0f} | EV/h: {evh:.0f} | barrera: {zbs:.0f}/100",
                            exact_steps=[
                                "1. Ejecuta POST /api/direct-work/workbank/cycle para prepararla",
                                f"2. Revisa requisitos de acceso: {access_req}",
                                "3. Si tienes acceso, marca como ready_to_deliver",
                            ],
                            estimated_time_min=10,
                            priority="HIGH",
                            category="HIGH_VALUE",
                        )
                    )

        except Exception as e:
            logger.warning(f"[DAILY_BRIEF] Error getting high value: {e}")

        return actions[:3]

    # ── Autonomous Work ────────────────────────────────────────

    def _get_autonomous_work(self) -> list[dict[str, Any]]:
        """Get currently running autonomous work."""
        works = []

        try:
            from core.mission.controller import get_mission_controller

            mission_ctrl = get_mission_controller()

            active = mission_ctrl.get_active_missions()
            for mission in active:
                if mission.status == "running":
                    works.append(
                        {
                            "mission_id": mission.mission_id,
                            "mission_type": mission.mission_type,
                            "current_stage": mission.current_stage,
                            "progress_pct": round((mission.stage_order / max(mission.total_stages, 1)) * 100, 1),
                            "eta_minutes": max(
                                1, int((mission.total_stages - mission.stage_order) * 30)
                            ),  # ~30 min per stage
                            "expected_value_usd": mission.expected_value_usd,
                        }
                    )
        except Exception as e:
            logger.warning(f"[DAILY_BRIEF] Error getting autonomous work: {e}")

        return works

    # ── Waiting Items ──────────────────────────────────────────

    def _get_waiting_items(self) -> list[dict[str, Any]]:
        """Get items waiting for user/external action."""
        waiting = []

        try:
            from core.mission.controller import get_mission_controller

            mission_ctrl = get_mission_controller()

            # Waiting for human
            waiting_human = mission_ctrl.get_waiting_human_missions()
            for mission in waiting_human:
                context = json.loads(mission.context_json) if mission.context_json else {}
                waiting.append(
                    {
                        "mission_id": mission.mission_id,
                        "reason": "Esperando aprobación humana",
                        "waiting_for": "human_approval",
                        "blocked_since": mission.last_heartbeat or mission.updated_at.isoformat()
                        if mission.updated_at
                        else "",
                        "expected_value_usd": mission.expected_value_usd,
                    }
                )

            # Stale missions
            from core.mission.controller import get_mission_controller

            stale = mission_ctrl.get_stale_missions(max_age_hours=2.0)
            for mission in stale:
                waiting.append(
                    {
                        "mission_id": mission.mission_id,
                        "reason": f"Sin heartbeat > 2h (último: {mission.last_heartbeat})",
                        "waiting_for": "recovery",
                        "blocked_since": mission.last_heartbeat.isoformat() if mission.last_heartbeat else "",
                        "expected_value_usd": mission.expected_value_usd,
                    }
                )

        except Exception as e:
            logger.warning(f"[DAILY_BRIEF] Error getting waiting items: {e}")

        return waiting

    # ── Completed Work ────────────────────────────────────────

    def _get_completed_work(self) -> list[dict[str, Any]]:
        """Get recently completed work (last 24h)."""
        completed = []

        try:
            from datetime import timedelta

            from core.mission.store import MissionModel, MissionStatus, get_mission_store

            store = get_mission_store()
            cutoff = datetime.now(UTC) - timedelta(hours=24)

            session = store._get_session()
            try:
                missions = (
                    session.query(MissionModel)
                    .filter(MissionModel.status == MissionStatus.COMPLETED.value, MissionModel.completed_at >= cutoff)
                    .order_by(MissionModel.completed_at.desc())
                    .limit(5)
                    .all()
                )

                for mission in missions:
                    completed.append(
                        {
                            "mission_id": mission.mission_id,
                            "title": f"{mission.mission_type} / {mission.opportunity_id or 'N/A'}",
                            "completed_at": mission.completed_at.isoformat() if mission.completed_at else "",
                            "actual_value_usd": mission.actual_value_usd,
                            "platform": json.loads(mission.context_json).get("platform")
                            if mission.context_json
                            else None,
                        }
                    )
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"[DAILY_BRIEF] Error getting completed work: {e}")

        return completed

    # ── Revenue Summary ────────────────────────────────────────

    def _get_revenue_summary(self) -> dict[str, Any]:
        """Get revenue summary for dashboard."""
        try:
            from core.revenue.ledger import get_revenue_ledger

            ledger = get_revenue_ledger()
            return ledger.get_summary()
        except Exception as e:
            logger.warning(f"[DAILY_BRIEF] Error getting revenue summary: {e}")
            return {
                "total_gross_usd": 0.0,
                "total_fees_usd": 0.0,
                "total_fx_usd": 0.0,
                "total_tax_estimate_usd": 0.0,
                "total_net_usd": 0.0,
                "by_state": {},
            }

    # ── Alerts ────────────────────────────────────────────────

    def _get_alerts(self) -> list[dict[str, Any]]:
        """Get system alerts for the briefing."""
        alerts = []

        try:
            # Calibration alerts
            from core.learning.outcome_loop import get_outcome_learning_loop

            loop = get_outcome_learning_loop()
            alerts.extend(loop.check_calibration_alerts())

            # Stale missions
            from core.mission.controller import get_mission_controller

            mission_ctrl = get_mission_controller()
            stale = len(mission_ctrl.get_stale_missions(max_age_hours=2.0))
            if stale > 0:
                alerts.append(
                    {
                        "type": "STALE_MISSIONS",
                        "severity": "WARNING",
                        "message": f"{stale} misiones sin heartbeat > 2h",
                    }
                )

            # Failed missions with max retries
            from core.mission.store import MissionModel, MissionStatus, get_mission_store

            store = get_mission_store()
            session = store._get_session()
            try:
                failed = session.query(MissionModel).filter(MissionModel.status == MissionStatus.FAILED.value).all()
                max_retries_failed = [m for m in failed if m.retry_count >= m.max_retries]
                if max_retries_failed:
                    alerts.append(
                        {
                            "type": "MAX_RETRIES_EXCEEDED",
                            "severity": "CRITICAL",
                            "message": f"{len(max_retries_failed)} misiones agotaron reintentos",
                        }
                    )
            finally:
                session.close()

        except Exception as e:
            logger.warning(f"[DAILY_BRIEF] Error getting alerts: {e}")

        return alerts

    # ── Persistence ────────────────────────────────────────────

    def save_brief(self, brief: DailyBrief) -> None:
        """Save brief to database for history."""
        from core.daily.brief_store import save_brief

        save_brief(asdict(brief))


# ── Scheduler Job ───────────────────────────────────────────────


def run_daily_brief() -> dict[str, Any]:
    """Scheduler job: generate daily brief."""
    logger.info("[DAILY_BRIEF] Generating daily brief")
    engine = DailyBriefEngine()
    brief = engine.generate()
    engine.save_brief(brief)
    logger.info(
        f"[DAILY_BRIEF] Generated: {len(brief.critical)} critical, {len(brief.high_value)} high-value, {len(brief.autonomous)} autonomous, {len(brief.waiting)} waiting, {len(brief.completed)} completed"
    )
    return {
        "generated_at": brief.generated_at,
        "critical_count": len(brief.critical),
        "high_value_count": len(brief.high_value),
        "autonomous_count": len(brief.autonomous),
        "waiting_count": len(brief.waiting),
        "completed_count": len(brief.completed),
    }


# ── Singleton ──────────────────────────────────────────────────

_daily_brief_engine: DailyBriefEngine | None = None


def get_daily_brief_engine() -> DailyBriefEngine:
    global _daily_brief_engine
    if _daily_brief_engine is None:
        _daily_brief_engine = DailyBriefEngine()
    return _daily_brief_engine
