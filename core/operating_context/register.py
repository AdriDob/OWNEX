"""OWNEX Operating Context — register of executable policies.

This module exposes the Operating Context as VERIFIABLE POLICIES that the
PolicyEngine can enforce. It is NOT a second policy engine: it reuses
``core.copilot.permissions.PolicyEngine`` but adds the operational layer
(opportunity eligibility, evidence expiry, human gates, financial gates).

Rules:
- Never duplicate the existing PolicyEngine. Reuse it.
- Every policy carries a source reference (doc section, registry entry).
- Every policy can be refused by the evidence or by the evidence expiry.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from core.copilot.permissions import AuthorityLevel, Policy, PolicyEngine

logger = logging.getLogger("orion.core.operating_context")

# ── Context state ────────────────────────────────────────────────────────────

class ContextStatus(StrEnum):
    """How the Operating Context itself is considered valid."""

    LOADED = "loaded"
    VALIDATED = "validated"
    STALE = "stale"
    BLOCKED = "blocked"


class ContextQuality(StrEnum):
    """Evidence quality classification (per the Operating Context)."""

    VERIFIED = "verified"
    REPORTED = "reported"
    HYPOTHESIS = "hypothesis"
    UNVERIFIED = "unverified"
    STALE = "stale"
    BLOCKED = "blocked"
    PAID_VERIFIED = "paid_verified"


class OpportunityState(StrEnum):
    """Canonical opportunity state defined in the Operating Context."""

    DISCOVERED = "discovered"
    ELIGIBILITY_VERIFIED = "eligibility_verified"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EARNED = "earned"
    PAID = "paid"
    WITHDRAWN = "withdrawn"


# ── The Operating Context policy group ──────────────────────────────────────

class OperatingContextPolicies:
    """Bundle of policies that constrain the operating context behavior."""

    def __init__(self, engine: PolicyEngine) -> None:
        self.engine = engine
        self._register()

    def _register(self) -> None:
        self.engine.add(
            Policy(
                name="opcontext:deny_default",
                description=(
                    "Denegación por defecto: si una acción no está explícitamente "
                    "permitida en el Operating Context v1.0 → BLOQUEADA. "
                    "El contexto puede ampliar reglas, nunca eliminarlas."
                ),
                level=AuthorityLevel.OPERATOR,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:paid_only_with_evidence",
                description=(
                    "PAID solo con evidencia (tx hash, Stripe confirmation, o "
                    "cambio de estado en la plataforma). Merge ≠ Paid. "
                    "Source: REGLA 2 — MI MANDATO"
                ),
                level=AuthorityLevel.SENIOR_HUNTER,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:no_simulation",
                description=(
                    "No simular nada. No inventar payouts, no declarar PAID sin "
                    "confirmación, no confundir GMV de plataforma con ingreso propio. "
                    "Source: REGLA 4 — MI MANDATO"
                ),
                level=AuthorityLevel.SENIOR_HUNTER,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:limit_submissions_per_day",
                description=(
                    "No más de 5 submissions/día. No más de 1 security report/semana. "
                    "Source: REGLA 5 — MI MANDATO"
                ),
                level=AuthorityLevel.OPERATOR,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:human_gate_irreversible",
                description=(
                    "Acciones irreversibles (submit, publish, withdraw, spend >$5) "
                    "→ SIEMPRE aprobación humana. "
                    "Source: REGLA 6 — MI MANDATO"
                ),
                level=AuthorityLevel.SENIOR_HUNTER,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:never_delete_history",
                description=(
                    "No borrar tareas REJECTED/EXPIRED/CANCELLED del historial. "
                    "Source: REGLA 7 — MI MANDATO"
                ),
                level=AuthorityLevel.ADMINISTRATOR,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:adapter_exception_not_success",
                description=(
                    "Si un adaptador lanza excepción → NO interpretar como éxito. "
                    "Source: REGLA 8 — MI MANDATO"
                ),
                level=AuthorityLevel.OPERATOR,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:ambiguous_response_pending",
                description=(
                    "Si la respuesta de la plataforma es ambigua → PENDING, no "
                    "DELIVERED. "
                    "Source: REGLA 9 — MI MANDATO"
                ),
                level=AuthorityLevel.ASSISTANT,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:no_compete_early_bounty",
                description=(
                    "No competir por bounties < 2h de antigüedad (8-158 PRs llegan "
                    "en las primeras horas). "
                    "Source: REGLA 10 — MI MANDATO"
                ),
                level=AuthorityLevel.ASSISTANT,
            )
        )

        # ── Políticas operativas de la fuente ─────────────────────────────

        self.engine.add(
            Policy(
                name="opcontext:limit_lilly_prs",
                description=(
                    "Máx 2 PRs simultáneos en Lilly-Protocol. "
                    "Source: Operating Context §1"
                ),
                level=AuthorityLevel.OPERATOR,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:limit_huntr_reports",
                description=(
                    "Máx 1 report/semana en huntr. "
                    "Source: Operating Context §2"
                ),
                level=AuthorityLevel.SENIOR_HUNTER,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:no_pause_sources",
                description=(
                    "No usar AgentHansa para claimar, no usar Superteam para "
                    "claimar sin aprobación, y no usar fuentes en PAUSA hasta "
                    "haber identificado demanda. "
                    "Source: Operating Context §3-§5"
                ),
                level=AuthorityLevel.OPERATOR,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:block_broken_sources",
                description=(
                    "No usar fuentes en PAUSA (MCP Marketplace/MCPize, Gravity, "
                    "Apify, Forecast-bot) hasta que se identifique demanda. "
                    "Source: Operating Context §4"
                ),
                level=AuthorityLevel.ADMINISTRATOR,
            )
        )
        self.engine.add(
            Policy(
                name="opcontext:budget_never_guaranteed",
                description=(
                    "Piso es $0. No hay ingreso garantizado. No presupuestar nada "
                    "como seguro. "
                    "Source: REGLA 1 — MI MANDATO"
                ),
                level=AuthorityLevel.SENIOR_HUNTER,
            )
        )

        # ── Ventana temprana de bounties ────────────────────────────────

        self.engine.add(
            Policy(
                name="opcontext:no_early_submit",
                description=(
                    "No iniciar trabajo sustancial en un bounty que tiene menos de "
                    "2 horas de antigüedad (8-158 PRs llegan en ese tiempo). "
                    "Source: REGLA 10 — MI MANDATO"
                ),
                level=AuthorityLevel.OPERATOR,
            )
        )


# ── Policy registry: opportunity states ─────────────────────────────────────

class OpportunityPolicyEngine(PolicyEngine):
    """PolicyEngine subclass that understands opportunity states and the
    Operating Context constraints.

    It is a thin wrapper around the existing PolicyEngine: it does not
    replace it, it registers the operational policies and provides helpers
    to check opportunity eligibility.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._opportunity_states = set(OpportunityState)
        self._evidence_expiry: dict[str, datetime] = {}

    def register_opportunity_state(self, state: OpportunityState) -> None:
        """Register a known opportunity state (extensible)."""
        self._opportunity_states.add(state)

    def is_valid_opportunity_state(self, state: str) -> bool:
        """Check if a string is a known opportunity state."""
        return state in self._opportunity_states

    def set_evidence_expiry(self, key: str, expires_at: datetime) -> None:
        """Set the expiry of a piece of evidence (for STALE policy)."""
        self._evidence_expiry[key] = expires_at

    def get_evidence_expiry(self, key: str) -> datetime | None:
        """Get the expiry of a piece of evidence."""
        return self._evidence_expiry.get(key)

    def is_evidence_stale(self, key: str, now: datetime | None = None) -> bool:
        """Check if an evidence key is expired or stale."""
        now = now or datetime.now(UTC)
        expiry = self.get_evidence_expiry(key)
        if expiry is None:
            return False
        return expiry <= now

    def check_opportunity_eligibility(
        self,
        source: str,
        state: str,
        min_age_hours: float = 2.0,
        *,
        now: datetime | None = None,
    ) -> tuple[bool, list[str]]:
        """Check opportunity eligibility across multiple constraints.

        Returns (allowed, [blocking policy names]).
        """
        blocked: list[str] = []
        now = now or datetime.now(UTC)

        # Opportunity state must be known
        if not self.is_valid_opportunity_state(state):
            blocked.append("opcontext:deny_default")
            return False, blocked

        # Early bounty (<2h) → no early submit
        if min_age_hours > 0:
            blocked.append("opcontext:no_early_submit")

        # Don't use broken sources
        if source in {"moltjobs", "clawtasks", "nanoCORP", "mulerun", "aigen_protocol"}:
            blocked.append("opcontext:block_broken_sources")

        # Don't use paused sources
        if source in {"mcp_marketplace", "mcpize", "gravity", "apify", "forecast_bot"}:
            blocked.append("opcontext:block_broken_sources")

        # Bounty source-specific limits
        if source == "lilly-protocol":
            blocked.append("opcontext:limit_lilly_prs")
        if source == "huntr":
            blocked.append("opcontext:limit_huntr_reports")

        return len(blocked) == 0, blocked
