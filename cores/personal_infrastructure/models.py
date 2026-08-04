"""Personal Infrastructure Manager - Data Models.

Modelos de datos para gestionar objetivos, integraciones, progreso y aprobaciones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ObjectiveCategory(StrEnum):
    """Categorías de objetivos del usuario."""

    DEVELOPMENT = "development"
    BUG_BOUNTY = "bug_bounty"
    DEV_BOUNTY = "dev_bounty"
    FREELANCE = "freelance"
    WEALTH = "wealth"
    PRODUCTIVITY = "productivity"
    SECURITY = "security"
    BACKUP = "backup"


class IntegrationHealth(StrEnum):
    """Estado de salud de una integración."""

    CONNECTED = "connected"
    PENDING_AUTH = "pending_auth"
    NOT_CONFIGURED = "not_configured"
    ERROR = "error"
    DEPRECATED = "deprecated"


class ApprovalCategory(StrEnum):
    """Categorías de aprobación para acciones sensibles."""

    AUTO = "auto"  # Puede hacerlo solo (organizar archivos, actualizar docs, tests)
    CONFIRM = "confirm"  # Pregunta antes (enviar emails, conectar servicios)
    MANUAL = "manual"  # Nunca automático (movimientos financieros, inversiones, pagos)


@dataclass
class LearningExplanation:
    """Explicación educativa para una acción o concepto."""

    title: str
    what_is: str  # "Qué es"
    what_for: str  # "Para qué sirve"
    what_changes: str  # "Qué cambia"
    what_risk: str  # "Qué riesgo existe"
    what_if_not: str  # "Qué pasa si no lo hago"
    simple_version: str  # "Versión simplificada (ej: OAuth sin contraseña)"


@dataclass
class AccountIntegration:
    """Representa una cuenta o servicio integrado."""

    integration_id: str
    name: str
    category: ObjectiveCategory
    purpose: str  # "Esta cuenta permite recibir oportunidades"
    permissions: list[str]  # Lista de permisos requeridos
    last_sync: datetime | None = None
    health: IntegrationHealth = IntegrationHealth.NOT_CONFIGURED
    risks: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    explanation: LearningExplanation | None = None
    connection_type: str = "oauth"  # oauth, api_key, export_file, manual


@dataclass
class ObjectiveDefinition:
    """Definición de un objetivo del usuario."""

    objective_id: str
    category: ObjectiveCategory
    title: str
    description: str
    required_integrations: list[AccountIntegration]
    explanation: LearningExplanation
    estimated_duration_hours: int = 0
    dependencies: list[str] = field(default_factory=list)  # IDs de objetivos previos
    approval_required: bool = False


@dataclass
class ObjectiveProgress:
    """Progreso de un objetivo del usuario."""

    objective_id: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    completion_percentage: float = 0.0
    completed_tasks: list[str] = field(default_factory=list)
    pending_tasks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    current_step: str = ""


@dataclass
class AdministrativeStep:
    """Paso de un trámite administrativo."""

    step_id: str
    title: str
    description: str
    why_do_it: str  # "Por qué hacerlo"
    when_do_it: str  # "Cuándo hacerlo"
    documents_needed: list[str]
    errors_to_avoid: list[str]
    status: str = "pending"  # pending, in_progress, completed, skipped
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convertir a dict."""
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "why_do_it": self.why_do_it,
            "when_do_it": self.when_do_it,
            "documents_needed": self.documents_needed,
            "errors_to_avoid": self.errors_to_avoid,
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class AdministrativeProcess:
    """Proceso administrativo completo (ej: configurar pagos internacionales)."""

    process_id: str
    title: str
    objective: str  # "Recibir pagos internacionales"
    steps: list[AdministrativeStep]
    current_step_index: int = 0
    status: str = "pending"  # pending, in_progress, completed
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class WealthAccount:
    """Cuenta financiera (sin datos sensibles)."""

    account_id: str
    name: str
    type: str  # bank, crypto, paypal, wise, etc.
    purpose: str  # "Recibir pagos de Dev Bounty"
    connection_method: str  # oauth, api, export
    status: str = "not_configured"
    last_sync: datetime | None = None
    # Nunca almacenar: contraseñas, claves privadas, credenciales sensibles


@dataclass
class InfrastructureSnapshot:
    """Snapshot completo de la infraestructura personal."""

    objectives_progress: dict[str, ObjectiveProgress]
    integrations: dict[str, AccountIntegration]
    administrative_processes: dict[str, AdministrativeProcess]
    wealth_accounts: dict[str, WealthAccount]
    overall_completion: float = 0.0
    next_recommended_action: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
