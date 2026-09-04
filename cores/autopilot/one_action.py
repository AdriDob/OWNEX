"""One Action Contract — Canonical model for the single best action OWNEX recommends.

This is the central contract for the Daily Autopilot. Every day, OWNEX produces
exactly ONE action that the human should execute. No competing recommendations,
no dashboards full of options. Just: DO THIS NOW.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from cores.direct_work_engine.availability import (
    can_accommodate_task,
    get_availability_engine,
    get_available_hours,
    recommend_max_task_hours,
)


class ActionType(StrEnum):
    """Type of action the human needs to take."""

    DELIVER_WORK = "deliver_work"
    SUBMIT_BOUNTY = "submit_bounty"
    SUBMIT_DEV_BOUNTY = "submit_dev_bounty"
    APPLY_PLATFORM = "apply_platform"
    COMPLETE_ONBOARDING = "complete_onboarding"
    APPROVE_PR = "approve_pr"
    APPROVE_DELIVERY = "approve_delivery"
    APPROVE_REBALANCE = "approve_rebalance"
    STRATEGIC_DECISION = "strategic_decision"
    COMPLETE_ASSESSMENT = "complete_assessment"
    SETUP_PAYMENT = "setup_payment"
    SETUP_API = "setup_api"
    REVIEW_FINDING = "review_finding"
    STRATEGIC_REVIEW = "strategic_review"


class ActionUrgency(StrEnum):
    IMMEDIATE = "immediate"
    TODAY = "today"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    FLEXIBLE = "flexible"


class ConfidenceBand(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class OneAction:
    """
    The One Action Contract — the single best action OWNEX recommends right now.

    This is the canonical output of the Daily Autopilot. Every field is designed
    to give the human everything they need to execute without ambiguity.
    """

    # Identity
    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:12]}")
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    # Classification
    action_type: ActionType = field(default=ActionType.STRATEGIC_REVIEW)
    urgency: ActionUrgency = field(default=ActionUrgency.FLEXIBLE)
    deadline: datetime | None = None

    # Human-facing
    title: str = ""
    description: str = ""
    why: str = ""
    instruction: str = ""

    # Economics
    expected_value_usd: float = 0.0
    ev_per_human_hour_usd: float = 0.0
    estimated_human_hours: float = 0.0
    payoff_range: dict[str, float] | None = None
    cash_speed_days: int | None = None
    confidence_band: ConfidenceBand = field(default=ConfidenceBand.UNKNOWN)
    success_probability: float = 0.0
    acceptance_probability: float = 0.0
    payment_probability: float = 0.0

    # Risk
    risk_level: str = "low"
    risk_factors: list[str] = field(default_factory=list)

    # Platform & Context
    platform: str = ""
    platform_readiness_pct: int = 0
    assessment_required: bool = False
    zero_experience: bool = True
    zero_barrier: bool = True

    # Execution
    url: str | None = None
    platform_name: str = ""
    platform_url: str = ""
    deliverables: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)

    # Metadata
    source: str = ""
    item_id: str = ""
    payoff_range_usd: dict[str, float] | None = None
    expected_cash: dict[str, Any] | None = None
    htroi: float | None = None

    # Availability Intelligence
    available_hours_today: float = 0.0
    available_hours_week: float = 0.0
    available_hours_month: float = 0.0
    can_accommodate: bool = True
    max_recommended_hours: float = 0.0
    availability_source: str = "profile_kit"
    time_blocks: list[dict] = field(default_factory=list)

    # Tracking
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for API/JSON."""
        data = asdict(self)
        data["action_type"] = self.action_type.value
        data["urgency"] = self.urgency.value
        data["confidence_band"] = self.confidence_band.value
        for key in ["generated_at", "expires_at", "deadline", "created_at", "updated_at"]:
            if data.get(key) and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        return data

    @property
    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.now(UTC) > self.expires_at
        return False

    @property
    def is_actionable(self) -> bool:
        return not self.is_expired and (bool(self.url) or bool(self.instruction))

    @property
    def priority_score(self) -> float:
        base = self.ev_per_human_hour_usd * self.success_probability
        urgency_multiplier = {
            "immediate": 10.0,
            "today": 5.0,
            "this_week": 2.0,
            "this_month": 1.0,
            "flexible": 0.5,
        }.get(self.urgency.value, 1.0)
        # Availability factor: if can't accommodate, heavily penalize
        availability_factor = 1.0 if self.can_accommodate else 0.1
        # Availability fit: how well the action fits in available time
        if self.estimated_human_hours > 0 and self.available_hours_today > 0:
            fit_ratio = min(1.0, self.available_hours_today / self.estimated_human_hours)
            availability_factor *= max(0.5, fit_ratio)
        return base * urgency_multiplier * self.success_probability * availability_factor


