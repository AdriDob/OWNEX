"""First Money Workflow Tracker — Zero-to-Earning Pipeline.

Tracks the owner's progress from $0 through first earning:
Platform → Account → Profile → Payment → Opportunity → Prepare → Approve → Execute → Verify → Earn → Record

Each stage is a milestone. The system guides, tracks, and learns.

Extended with: Milestone Tracker ($100 → $500 → $1k → $2.5k → $5k → $10k)
and Engine Proximity (which income source is closest to next milestone).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

logger = logging.getLogger("ownex.first_money")


class IncomeEngine(StrEnum):
    """Motores de ingresos disponibles (Adriel Webs es OPCIONAL, no principal)."""

    AI_TRAINING = "ai_training"
    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"


class Milestone(StrEnum):
    """Hitos de ingreso acumulado."""

    M100 = "100"
    M500 = "500"
    M1K = "1k"
    M2_5K = "2.5k"
    M5K = "5k"
    M10K = "10k"
    # Aggressive mode: end-of-year stretch targets
    M5K_EOY = "5k_eoy"
    M10K_EOY = "10k_eoy"

    @property
    def usd(self) -> int:
        mapping = {
            Milestone.M100: 100,
            Milestone.M500: 500,
            Milestone.M1K: 1000,
            Milestone.M2_5K: 2500,
            Milestone.M5K: 5000,
            Milestone.M10K: 10000,
            Milestone.M5K_EOY: 5000,
            Milestone.M10K_EOY: 10000,
        }
        return mapping[self]

    @property
    def label(self) -> str:
        return f"${self.usd:,}"

    @property
    def is_aggressive(self) -> bool:
        return self in (Milestone.M5K_EOY, Milestone.M10K_EOY)


@dataclass
class EngineProximity:
    """Proximidad de un motor de ingresos al próximo hito."""

    engine: IncomeEngine
    label: str
    current_usd: float
    projected_usd: float
    next_milestone: Milestone
    usd_to_milestone: float
    pct_to_milestone: float
    engine_status: str  # "ready" | "needs_setup" | "needs_action" | "blocked"
    next_action: str
    action_url: str | None = None
    confidence: float = 0.5  # 0-1, qué tan confiable es la proyección

    @property
    def is_closest(self) -> bool:
        return self.usd_to_milestone <= 0


@dataclass
class MilestoneProgress:
    """Progreso hacia un hito específico."""

    milestone: Milestone
    current_total_usd: float
    usd_needed: float
    pct_complete: float
    engines_contributing: list[str]
    eta_days: int | None = None  # Estimación simple basada en ritmo actual


@dataclass
class DailyAction:
    """Acción concreta para hoy."""

    engine: IncomeEngine
    title: str
    description: str
    estimated_minutes: int
    impact_usd: float  # EV estimado
    priority: int  # 1 = highest
    url: str | None = None


class FirstMoneyStage(StrEnum):
    """Etapas del funnel Zero-to-Earning."""

    PLATFORM_SELECTED = "platform_selected"
    ACCOUNT_CREATED = "account_created"
    PROFILE_COMPLETED = "profile_completed"
    PAYMENT_CONFIGURED = "payment_configured"
    PLATFORM_LEARNED = "platform_learned"
    OPPORTUNITY_SELECTED = "opportunity_selected"
    ACTION_PREPARED = "action_prepared"
    HUMAN_APPROVED = "human_approved"
    EXECUTED = "executed"
    VERIFIED = "verified"
    FIRST_REVENUE = "first_revenue"
    REVENUE_RECORDED = "revenue_recorded"
    ANALYZED = "analyzed"
    NEXT_RECOMMENDED = "next_recommended"


class StageStatus(StrEnum):
    """Estado de cada etapa."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class StageProgress:
    """Progreso de una etapa."""

    stage: FirstMoneyStage
    status: StageStatus = StageStatus.NOT_STARTED
    started_at: str | None = None
    completed_at: str | None = None
    platform: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    blocking_reason: str | None = None


@dataclass
class FirstMoneyProgress:
    """Progreso completo del funnel First Money."""

    user_name: str
    current_stage: FirstMoneyStage = FirstMoneyStage.PLATFORM_SELECTED
    stages: dict[str, StageProgress] = field(default_factory=dict)
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str | None = None
    first_revenue_amount: float = 0.0
    first_revenue_platform: str | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self):
        # Initialize all stages
        for stage in FirstMoneyStage:
            if stage.value not in self.stages:
                self.stages[stage.value] = StageProgress(stage=stage)


