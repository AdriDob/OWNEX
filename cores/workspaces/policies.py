"""Workspace income policies — SSOT for which workspaces may carry income goals.

Rules (owner-decided, documented so the economic orchestrator never invents):
- TRADING is CAPITAL only, never base income; PAPER by default, explicit human arm.
- BACKUP_INCOME (in-person CABA/Zona Sur) is a LAST-RESORT safety net:
  reported separately, never auto-ranked as upside.
- OWNEX core is maintenance, not income.
- Everything else with an active context may join the income mix.

Pure functions over WorkspaceType — no DB, no side effects, never raises.
"""

from __future__ import annotations

from enum import StrEnum

from cores.workspaces.registry import WorkspaceType


class IncomeRole(StrEnum):
    """What a workspace may be in the monthly income plan."""

    PRIMARY = "primary"  # base income engines (bug/dev/ai)
    UPSIDE = "upside"  # optional commercial engines, only if ACTIVE
    CORE = "core"  # maintenance, never income
    CAPITAL_ONLY = "capital_only"  # trading: capital, PAPER default
    LAST_RESORT = "last_resort"  # backup_income: safety net, explicit only


_INCOME_ROLES: dict[WorkspaceType, IncomeRole] = {
    WorkspaceType.BUG_BOUNTY: IncomeRole.PRIMARY,
    WorkspaceType.DEV_BOUNTY: IncomeRole.PRIMARY,
    WorkspaceType.AI_TRAINING: IncomeRole.PRIMARY,
    WorkspaceType.DROPPINGLABEL: IncomeRole.UPSIDE,
    WorkspaceType.MERCADO_LIBRE: IncomeRole.UPSIDE,
    WorkspaceType.ADRIEL_WEBS: IncomeRole.UPSIDE,
    WorkspaceType.CONTENT_FACTORY: IncomeRole.UPSIDE,
    WorkspaceType.OWNEX: IncomeRole.CORE,
    WorkspaceType.TRADING: IncomeRole.CAPITAL_ONLY,
    WorkspaceType.BACKUP_INCOME: IncomeRole.LAST_RESORT,
}

_ROLE_EXPLANATION: dict[IncomeRole, str] = {
    IncomeRole.PRIMARY: "Motor de renta base: participa siempre del mix de ingresos.",
    IncomeRole.UPSIDE: "Comercial opcional: solo si está ACTIVE, nunca por defecto.",
    IncomeRole.CORE: "Mantenimiento: no genera ingresos, no entra al mix.",
    IncomeRole.CAPITAL_ONLY: "Solo capital (PAPER default, armado humano explícito): jamás renta base.",
    IncomeRole.LAST_RESORT: "Red de seguridad presencial: se reporta aparte, nunca como upside.",
}


def income_role(workspace_type: WorkspaceType) -> IncomeRole:
    """Income role for a workspace type. Unknown future types default to UPSIDE (opt-in)."""
    return _INCOME_ROLES.get(workspace_type, IncomeRole.UPSIDE)


def allowed_in_income_mix(
    workspace_type: WorkspaceType,
    *,
    active: bool = True,
    include_optional: bool = False,
    allow_last_resort: bool = False,
) -> bool:
    """Whether a workspace may join the monthly income mix.

    - PRIMARY: yes when active.
    - UPSIDE: only when active AND explicitly included.
    - CORE / CAPITAL_ONLY: never.
    - LAST_RESORT: only with explicit allow_last_resort (human asked for it).
    """
    role = income_role(workspace_type)
    if role == IncomeRole.PRIMARY:
        return active
    if role == IncomeRole.UPSIDE:
        return active and include_optional
    if role == IncomeRole.LAST_RESORT:
        return allow_last_resort
    return False


def rank_for_mission(
    workspace_types: list[WorkspaceType],
    *,
    priorities: dict[WorkspaceType, int] | None = None,
    include_optional: bool = False,
    allow_last_resort: bool = False,
) -> list[WorkspaceType]:
    """Order workspace types for mission allocation (highest priority first).

    Only income-eligible workspaces survive; ties keep input order (stable).
    """
    eligible = [
        w
        for w in workspace_types
        if allowed_in_income_mix(w, include_optional=include_optional, allow_last_resort=allow_last_resort)
    ]
    prio = priorities or {}
    return sorted(eligible, key=lambda w: prio.get(w, 5), reverse=True)


def explain(workspace_type: WorkspaceType) -> str:
    """Human-readable policy reason for a workspace (for UI/API)."""
    return _ROLE_EXPLANATION[income_role(workspace_type)]
