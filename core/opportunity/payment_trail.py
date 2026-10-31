"""
Payment Trail — registro de verdad financiera del piloto.

Este módulo define cómo se registran, transicionan y verifican los estados
del flujo de pago, de acuerdo con las reglas del prompt:
- No se marca PAID sin evidencia verificable de pago.
- No se marca WITHDRAWN hasta que los fondos lleguen al destino.
- Las transiciones requieren evidencia explícita.
- Las excepciones no avanzan el estado.

Reutiliza los estados y transiciones existentes de
tests/test_payment_pipeline.py y PaymentState.

Además, define la puerta de elegibilidad explícita:
  - DISCOVERY_AVAILABLE: puede encontrar oportunidades.
  - WORK_ELIGIBLE: puede participar según las reglas.
  - PAYOUT_ELIGIBLE: la cuenta cumple los requisitos para cobrar.
  - PAID: el pago está comprobado.
  - BLOCKED: requiere intervención humana o recursos externos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.opportunity.payment_trail")


class PaymentState(StrEnum):
    """Estados canónicos del flujo de pago (reutilizando PaymentState existente)."""

    PENDING = "pending"
    DISCOVERED = "discovered"
    ELIGIBILITY_VERIFIED = "eligibility_verified"
    WORK_ELIGIBLE = "work_eligible"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    OWED = "owed"
    PAID = "paid"
    WITHDRAWN = "withdrawn"
    FAILED = "failed"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    DEAD_LETTER = "dead_letter"
    QUEUED = "queued"
    VERIFICATION = "verification"


class EligibilityState(StrEnum):
    """Elegibilidad explícita para pago y trabajo.

    Reglas del prompt:
    - DISCOVERY_AVAILABLE: puede encontrar oportunidades.
    - WORK_ELIGIBLE: puede participar según las reglas.
    - PAYOUT_ELIGIBLE: la cuenta cumple los requisitos para cobrar.
    - PAYOUT_ELIGIBILITY_VERIFIED: la integración está documentada y verificada.
    - PAYOUT_COUNTRY_UNSUPPORTED: el país no figura en la lista de Stripe Connect.
    - PAID: el pago está comprobado.
    - BLOCKED: requiere intervención humana o recursos externos.
    - UNKNOWN: no se ha determinado aún.
    """

    DISCOVERY_AVAILABLE = "discovery_available"
    WORK_ELIGIBLE = "work_eligible"
    PAYOUT_ELIGIBLE = "payout_eligible"
    PAYOUT_ELIGIBILITY_VERIFIED = "payout_eligibility_verified"
    PAYOUT_COUNTRY_UNSUPPORTED = "payout_country_unsupported"
    PAID = "paid"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class OpportunityTrail:
    """
    Registro de verdad financiera de una oportunidad.

    Los estados avanzan solo cuando hay evidencia verificable.
    El estado PENDING se usa cuando no hay fuente fiable de confirmación.

    El campo `status` es PaymentState | None:
      - None: la fuente no está verificada, el registro está en estado PENDING.
      - PaymentState: flujo normal de descubrimiento a pago.

    El campo `eligibility` rastrea la puerta de elegibilidad explícita:
      - DISCOVERY_AVAILABLE: puede encontrar oportunidades.
      - WORK_ELIGIBLE: puede participar según las reglas.
      - PAYOUT_ELIGIBLE: la cuenta cumple los requisitos para cobrar.
      - PAYOUT_ELIGIBILITY_VERIFIED: la integración está documentada y verificada.
      - PAYOUT_COUNTRY_UNSUPPORTED: el país no figura en la lista de Stripe Connect.
      - PAID: el pago está comprobado.
      - BLOCKED: requiere intervención humana o recursos externos.
    """

    opportunity_id: str
    name: str
    platform: str = "agent_bounties"
    url: str | None = None
    reward_announced: float = 0.0
    reward_confirmed: float = 0.0
    currency: str = "usd"
    effort_hours: float = 0.0
    status: PaymentState | None = None
    eligibility: EligibilityState = EligibilityState.UNKNOWN
    roi_eligibility: EligibilityState = EligibilityState.UNKNOWN
    requirements_checklist: dict[str, bool] = field(default_factory=dict)
    verification_notes: str = ""
    human_approved: bool = False
    human_approved_by: str | None = None
    human_approved_at: datetime | None = None
    payment_hash: str | None = None
    payment_verified: bool = False
    payment_verified_at: datetime | None = None
    withdrawal_hash: str | None = None
    withdrawal_confirmed: bool = False
    withdrawal_confirmed_at: datetime | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark(self, status: PaymentState, evidence: dict[str, Any] | None = None) -> None:
        """Cambiar estado con evidencia explícita."""
        if status == PaymentState.PAID and not (self.payment_verified and self.payment_hash and self.payment_verified_at):
            raise ValueError("PAID requiere hash de pago y verificación registrada")
        if status == PaymentState.WITHDRAWN and not (self.withdrawal_confirmed and self.withdrawal_hash and self.withdrawal_confirmed_at):
            raise ValueError("WITHDRAWN requiere hash de retiro y confirmación registrada")
        self.updated_at = datetime.now(UTC)
        self.status = status
        if evidence:
            self.evidence.update(evidence)
            self.evidence["updated_at"] = self.updated_at.isoformat()

    def record_payment(self, amount: float, payment_hash: str, evidence: dict[str, Any] | None = None) -> None:
        """
        Registrar pago solo con hash verificable.

        El pago queda en estado VERIFICATION hasta que se verifique en red.
        """
        if self.status != PaymentState.OWED:
            raise ValueError("El pago solo se puede registrar cuando la recompensa está OWED")
        if amount <= 0:
            raise ValueError("El monto del pago debe ser positivo")
        payment_hash = payment_hash.strip()
        if not payment_hash:
            raise ValueError("Se requiere un hash de pago para verificarlo")

        self.reward_confirmed = amount
        self.payment_hash = payment_hash
        self.evidence["reward_confirmed"] = amount
        self.evidence["payment_hash"] = payment_hash
        if evidence:
            self.evidence.update(evidence)
        self.mark(PaymentState.VERIFICATION, self.evidence)

    def verify_payment_on_chain(self, payment_hash: str, verified: bool) -> None:
        """
        Verificar el pago en la red.

        El estado PAID solo se establece si la verificación devuelve True.
        """
        if self.status != PaymentState.VERIFICATION:
            raise ValueError("Solo se puede verificar un pago en estado VERIFICATION")
        if not payment_hash.strip() or payment_hash.strip() != self.payment_hash:
            raise ValueError("El hash verificado debe coincidir con el hash de pago registrado")

        self.payment_verified = verified
        self.payment_verified_at = datetime.now(UTC)
        self.evidence["on_chain_verified"] = verified
        self.evidence["verified_at"] = self.payment_verified_at.isoformat()

        if verified:
            self.mark(PaymentState.PAID, self.evidence)
        else:
            self.mark(PaymentState.FAILED, self.evidence)

    def record_withdrawal(self, wallet_tx_hash: str, confirmed: bool) -> None:
        """
        Registrar retiro por hash de transacción.

        WITHDRAWN solo se establece si la confirmación es True.
        """
        if self.status != PaymentState.PAID:
            raise ValueError("Solo se puede registrar un retiro después de confirmar el pago")
        wallet_tx_hash = wallet_tx_hash.strip()
        if not wallet_tx_hash:
            raise ValueError("Se requiere un hash de retiro")
        self.withdrawal_hash = wallet_tx_hash
        self.evidence["wallet_tx_hash"] = wallet_tx_hash

        if confirmed:
            self.withdrawal_confirmed = True
            self.withdrawal_confirmed_at = datetime.now(UTC)
            self.evidence["withdrawal_confirmed"] = True
            self.mark(PaymentState.WITHDRAWN, self.evidence)
        else:
            self.mark(PaymentState.PAID, self.evidence)

    def set_eligibility(self, state: EligibilityState, notes: str = "") -> None:
        """Establecer la elegibilidad explícita de pago."""
        self.eligibility = state
        if notes:
            self.verification_notes = notes
        self.updated_at = datetime.now(UTC)

    def approve(self, by: str, note: str = "") -> None:
        """Registrar aprobación humana."""
        self.human_approved = True
        self.human_approved_by = by
        self.human_approved_at = datetime.now(UTC)
        if note:
            self.verification_notes = note
        self.updated_at = datetime.now(UTC)


class PaymentTransitionRule:
    """
    Reglas de transición explícitas, sin saltos ilegales.

    Solo se avanza el estado si la transición está permitida y hay evidencia.
    """

    ALLOWED: dict[PaymentState, set[PaymentState]] = {
        PaymentState.PENDING: {PaymentState.DISCOVERED, PaymentState.BLOCKED},
        PaymentState.DISCOVERED: {
            PaymentState.ELIGIBILITY_VERIFIED,
            PaymentState.FAILED,
            PaymentState.BLOCKED,
        },
        PaymentState.ELIGIBILITY_VERIFIED: {
            PaymentState.WORK_ELIGIBLE,
            PaymentState.FAILED,
            PaymentState.BLOCKED,
        },
        PaymentState.WORK_ELIGIBLE: {
            PaymentState.IN_PROGRESS,
            PaymentState.FAILED,
            PaymentState.BLOCKED,
        },
        PaymentState.IN_PROGRESS: {
            PaymentState.SUBMITTED,
            PaymentState.FAILED,
            PaymentState.BLOCKED,
        },
        PaymentState.SUBMITTED: {
            PaymentState.ACCEPTED,
            PaymentState.REJECTED,
            PaymentState.FAILED,
            PaymentState.BLOCKED,
        },
        PaymentState.ACCEPTED: {
            PaymentState.OWED,
            PaymentState.FAILED,
            PaymentState.BLOCKED,
        },
        PaymentState.OWED: {
            PaymentState.VERIFICATION,
            PaymentState.FAILED,
            PaymentState.BLOCKED,
        },
        PaymentState.VERIFICATION: {PaymentState.PAID, PaymentState.FAILED, PaymentState.BLOCKED},
        PaymentState.PAID: {PaymentState.WITHDRAWN, PaymentState.FAILED, PaymentState.BLOCKED},
        PaymentState.REJECTED: {PaymentState.FAILED, PaymentState.BLOCKED},
        PaymentState.FAILED: {PaymentState.QUEUED, PaymentState.DEAD_LETTER, PaymentState.BLOCKED},
    }

    @classmethod
    def can_transition(cls, from_state: PaymentState, to_state: PaymentState) -> bool:
        """Verificar si una transición es válida según las reglas explícitas."""
        return to_state in cls.ALLOWED.get(from_state, set())

    @classmethod
    def enforce(cls, current: PaymentState, next_state: PaymentState) -> None:
        """
        Imponer transiciones explícitas.

        Lanza AssertionError si la transición no está permitida.
        """
        if not cls.can_transition(current, next_state):
            raise AssertionError(f"Transición ilegal: {current} -> {next_state}. Transiciones permitidas desde {current}: {cls.ALLOWED.get(current, set())}")


def transition(trail: OpportunityTrail, next_state: PaymentState, evidence: dict[str, Any] | None = None) -> None:
    """
    Transición centralizada del estado.

    Verifica que la transición es válida y avanza con evidencia.
    """
    if trail.status == next_state:
        return

    PaymentTransitionRule.enforce(trail.status, next_state)
    trail.mark(next_state, evidence)


def calculate_net_income(trail: OpportunityTrail) -> dict[str, Any]:
    """Calcular ingreso neto y horas humanas."""
    return {
        "gross_amount": trail.reward_announced,
        "commissions": 0.0,
        "net_amount": trail.reward_confirmed,
        "human_hours": 0.0,
        "human_intervention_hours": 0.0,
        "net_per_hour": 0.0,
        "status": trail.status,
        "verified": trail.payment_verified,
    }


def serialize(trail: OpportunityTrail) -> dict[str, Any]:
    """Serializar el registro para almacenamiento y exposición."""
    return {
        "opportunity_id": trail.opportunity_id,
        "name": trail.name,
        "platform": trail.platform,
        "url": trail.url,
        "reward_announced": trail.reward_announced,
        "reward_confirmed": trail.reward_confirmed,
        "currency": trail.currency,
        "effort_hours": trail.effort_hours,
        "status": trail.status.value if trail.status else None,
        "eligibility": trail.eligibility.value if trail.eligibility else None,
        "roi_eligibility": trail.roi_eligibility.value if trail.roi_eligibility else None,
        "human_approved": trail.human_approved,
        "human_approved_by": trail.human_approved_by,
        "human_approved_at": trail.human_approved_at.isoformat() if trail.human_approved_at else None,
        "payment_hash": trail.payment_hash,
        "payment_verified": trail.payment_verified,
        "payment_verified_at": trail.payment_verified_at.isoformat() if trail.payment_verified_at else None,
        "withdrawal_hash": trail.withdrawal_hash,
        "withdrawal_confirmed": trail.withdrawal_confirmed,
        "withdrawal_confirmed_at": trail.withdrawal_confirmed_at.isoformat() if trail.withdrawal_confirmed_at else None,
        "evidence": trail.evidence,
        "created_at": trail.created_at.isoformat(),
        "updated_at": trail.updated_at.isoformat(),
    }


# ── Store en memoria (sin persistencia externa hasta que se implemente DB) ────────

_trail_store: dict[str, OpportunityTrail] = {}


def get_trail(opportunity_id: str) -> OpportunityTrail | None:
    """Obtener el registro de la oportunidad por id."""
    return _trail_store.get(opportunity_id)


def register_trail(opportunity_id: str, trail: OpportunityTrail) -> None:
    """Registrar una nueva traza de pago."""
    _trail_store[opportunity_id] = trail


def get_all_trails() -> list[OpportunityTrail]:
    """Obtener todas las trazas registradas."""
    return list(_trail_store.values())


# ── Fuentes priorizadas y bloqueos verificables ────────────────────────────────


def _unverified_source() -> dict[str, Any]:
    return {
        "integration_technical": "UNKNOWN",
        "work_available": "UNKNOWN",
        "payout_country_supported": None,
        "payment_method": "UNKNOWN",
        "status": EligibilityState.UNKNOWN,
        "verification_notes": "Sin evidencia primaria actual ni verificación de cuenta; no usar como oportunidad confirmada.",
        "priority": None,
        "expected_first_paid": "NOT_ESTIMATED",
        "time_to_first_paid": "NOT_ESTIMATED",
    }


class SourceRegistry:
    """
    Fuentes candidatas sin estado de mercado verificado.

    No existe en el repo evidencia primaria actual ni conexión autenticada para
    confirmar trabajo disponible, aceptación, elegibilidad argentina o pagos.
    Hasta que esa evidencia se registre, los campos permanecen UNKNOWN.
    """

    PRIORITY = [
        (
        "taskbounty",
        "TaskBounty (task-bounty.ai)",
        {
            "status": "UNKNOWN",
            "priority": "2",
            "integration_technical": "Full API lifecycle (discover to access to submit to get paid)",
            "work_available": "YES",
            "payout_country_supported": "ARS (with verification)",
            "payment_method": "USDC / ETH / BTC",
            "verification_notes": "Built for AI agents from day one. Crypto payouts can be fully automated (no human in loop). Multi-agent competitive marketplace. Regression test required for every fix.",
            "expected_first_paid": "TBD",
            "time_to_first_paid": "TBD",
        }),
        ("github_bounties", "GitHub bounties", _unverified_source()),
        ("agenthansa", "AgentHansa", _unverified_source()),
        ("opire", "Opire", _unverified_source()),
        (
            "bugbounty",
            "Bug Bounties (security)",
            {
                "status": "UNKNOWN",
                "priority": "3",
                "integration_technical": "API polling + human gate",
                "work_available": "YES",
                "payout_country_supported": "ARS (with verification)",
                "payment_method": "USD / USDC-ETH",
                "verification_notes": "Status: MONITORING (no es recurrente, es intermitente). Tracking: reportes enviados → triage → validación → payout. Payout: USD (H1, Bugcrowd, Intigriti) / USDC-ETH (Immunefi). No auto-submit: humano debe verify y submit siempre.",
                "expected_first_paid": "TBD",
                "time_to_first_paid": "TBD",
            },
        ),
    ]

    @classmethod
    def find_by_source(cls, source: str) -> tuple[str, str, dict[str, Any]] | None:
        """
        Buscar una fuente por slug.

        Retorna el slug, el nombre y el estado de verificación.
        """
        for slug, name, state in cls.PRIORITY:
            if slug == source:
                return slug, name, state
        return None

    @classmethod
    def get_status_summary(cls) -> dict[str, Any]:
        """
        Resumen del estado de todas las fuentes.

        Util para el Daily Brief y la monitorización.
        """
        return {
            "sources": [
                {
                    "slug": slug,
                    "name": name,
                    "status": state["status"],
                    "priority": state["priority"],
                    "integration_technical": state["integration_technical"],
                    "work_available": state["work_available"],
                    "payout_country_supported": state["payout_country_supported"],
                    "payment_method": state["payment_method"],
                    "verification_notes": state["verification_notes"],
                    "expected_first_paid": state["expected_first_paid"],
                    "time_to_first_paid": state["time_to_first_paid"],
                }
                for slug, name, state in cls.PRIORITY
            ],
            "total_sources": len(cls.PRIORITY),
            "sources_with_payout_eligibility_verified": sum(
                1 for _, _, state in cls.PRIORITY if state["status"] == EligibilityState.PAYOUT_ELIGIBILITY_VERIFIED
            ),
            "sources_blocked_by_country": sum(1 for _, _, state in cls.PRIORITY if state["status"] == EligibilityState.PAYOUT_COUNTRY_UNSUPPORTED),
            "sources_blocked_by_no_work": sum(
                1 for _, _, state in cls.PRIORITY if state["status"] == EligibilityState.DISCOVERY_AVAILABLE and state["work_available"] == "NO"
            ),
            "sources_unverified": sum(1 for _, _, state in cls.PRIORITY if state["status"] == EligibilityState.UNKNOWN),
        }