class FirstMoneyTracker:
    """Tracker del funnel Zero-to-Earning."""

    STAGE_ORDER = list(FirstMoneyStage)

    STAGE_LABELS = {
        FirstMoneyStage.PLATFORM_SELECTED: "Plataforma seleccionada",
        FirstMoneyStage.ACCOUNT_CREATED: "Cuenta creada",
        FirstMoneyStage.PROFILE_COMPLETED: "Perfil completado",
        FirstMoneyStage.PAYMENT_CONFIGURED: "Pagos configurados",
        FirstMoneyStage.PLATFORM_LEARNED: "Plataforma aprendida",
        FirstMoneyStage.OPPORTUNITY_SELECTED: "Oportunidad seleccionada",
        FirstMoneyStage.ACTION_PREPARED: "Acción preparada",
        FirstMoneyStage.HUMAN_APPROVED: "Aprobación humana",
        FirstMoneyStage.EXECUTED: "Ejecutado",
        FirstMoneyStage.VERIFIED: "Verificado",
        FirstMoneyStage.FIRST_REVENUE: "Primer ingreso",
        FirstMoneyStage.REVENUE_RECORDED: "Ingreso registrado",
        FirstMoneyStage.ANALYZED: "Analizado",
        FirstMoneyStage.NEXT_RECOMMENDED: "Próxima recomendación",
    }

    STAGE_DESCRIPTIONS = {
        FirstMoneyStage.PLATFORM_SELECTED: "Elegir la primera plataforma para empezar (HackerOne, Fiverr, Outlier, etc.)",
        FirstMoneyStage.ACCOUNT_CREATED: "Registrarse en la plataforma con email real y verificar",
        FirstMoneyStage.PROFILE_COMPLETED: "Completar bio, skills, foto, 2FA. Credibilidad = más oportunidades",
        FirstMoneyStage.PAYMENT_CONFIGURED: "Configurar método de cobro (Payoneer, PayPal, Wise, Stripe). Sin esto no cobras",
        FirstMoneyStage.PLATFORM_LEARNED: "Entender UI, terminología, reglas, scope, submission flow. Leer guías oficiales",
        FirstMoneyStage.OPPORTUNITY_SELECTED: "Seleccionar primera oportunidad beginner-friendly con alta probabilidad",
        FirstMoneyStage.ACTION_PREPARED: "Preparar: reporte, PR, gig, task. OWNEX genera borrador, tú revisas",
        FirstMoneyStage.HUMAN_APPROVED: "TÚ apruebas antes de cualquier acción externa irreversible",
        FirstMoneyStage.EXECUTED: "OWNEX ejecuta (submit report, PR, publish gig) o te da pasos exactos manuales",
        FirstMoneyStage.VERIFIED: "Confirmar: submitted/accepted/merged/published. Evidencia guardada",
        FirstMoneyStage.FIRST_REVENUE: "Dinero real en tu cuenta. Status = PAID. Celebrar 🎉",
        FirstMoneyStage.REVENUE_RECORDED: "Registrar en Revenue Ledger: amount, fees, net, time-to-payment, platform",
        FirstMoneyStage.ANALYZED: "Comparar: estimated vs actual. Time, revenue, difficulty. Aprender para la siguiente",
        FirstMoneyStage.NEXT_RECOMMENDED: "OWNEX recomienda la siguiente oportunidad basada en lo que funcionó",
    }

    def __init__(self, storage_path: Path | None = None, user_name: str = "Adriel"):
        self.storage_path = storage_path or Path.home() / ".ownex" / "first_money"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.user_name = user_name
        self.progress: FirstMoneyProgress | None = None
        self._load_progress()

    def _load_progress(self) -> None:
        progress_file = self.storage_path / "progress.json"
        if progress_file.exists():
            try:
                with open(progress_file) as f:
                    data = json.load(f)
                # Reconstruct progress
                self.progress = FirstMoneyProgress(
                    user_name=data.get("user_name", self.user_name),
                    current_stage=FirstMoneyStage(data.get("current_stage", FirstMoneyStage.PLATFORM_SELECTED.value)),
                    first_revenue_amount=data.get("first_revenue_amount", 0.0),
                    first_revenue_platform=data.get("first_revenue_platform"),
                    started_at=data.get("started_at", datetime.now(UTC).isoformat()),
                    completed_at=data.get("completed_at"),
                    notes=data.get("notes", []),
                )
                # Reconstruct stages
                for stage_key, stage_data in data.get("stages", {}).items():
                    self.progress.stages[stage_key] = StageProgress(
                        stage=FirstMoneyStage(stage_data["stage"]),
                        status=StageStatus(stage_data["status"]),
                        started_at=stage_data.get("started_at"),
                        completed_at=stage_data.get("completed_at"),
                        platform=stage_data.get("platform"),
                        metadata=stage_data.get("metadata", {}),
                        notes=stage_data.get("notes", ""),
                        blocking_reason=stage_data.get("blocking_reason"),
                    )
                logger.info(f"First Money progress loaded: {self.progress.current_stage}")
            except Exception as exc:
                logger.warning(f"Could not load First Money progress: {exc}")
                self._init_fresh()
        else:
            self._init_fresh()

    def _init_fresh(self) -> None:
        self.progress = FirstMoneyProgress(user_name=self.user_name)
        self._save_progress()

    def _save_progress(self) -> None:
        if not self.progress:
            return
        progress_file = self.storage_path / "progress.json"
        try:
            data = {
                "user_name": self.progress.user_name,
                "current_stage": self.progress.current_stage.value,
                "first_revenue_amount": self.progress.first_revenue_amount,
                "first_revenue_platform": self.progress.first_revenue_platform,
                "started_at": self.progress.started_at,
                "completed_at": self.progress.completed_at,
                "notes": self.progress.notes,
                "stages": {
                    k: {
                        "stage": v.stage.value,
                        "status": v.status.value,
                        "started_at": v.started_at,
                        "completed_at": v.completed_at,
                        "platform": v.platform,
                        "metadata": v.metadata,
                        "notes": v.notes,
                        "blocking_reason": v.blocking_reason,
                    }
                    for k, v in self.progress.stages.items()
                },
            }
            with open(progress_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as exc:
            logger.warning(f"Could not save First Money progress: {exc}")

    def start_stage(self, stage: FirstMoneyStage, platform: str | None = None, metadata: dict | None = None) -> bool:
        """Iniciar una etapa."""
        if not self.progress:
            return False
        stage_progress = self.progress.stages.get(stage.value)
        if not stage_progress:
            return False
        if stage_progress.status == StageStatus.COMPLETED:
            return True  # Ya completada
        stage_progress.status = StageStatus.IN_PROGRESS
        stage_progress.started_at = datetime.now(UTC).isoformat()
        stage_progress.platform = platform
        if metadata:
            stage_progress.metadata.update(metadata)
        self.progress.current_stage = stage
        self._save_progress()
        logger.info(f"First Money: started stage {stage.value}")
        return True

    def complete_stage(self, stage: FirstMoneyStage, notes: str = "", metadata: dict | None = None) -> bool:
        """Completar una etapa."""
        if not self.progress:
            return False
        stage_progress = self.progress.stages.get(stage.value)
        if not stage_progress:
            return False
        stage_progress.status = StageStatus.COMPLETED
        stage_progress.completed_at = datetime.now(UTC).isoformat()
        stage_progress.notes = notes
        if metadata:
            stage_progress.metadata.update(metadata)
        # Avanzar a siguiente etapa si es la actual
        if self.progress.current_stage == stage:
            self._advance_to_next()
        self._save_progress()
        logger.info(f"First Money: completed stage {stage.value}")
        return True

    def _advance_to_next(self) -> None:
        """Avanzar a la siguiente etapa no completada."""
        if not self.progress:
            return
        current_index = self.STAGE_ORDER.index(self.progress.current_stage)
        for i in range(current_index + 1, len(self.STAGE_ORDER)):
            next_stage = self.STAGE_ORDER[i]
            if self.progress.stages[next_stage.value].status != StageStatus.COMPLETED:
                self.progress.current_stage = next_stage
                break
        else:
            # Todas completadas
            self.progress.completed_at = datetime.now(UTC).isoformat()

    def block_stage(self, stage: FirstMoneyStage, reason: str) -> bool:
        """Bloquear una etapa con razón."""
        if not self.progress:
            return False
        stage_progress = self.progress.stages.get(stage.value)
        if not stage_progress:
            return False
        stage_progress.status = StageStatus.BLOCKED
        stage_progress.blocking_reason = reason
        self._save_progress()
        return True

    # ── Engine Proximity & Milestone Tracking ────────────────────────────

    def get_engine_proximity(self) -> list[EngineProximity]:
        """Calcular proximidad de cada motor al próximo hito de ingreso."""
        if not self.progress:
            return []

        total_earned = self.progress.first_revenue_amount
        # Próximo hito no alcanzado
        next_milestone = None
        for m in Milestone:
            if total_earned < m.usd:
                next_milestone = m
                break

        if not next_milestone:
            # Todos los hitos alcanzados
            next_milestone = Milestone.M10K

        # Datos de motores (en producción vendrían de trackers reales)
        engines_data = self._get_engines_status(total_earned)

        proximities = []
        for eng_data in engines_data:
            engine = eng_data["engine"]
            current = eng_data["current_usd"]
            projected = eng_data["projected_usd"]
            status = eng_data["status"]
            action = eng_data["next_action"]
            action_url = eng_data.get("action_url")
            confidence = eng_data.get("confidence", 0.5)

            usd_to_milestone_eng = max(0, next_milestone.usd - (total_earned + projected - current))
            pct_to_milestone = (1 - usd_to_milestone_eng / next_milestone.usd) * 100 if next_milestone.usd > 0 else 100

            prox = EngineProximity(
                engine=engine,
                label=engine.value.replace("_", " ").title(),
                current_usd=current,
                projected_usd=projected,
                next_milestone=next_milestone,
                usd_to_milestone=usd_to_milestone_eng,
                pct_to_milestone=round(pct_to_milestone, 1),
                engine_status=status,
                next_action=action,
                action_url=action_url,
                confidence=confidence,
            )
            proximities.append(prox)

        # Ordenar: más cercano al hito primero
        proximities.sort(key=lambda p: p.usd_to_milestone)
        return proximities

    def _get_engines_status(self, total_earned: float) -> list[dict]:
        """Obtener estado de cada motor (placeholder para integración real)."""
        if not self.progress:
            return []
        # Por ahora, heurísticas basadas en etapas completadas
        # AI Training: si PLATFORM_LEARNED o superior para Outlier/Outlier-type
        ai_ready = self.progress.stages.get(FirstMoneyStage.PLATFORM_LEARNED.value, None)
        ai_stage = ai_ready.status if ai_ready else StageStatus.NOT_STARTED

        # Bug Bounty: si PLATFORM_LEARNED y OPPORTUNITY_SELECTED
        opp_ready = self.progress.stages.get(FirstMoneyStage.OPPORTUNITY_SELECTED.value, None)

        # Dev Bounty: similar a bug bounty pero para plataformas dev
        dev_ready = self.progress.stages.get(FirstMoneyStage.OPPORTUNITY_SELECTED.value, None)

        return [
            {
                "engine": IncomeEngine.AI_TRAINING,
                "current_usd": 0.0,
                "projected_usd": 300.0 if ai_stage == StageStatus.COMPLETED else 50.0,
                "status": "ready"
                if ai_stage == StageStatus.COMPLETED
                else ("needs_setup" if ai_stage == StageStatus.IN_PROGRESS else "needs_action"),
                "next_action": "Completar onboarding en Outlier/Mindrift"
                if ai_stage != StageStatus.COMPLETED
                else "Revisar tareas disponibles hoy",
                "action_url": "/operations/platforms/outlier",
                "confidence": 0.7 if ai_stage == StageStatus.COMPLETED else 0.3,
            },
            {
                "engine": IncomeEngine.BUG_BOUNTY,
                "current_usd": 0.0,
                "projected_usd": 500.0,
                "status": "ready" if opp_ready and opp_ready.status == StageStatus.COMPLETED else "needs_setup",
                "next_action": "Seleccionar primer programa en HackerOne"
                if opp_ready and opp_ready.status != StageStatus.COMPLETED
                else "Enviar primer reporte",
                "action_url": "/operations/work-queue",
                "confidence": 0.4,
            },
            {
                "engine": IncomeEngine.DEV_BOUNTY,
                "current_usd": 0.0,
                "projected_usd": 400.0,
                "status": "ready" if dev_ready and dev_ready.status == StageStatus.COMPLETED else "needs_setup",
                "next_action": "Revisar issues en Opire/IssueHunt"
                if dev_ready and dev_ready.status != StageStatus.COMPLETED
                else "Enviar PR a bounty abierto",
                "action_url": "/operations/work-queue",
                "confidence": 0.5,
            },
        ]

    def get_milestone_tracker_data(self) -> dict[str, Any]:
        """Dashboard completo: hitos, motores, acción diaria."""
        if not self.progress:
            return {"error": "No progress"}

        total_earned = self.progress.first_revenue_amount

        # Próximo hito
        next_milestone = None
        for m in Milestone:
            if self.progress.first_revenue_amount < m.usd:
                next_milestone = m
                break
        if not next_milestone:
            next_milestone = Milestone.M10K

        usd_needed = next_milestone.usd - total_earned
        pct_complete = (total_earned / next_milestone.usd) * 100 if next_milestone.usd > 0 else 100

        # Proximidad de motores
        proximities = self.get_engine_proximity()

        # Hitos con progreso
        milestones = []
        for m in Milestone:
            usd_needed_m = max(0, m.usd - total_earned)
            pct = (total_earned / m.usd) * 100 if m.usd > 0 else 100
            engines_contrib = [e.engine.value for e in self.get_engine_proximity() if e.projected_usd > 0]
            milestones.append(
                {
                    "milestone": m.value,
                    "label": m.label,
                    "usd_target": m.usd,
                    "current_usd": min(total_earned, m.usd),
                    "usd_needed": usd_needed_m,
                    "pct_complete": round(min(pct, 100), 1),
                    "engines_contributing": engines_contrib,
                    "is_next": m == next_milestone,
                    "achieved": total_earned >= m.usd,
                }
            )

        # Motor más cercano al hito
        closest = (
            min(self.get_engine_proximity(), key=lambda p: p.usd_to_milestone) if self.get_engine_proximity() else None
        )

        # Acción diaria recomendada
        daily_action = self._get_daily_action()

        return {
            "total_earned_usd": total_earned,
            "next_milestone": {
                "milestone": next_milestone.value,
                "label": next_milestone.label,
                "usd_needed": usd_needed,
                "pct_complete": round(pct_complete, 1),
            },
            "milestones": milestones,
            "engine_proximities": [
                {
                    "engine": p.engine.value,
                    "label": p.label,
                    "current_usd": p.current_usd,
                    "projected_usd": p.projected_usd,
                    "next_milestone": p.next_milestone.value,
                    "usd_to_milestone": p.usd_to_milestone,
                    "pct_to_milestone": p.pct_to_milestone,
                    "status": p.engine_status,
                    "next_action": p.next_action,
                    "action_url": p.action_url,
                    "confidence": p.confidence,
                    "is_closest": p.is_closest,
                }
                for p in proximities
            ],
            "closest_engine": {
                "engine": closest.engine.value,
                "label": closest.label,
                "usd_to_milestone": closest.usd_to_milestone,
                "next_action": closest.next_action,
                "action_url": closest.action_url,
            }
            if closest
            else None,
            "daily_action": daily_action,
        }

    def _get_daily_action(self) -> DailyAction | None:
        """Acción concreta recomendada para hoy."""
        if not self.progress:
            return None

        proximities = self.get_engine_proximity()
        if not proximities:
            return None

        # Priorizar el motor más cercano al hito que esté "ready" o "needs_action"
        for p in proximities:
            if p.engine_status in ("ready", "needs_action"):
                return DailyAction(
                    engine=p.engine,
                    title=p.next_action,
                    description=f"Acercar ${p.usd_to_milestone:,.0f} al hito ${p.next_milestone.label}",
                    estimated_minutes=30,
                    impact_usd=p.projected_usd,
                    priority=1,
                    url=p.action_url,
                )

        # Fallback: primer motor que necesite setup
        for p in proximities:
            if p.engine_status == "needs_setup":
                return DailyAction(
                    engine=p.engine,
                    title=p.next_action,
                    description=f"Configurar {p.label} para desbloquear ingresos",
                    estimated_minutes=45,
                    impact_usd=p.projected_usd,
                    priority=2,
                    url=p.action_url,
                )

        return DailyAction(
            engine=IncomeEngine.AI_TRAINING,
            title="Revisar plataformas de AI training",
            description="Verificar tareas disponibles en Outlier/Mindrift",
            estimated_minutes=15,
            impact_usd=50.0,
            priority=3,
            url="/operations/platforms",
        )

    # ── Aggressive Mode (EOY Targets: $5k / $10k by Dec 31) ────────────

    def get_aggressive_plan(self, target_usd: int = 5000) -> dict[str, Any]:
        """Plan agresivo para llegar a $target_usd antes de fin de año.

        Calcula output semanal requerido por motor para cerrar la brecha.
        """
        if not self.progress:
            return {"error": "No progress"}

        total_earned = self.progress.first_revenue_amount
        gap = max(0, target_usd - total_earned)

        # Semanas restantes hasta fin de año (aprox)
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        # Semanas restantes hasta fin de año (semana actual a semana 52)
        current_week = now.isocalendar()[1]
        weeks_left = max(1, 52 - current_week + 1)  # ej: semana 37 → 16 semanas restantes

        if weeks_left <= 0:
            return {"error": "No time left", "gap_usd": gap}

        # USD semanal requerido para cerrar la brecha
        weekly_required = gap / weeks_left

        # Distribución por motor basada en projected_usd y status
        proximities = self.get_engine_proximity()
        ready_engines = [p for p in proximities if p.engine_status in ("ready", "needs_action")]
        setup_engines = [p for p in proximities if p.engine_status == "needs_setup"]

        # Distribuir carga: motores ready llevan 70%, setup 30% (se activan en 2-3 semanas)
        weekly_ready = weekly_required * 0.7
        weekly_setup = weekly_required * 0.3

        engine_plan = []

        for p in ready_engines:
            share = p.projected_usd / sum(e.projected_usd for e in ready_engines) if ready_engines else 1
            weekly_target = weekly_ready * share
            # Estimar horas basado en rate efectivo por motor: AI=$30/h, Bug=$40/h, Dev=$35/h
            rate_map = {
                IncomeEngine.AI_TRAINING: 30.0,
                IncomeEngine.BUG_BOUNTY: 40.0,
                IncomeEngine.DEV_BOUNTY: 35.0,
            }
            rate = rate_map.get(p.engine, 30.0)
            hours_needed = weekly_target / rate

            engine_plan.append(
                {
                    "engine": p.engine.value,
                    "label": p.label,
                    "status": p.engine_status,
                    "weekly_usd_target": round(weekly_target, 2),
                    "monthly_usd_target": round(weekly_target * 4.33, 2),
                    "est_hours_per_week": round(hours_needed, 1),
                    "current_projected_monthly": p.projected_usd,
                    "gap_to_monthly_target": round(max(0, (weekly_target * 4.33) - p.projected_usd), 2),
                    "confidence": p.confidence,
                    "is_primary": p.is_closest,
                }
            )

        for p in setup_engines:
            # Motores en setup: activación en 2-3 semanas, luego ramp-up
            engine_plan.append(
                {
                    "engine": p.engine.value,
                    "label": p.label,
                    "status": p.engine_status,
                    "weekly_usd_target": round(weekly_setup / len(setup_engines), 2) if setup_engines else 0,
                    "monthly_usd_target": round((weekly_setup / len(setup_engines)) * 4.33, 2) if setup_engines else 0,
                    "est_hours_per_week": 5,  # tiempo de setup/onboarding
                    "current_projected_monthly": p.projected_usd,
                    "gap_to_monthly_target": round(p.projected_usd * 0.5, 2),  # 50% ramp-up
                    "confidence": p.confidence,
                    "is_primary": False,
                    "setup_phase": True,
                    "setup_actions": p.next_action,
                }
            )

        # Ordenar: primary first, luego por weekly_usd_target desc
        engine_plan.sort(key=lambda x: (not x.get("is_primary", False), -x["weekly_usd_target"]))

        # Weekly checklist accionable
        weekly_checklist = []
        for ep in engine_plan:
            if ep.get("setup_phase"):
                weekly_checklist.append(f"[SETUP] {ep['label']}: {ep['setup_actions']} (~{ep['est_hours_per_week']}h)")
            else:
                weekly_checklist.append(
                    f"[PROD] {ep['label']}: ${ep['weekly_usd_target']:.0f}/sem ({ep['est_hours_per_week']:.1f}h) → ${ep['monthly_usd_target']:.0f}/mes"
                )

        return {
            "target_usd": target_usd,
            "current_earned": self.progress.first_revenue_amount,
            "gap_usd": gap,
            "weeks_left": weeks_left,
            "weekly_required_total": round(weekly_required, 2),
            "monthly_required_total": round(weekly_required * 4.33, 2),
            "engine_plan": engine_plan,
            "weekly_checklist": weekly_checklist,
            "milestones_remaining": [
                {"label": m.label, "usd": m.usd, "achieved": self.progress.first_revenue_amount >= m.usd}
                for m in Milestone
                if m.usd <= target_usd
            ],
            "probability_note": self._estimate_probability(target_usd, weeks_left, weekly_required),
        }

    def _estimate_probability(self, target_usd: int, weeks_left: int, weekly_required: float) -> str:
        """Estimación honesta de probabilidad basada en requerimiento semanal."""
        # Heurística: <$200/sem = alta, $200-400 = media, >$400 = baja
        if weekly_required < 200:
            return f"ALTA: ${weekly_required:.0f}/sem es alcanzable con 2 motores activos"
        elif weekly_required < 400:
            return f"MEDIA: ${weekly_required:.0f}/sem requiere 3 motores a full + 1 ramping"
        else:
            return f"BAJA: ${weekly_required:.0f}/sem requiere todo a full capacity + suerte en bug bounty"

    def get_dashboard_data(self) -> dict[str, Any]:
        """Datos para UI dashboard."""
        if not self.progress:
            return {"error": "No progress"}

        completed_count = sum(1 for s in self.progress.stages.values() if s.status == StageStatus.COMPLETED)
        total_count = len(self.STAGE_ORDER)
        pct = (completed_count / total_count) * 100 if total_count else 0

        stages_ui = []
        for stage in self.STAGE_ORDER:
            sp = self.progress.stages[stage.value]
            stages_ui.append(
                {
                    "stage": stage.value,
                    "label": self.STAGE_LABELS[stage],
                    "description": self.STAGE_DESCRIPTIONS[stage],
                    "status": sp.status.value,
                    "started_at": sp.started_at,
                    "completed_at": sp.completed_at,
                    "platform": sp.platform,
                    "is_current": sp.stage == self.progress.current_stage,
                    "blocking_reason": sp.blocking_reason,
                }
            )

        return {
            "user_name": self.progress.user_name,
            "current_stage": self.progress.current_stage.value,
            "current_stage_label": self.STAGE_LABELS[self.progress.current_stage],
            "completion_percentage": round(pct, 1),
            "completed_count": completed_count,
            "total_count": total_count,
            "first_revenue_amount": self.progress.first_revenue_amount,
            "first_revenue_platform": self.progress.first_revenue_platform,
            "started_at": self.progress.started_at,
            "completed_at": self.progress.completed_at,
            "stages": stages_ui,
            "is_complete": self.progress.completed_at is not None,
        }

    def record_first_revenue(self, amount: float, platform: str, notes: str = "") -> bool:
        """Registrar el primer ingreso real."""
        if not self.progress:
            return False
        self.progress.first_revenue_amount = amount
        self.progress.first_revenue_platform = platform
        self.complete_stage(
            FirstMoneyStage.FIRST_REVENUE, notes=notes, metadata={"amount": amount, "platform": platform}
        )
        self.complete_stage(
            FirstMoneyStage.REVENUE_RECORDED, notes="Registrado en Revenue Ledger", metadata={"amount": amount}
        )
        return True

    def record_analysis(self, estimated_vs_actual: dict[str, Any], notes: str = "") -> bool:
        """Registrar análisis post-earning."""
        if not self.progress:
            return False
        self.complete_stage(FirstMoneyStage.ANALYZED, notes=notes, metadata=estimated_vs_actual)
        return True

    def recommend_next(self, recommendation: dict[str, Any]) -> bool:
        """Registrar próxima recomendación."""
        if not self.progress:
            return False
        self.complete_stage(
            FirstMoneyStage.NEXT_RECOMMENDED, notes="Next opportunity recommended", metadata=recommendation
        )
        # Reset para siguiente ciclo (mantener revenue history)
        self._reset_for_next_cycle()
        return True

    def _reset_for_next_cycle(self) -> None:
        """Resetear etapas operativas para el siguiente ciclo, mantener revenue history."""
        if not self.progress:
            return
        # Mantener completadas: PLATFORM_SELECTED through REVENUE_RECORDED
        # Resetear: ANALYZED, NEXT_RECOMMENDED, y etapas operativas específicas de la oportunidad
        operational_stages = [
            FirstMoneyStage.OPPORTUNITY_SELECTED,
            FirstMoneyStage.ACTION_PREPARED,
            FirstMoneyStage.HUMAN_APPROVED,
            FirstMoneyStage.EXECUTED,
            FirstMoneyStage.VERIFIED,
            FirstMoneyStage.ANALYZED,
            FirstMoneyStage.NEXT_RECOMMENDED,
        ]
        for stage in operational_stages:
            self.progress.stages[stage.value] = StageProgress(stage=stage)
        # Volver a oportunidad seleccionada como current
        self.progress.current_stage = FirstMoneyStage.OPPORTUNITY_SELECTED
        self._save_progress()

    def get_next_action(self) -> dict[str, Any] | None:
        """Obtener la siguiente acción recomendada basada en etapa actual."""
        if not self.progress:
            return None

        current = self.progress.current_stage
        platform = self.progress.stages[current.value].platform

        actions = {
            FirstMoneyStage.PLATFORM_SELECTED: {
                "action": "select_platform",
                "title": "Elegir primera plataforma",
                "description": "Recomendado: HackerOne (bug bounty), Fiverr (servicios), Outlier (AI training)",
                "platform": None,
            },
            FirstMoneyStage.ACCOUNT_CREATED: {
                "action": "create_account",
                "title": "Crear cuenta en la plataforma",
                "description": f"Registrarse en {platform or 'la plataforma elegida'} con email real",
                "platform": platform,
            },
            FirstMoneyStage.PROFILE_COMPLETED: {
                "action": "complete_profile",
                "title": "Completar perfil",
                "description": "Bio, skills, foto, 2FA habilitado",
                "platform": platform,
            },
            FirstMoneyStage.PAYMENT_CONFIGURED: {
                "action": "configure_payment",
                "title": "Configurar método de cobro",
                "description": f"Payoneer/PayPal/Wise/Stripe en {platform}. Sin esto no cobras",
                "platform": platform,
            },
            FirstMoneyStage.PLATFORM_LEARNED: {
                "action": "learn_platform",
                "title": "Aprender la plataforma",
                "description": f"Leer guía, ver UI, entender scope/rules/submission flow de {platform}",
                "platform": platform,
            },
            FirstMoneyStage.OPPORTUNITY_SELECTED: {
                "action": "select_opportunity",
                "title": "Seleccionar primera oportunidad",
                "description": "Beginner-friendly, alta probabilidad, scope claro",
                "platform": platform,
            },
            FirstMoneyStage.ACTION_PREPARED: {
                "action": "prepare_action",
                "title": "Preparar acción",
                "description": "OWNEX genera borrador (reporte/PR/gig/task). Tú revisas",
                "platform": platform,
            },
            FirstMoneyStage.HUMAN_APPROVED: {
                "action": "human_approve",
                "title": "Aprobar ejecución",
                "description": "Revisar qué se va a enviar. Solo TÚ autorizas acciones externas",
                "platform": platform,
            },
            FirstMoneyStage.EXECUTED: {
                "action": "execute",
                "title": "Ejecutar",
                "description": "OWNEX envía (submit/PR/publish) o te da pasos manuales exactos",
                "platform": platform,
            },
            FirstMoneyStage.VERIFIED: {
                "action": "verify",
                "title": "Verificar resultado",
                "description": "Confirmar: submitted/accepted/merged. Guardar evidencia",
                "platform": platform,
            },
            FirstMoneyStage.FIRST_REVENUE: {
                "action": "first_revenue",
                "title": "¡Primer ingreso!",
                "description": "Dinero real en tu cuenta. Status = PAID",
                "platform": platform,
            },
            FirstMoneyStage.REVENUE_RECORDED: {
                "action": "record_revenue",
                "title": "Registrar en Ledger",
                "description": "Amount, fees, net, time-to-payment, platform. Truth only",
                "platform": platform,
            },
            FirstMoneyStage.ANALYZED: {
                "action": "analyze",
                "title": "Analizar",
                "description": "Estimated vs actual: time, revenue, difficulty. Aprender",
                "platform": platform,
            },
            FirstMoneyStage.NEXT_RECOMMENDED: {
                "action": "next_opportunity",
                "title": "Siguiente oportunidad",
                "description": "OWNEX recomienda basada en lo que funcionó",
                "platform": platform,
            },
        }
        return actions.get(current)


# Singleton
_first_money_tracker: FirstMoneyTracker | None = None


def get_first_money_tracker(user_name: str = "Adriel") -> FirstMoneyTracker:
    """Obtener instancia singleton del First Money Tracker."""
    global _first_money_tracker
    if _first_money_tracker is None:
        _first_money_tracker = FirstMoneyTracker(user_name=user_name)
    return _first_money_tracker


def reset_first_money_tracker() -> None:
    """Resetear el singleton (el próximo get crea estado fresco)."""
    global _first_money_tracker
    _first_money_tracker = None