def create_deliver_action(item: dict[str, Any]) -> OneAction:
    """Create OneAction from a WorkBank item ready to deliver."""
    float(item.get("reward") or 0.0)
    action = OneAction(
        action_type=ActionType.DELIVER_WORK,
        urgency=ActionUrgency.TODAY,
    )
    reward_val = float(item.get("reward") or 0.0)
    action.title = f"Entregar: {item.get('title', 'Trabajo')}"
    action.description = f"Entregar trabajo completado a {item.get('platform', 'plataforma')}"
    action.why = f"Trabajo completado listo para entregar. Recompensa: ${reward_val:,.0f}"
    action.instruction = "1. Abrir paquete de entrega\n2. Revisar guía de submission\n3. Ejecutar submission en plataforma\n3. Marcar como entregado en OWNEX"
    action.expected_value_usd = float(item.get("reward") or 0.0)
    action.ev_per_human_hour_usd = 0.0
    action.estimated_human_hours = 0.25
    action.payoff_range = {"low": float(item.get("reward") or 0.0), "high": float(item.get("reward") or 0.0)}
    action.cash_speed_days = item.get("payout_cadence_days")
    action.confidence_band = ConfidenceBand.HIGH
    action.success_probability = 0.95
    action.acceptance_probability = 0.99
    action.payment_probability = 0.9
    action.risk_level = "low"
    action.platform = item.get("platform", "")
    action.platform_name = item.get("platform", "")
    action.url = item.get("url")
    action.deliverables = item.get("deliverables", [])
    action.prerequisites = ["Cuenta configurada en plataforma"]
    action.source = "workbank"
    action.item_id = item.get("id", "")
    action.payoff_range_usd = {"low": float(item.get("reward") or 0.0), "high": float(item.get("reward") or 0.0)}

    # Populate availability data
    try:
        action.available_hours_today = get_available_hours("today")
        action.available_hours_week = get_available_hours("this_week")
        action.available_hours_month = get_available_hours("this_month")
        action.max_recommended_hours = recommend_max_task_hours("today")
        engine = get_availability_engine()
        profile = engine._profile_kit.get() if engine._profile_kit else None
        action.availability_source = (
            getattr(profile, "availability_source", "profile_kit") if profile else "profile_kit"
        )
        action.can_accommodate, _ = can_accommodate_task(0.25, "today")
        blocks = engine.get_time_blocks(7)
        action.time_blocks = [{"start": b.start, "end": b.end, "type": b.type, "title": b.title} for b in blocks]
    except Exception:
        pass

    return action


