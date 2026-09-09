"""First Money Workflow Tracker — Zero-to-Earning Pipeline.

Tracks the owner's progress from $0 through first earning:
Platform → Account → Profile → Payment → Opportunity → Prepare → Approve → Execute → Verify → Earn → Record

Each stage is a milestone. The system guides, tracks, and learns.
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
