"""OWNEX Agent Runtime — capa de ejecución con agentes externos (G-fase).

Decisión owner 2026-08-26: NO construir agentes caseros desde cero.
Registrar integraciones open-source como EXECUTORS del runtime:

    Browser Use  → websites          (github.com/browser-use/browser-use)
    UI-TARS      → desktop apps      (github.com/bytedance/UI-TARS-desktop)
    OpenHands    → coding/software   (github.com/All-Hands-AI/OpenHands)

El cerebro sigue siendo OWNEX (OAR + Opportunity Engine + Work Queue +
Capital + Learning). Los agentes externos son MANOS, no cabeza.

Regla de autonomía (no negociable):
    dinero / credenciales / identidad / publicación / acciones irreversibles
    → SIEMPRE Human Gate (ExecutionMirror WAITING_HUMAN).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum


class AutonomyLevel(IntEnum):
    L0_RECOMMEND_ONLY = 0  # solo sugiere
    L1_REVERSIBLE = 1  # ejecuta tareas reversibles
    L2_WITH_APPROVAL = 2  # ejecuta con aprobación humana previa
    L3_SANDBOX = 3  # autónomo dentro de sandbox
    L4_LIMITED_MONEY = 4  # autónomo limitado con dinero externo


class AgentKind(StrEnum):
    BROWSER = "browser"  # Browser Use → websites
    DESKTOP = "desktop"  # UI-TARS → aplicaciones/escritorio
    CODE = "code"  # OpenHands → software/coding


# Acciones que SIEMPRE requieren gate humano, sin importar el nivel.
ALWAYS_HUMAN_GATE = frozenset(
    {
        "payment",
        "withdrawal",
        "purchase",
        "credential_change",
        "identity_change",
        "publication",
        "contractual_acceptance",
        "irreversible_external_action",
        "kyc",
    }
)


@dataclass(frozen=True)
class ExternalAgent:
    """Agente externo registrado como executor del runtime."""

    agent_id: str
    kind: AgentKind
    upstream_repo: str
    autonomy_default: AutonomyLevel
    surfaces: tuple[str, ...]  # qué controla
    integration_status: str = "pending"  # pending | wired | verified
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "kind": self.kind.value,
            "upstream_repo": self.upstream_repo,
            "autonomy_default": int(self.autonomy_default),
            "autonomy_name": self.autonomy_default.name,
            "surfaces": list(self.surfaces),
            "integration_status": self.integration_status,
            "notes": self.notes,
        }


REGISTRY: tuple[ExternalAgent, ...] = (
    ExternalAgent(
        agent_id="browser_use",
        kind=AgentKind.BROWSER,
        upstream_repo="https://github.com/browser-use/browser-use",
        autonomy_default=AutonomyLevel.L2_WITH_APPROVAL,
        surfaces=("websites", "forms", "assessments", "submissions"),
        integration_status="pending",
        notes="Prioritario: intermediario de plataformas (ghost operator).",
    ),
    ExternalAgent(
        agent_id="ui_tars_desktop",
        kind=AgentKind.DESKTOP,
        upstream_repo="https://github.com/bytedance/UI-TARS-desktop",
        autonomy_default=AutonomyLevel.L1_REVERSIBLE,
        surfaces=("desktop_apps", "screenshots", "mouse_keyboard"),
        integration_status="pending",
        notes="Capa de ejecución visual multimodal; Apache-2.0.",
    ),
    ExternalAgent(
        agent_id="openhands_code",
        kind=AgentKind.CODE,
        upstream_repo="https://github.com/All-Hands-AI/OpenHands",
        autonomy_default=AutonomyLevel.L3_SANDBOX,
        surfaces=("terminal", "repo_edits", "tests", "pr_drafts"),
        integration_status="pending",
        notes="Worker de software; MIT; PR siempre vía HUMAN GATE.",
    ),
)


def get_registry() -> list[dict]:
    return [a.as_dict() for a in REGISTRY]


def resolve_executor(kind: AgentKind) -> ExternalAgent | None:
    for a in REGISTRY:
        if a.kind == kind:
            return a
    return None


def required_gate_for(action: str, level: AutonomyLevel) -> str:
    """Política de gates: devuelve 'human' | 'auto' según acción y nivel.

    Las acciones de ALWAYS_HUMAN_GATE exigen humano en TODOS los niveles —
    coincide con ExecutionMirror WAITING_HUMAN y la regla §4 del charter.
    """
    if action in ALWAYS_HUMAN_GATE:
        return "human"
    return "auto" if int(level) >= AutonomyLevel.L3_SANDBOX else "human"


@dataclass(frozen=True)
class BotRole:
    """Roles del enjambre (estilo Rakazo, sin duplicar arquitectura)."""

    role_id: str
    name: str
    mission: str
    uses_agents: tuple[AgentKind, ...] = field(default_factory=tuple)


BOT_ROLES: tuple[BotRole, ...] = (
    BotRole("scout", "Scout", "Busca oportunidades nuevas", ()),
    BotRole("analyst", "Analyst", "Calcula ROI/dificultad/probabilidad", ()),
    BotRole("applicant", "Applicant", "Prepara/aplica cuando está permitido", (AgentKind.BROWSER,)),
    BotRole("worker", "Worker", "Ejecuta la tarea", (AgentKind.BROWSER, AgentKind.DESKTOP, AgentKind.CODE)),
    BotRole("verifier", "Verifier", "Comprueba que quedó terminada", (AgentKind.BROWSER,)),
    BotRole("finance", "Finance", "Registra ingreso/fees/reservas/capital", ()),
    BotRole("researcher", "Researcher", "Descubre categorías y plataformas nuevas", ()),
)


def get_bot_roles() -> list[dict]:
    return [
        {"role_id": b.role_id, "name": b.name, "mission": b.mission, "agents": [k.value for k in b.uses_agents]}
        for b in BOT_ROLES
    ]