def create_submit_bounty_action(item: dict[str, Any]) -> OneAction:
    """Create OneAction for submitting a bug bounty finding."""
    float(item.get("reward") or 0.0)
    action = OneAction(
        action_type=ActionType.SUBMIT_BOUNTY,
        urgency=ActionUrgency.TODAY,
    )
    action.title = f"Reportar: {item.get('title', 'Hallazgo')}"
    action.description = (
        f"Enviar reporte de {item.get('vulnerability_type', 'vulnerabilidad')} a {item.get('platform', 'programa')}"
    )
    action.why = f"Hallazgo validado listo para submission. Recompensa estimada: ${item.get('reward', 0):,.0f}"
    action.instruction = (
        "1. Revisar evidencia y PoC\n2. Completar formulario de submission\n3. Adjuntar evidencia\n4. Enviar reporte"
    )
    action.expected_value_usd = float(item.get("reward") or 0.0)
    action.ev_per_human_hour_usd = float(item.get("ev_per_human_hour_usd") or 0.0)
    action.estimated_human_hours = item.get("estimated_human_hours", 2.0)
    action.payoff_range = {"low": float(item.get("reward") or 0.0) * 0.5, "high": float(item.get("reward") or 0.0)}
    action.cash_speed_days = item.get("payout_cadence_days")
    action.confidence_band = ConfidenceBand.MEDIUM
    action.success_probability = item.get("acceptance_probability", 0.5)
    action.acceptance_probability = item.get("acceptance_probability", 0.5)
    action.payment_probability = 0.8
    action.risk_level = "medium"
    action.platform = item.get("platform", "")
    action.platform_name = item.get("program", "")
    action.url = item.get("submission_url")
    action.deliverables = ["Reporte técnico", "Evidencia/PoC", "Pasos de reproducción"]
    action.prerequisites = ["Cuenta en plataforma", "Evidencia preparada"]
    action.source = "bounty_scanner"
    action.item_id = item.get("id", "")
    action.payoff_range_usd = {"low": float(item.get("reward") or 0.0) * 0.5, "high": float(item.get("reward") or 0.0)}

    # Populate availability data
    try:
        action.available_hours_today = get_available_hours("today")
        action.available_hours_week = get_available_hours("this_week")
        action.available_hours_month = get_available_hours("this_month")
        action.max_recommended_hours = recommend_max_task_hours("today")
        engine = get_availability_engine()
        profile = engine._profile_kit.get() if engine._profile_kit else None
        action.availability_source = (
            getattr(profile, "availability_source", "profile_kit") if profile else "profile_kit"
        )
        action.can_accommodate, _ = can_accommodate_task(action.estimated_human_hours, "today")
        blocks = engine.get_time_blocks(7)
        action.time_blocks = [{"start": b.start, "end": b.end, "type": b.type, "title": b.title} for b in blocks]
    except Exception:
        pass

    return action


def create_apply_platform_action(platform_data: dict[str, Any]) -> OneAction:
    """Create OneAction for applying to a platform (Outlier, Fiverr, etc.)."""
    rate = platform_data.get("hourly_rate_usd")
    action = OneAction(
        action_type=ActionType.APPLY_PLATFORM,
        urgency=ActionUrgency.THIS_WEEK,
    )
    action.title = f"Aplicar a {platform_data.get('name', 'Plataforma')}"
    action.description = f"Completar aplicación y assessment en {platform_data.get('name', 'plataforma')}"
    action.why = f"Plataforma con tarifa documentada ${rate}/h. Assessment abre stream de ingresos recurrente."
    action.instruction = "1. Crear cuenta\n2. Completar assessment\n3. Configurar perfil\n4. Esperar aprobación"
    action.expected_value_usd = float(platform_data.get("hourly_rate_usd", 0) * 20 * 4)
    action.ev_per_human_hour_usd = float(platform_data.get("hourly_rate_usd", 0))
    action.estimated_human_hours = platform_data.get("time_to_first_work_hours", 5.0)
    action.payoff_range = {"low": 50.0, "high": 500.0}
    action.cash_speed_days = platform_data.get("payout_cadence_days")
    action.confidence_band = ConfidenceBand.MEDIUM
    action.success_probability = 0.3
    action.acceptance_probability = 0.3
    action.payment_probability = 0.9
    action.risk_level = "low"
    action.platform = platform_data.get("key", "")
    action.platform_name = platform_data.get("name", "")
    action.platform_url = platform_data.get("url", "")
    action.assessment_required = True
    action.zero_experience = platform_data.get("zero_experience", True)
    action.zero_barrier = platform_data.get("zero_barrier", False)
    action.url = platform_data.get("url")
    action.platform_readiness_pct = platform_data.get("readiness_pct", 50)
    action.prerequisites = ["Crear cuenta", "Completar assessment", "Verificar identidad"]
    action.source = "applications"
    action.item_id = platform_data.get("key", "")

    # Populate availability data
    try:
        action.available_hours_today = get_available_hours("today")
        action.available_hours_week = get_available_hours("this_week")
        action.available_hours_month = get_available_hours("this_month")
        action.max_recommended_hours = recommend_max_task_hours("today")
        engine = get_availability_engine()
        profile = engine._profile_kit.get() if engine._profile_kit else None
        action.availability_source = (
            getattr(profile, "availability_source", "profile_kit") if profile else "profile_kit"
        )
        action.can_accommodate, _ = can_accommodate_task(action.estimated_human_hours, "today")
        blocks = engine.get_time_blocks(7)
        action.time_blocks = [{"start": b.start, "end": b.end, "type": b.type, "title": b.title} for b in blocks]
    except Exception:
        pass

    return action


class OneActionFactory:
    """Factory that produces the single best OneAction from all available sources."""

    def __init__(self):
        self._sources: list[Callable] = []

    def register_source(self, source_fn: Callable) -> None:
        """Register a source function that returns a list of OneAction candidates."""
        self._sources.append(source_fn)

    def get_best_action(self, context: dict[str, Any] | None = None) -> OneAction | None:
        """Get the single best action from all registered sources."""
        all_actions: list[OneAction] = []

        for source in self._sources:
            try:
                actions = source(context)
                if actions:
                    all_actions.extend(actions if isinstance(actions, list) else [actions])
            except Exception:
                pass

        if not all_actions:
            return self._create_no_action()

        # Filter out actions that can't be accommodated
        feasible_actions = [a for a in all_actions if a.can_accommodate]

        # If no feasible actions, return the best overall (with warning in why)
        if not feasible_actions:
            all_actions.sort(key=lambda a: a.priority_score, reverse=True)
            best = all_actions[0]
            best.why += " ⚠️ ADVERTENCIA: Esta acción excede tu disponibilidad actual."
        else:
            feasible_actions.sort(key=lambda a: a.priority_score, reverse=True)
            best = feasible_actions[0]

        if best.urgency == "immediate":
            best.expires_at = datetime.now(UTC) + timedelta(hours=24)
        elif best.urgency == "today":
            best.expires_at = datetime.now(UTC) + timedelta(days=1)
        elif best.urgency == "this_week":
            best.expires_at = datetime.now(UTC) + timedelta(days=7)

        return best

    def _create_no_action(self) -> OneAction:
        """Create a 'no action required' action."""
        action = OneAction(
            action_type=ActionType.STRATEGIC_REVIEW,
            urgency=ActionUrgency.FLEXIBLE,
        )
        action.title = "NO ACTION REQUIRED"
        action.description = "OWNEX no ha encontrado acciones que valgan tu tiempo ahora mismo."
        action.why = "Ninguna acción supera el umbral mínimo de valor esperado por hora humana."
        action.instruction = "Relajate. OWNEX seguirá monitoreando y te avisará cuando haya algo valioso."
        action.expected_value_usd = 0.0
        action.ev_per_human_hour_usd = 0.0
        action.confidence_band = ConfidenceBand.HIGH
        action.success_probability = 1.0
        action.risk_level = "none"
        return action


# Singleton factory
_one_action_factory: OneActionFactory | None = None


def get_one_action_factory() -> OneActionFactory:
    global _one_action_factory
    if _one_action_factory is None:
        _one_action_factory = OneActionFactory()
    return _one_action_factory
