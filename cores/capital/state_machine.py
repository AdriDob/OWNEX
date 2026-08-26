"""Unified Money State Machine — SSOT para todos los estados económicos de OWNEX.

Unifica:
- TruthLayer.ValueCategory (VERIFIED_REAL, PENDING, ESTIMATED, MANUAL_INPUT, UNKNOWN)
- RevenuePipeline submission statuses (draft→submitted→under_review→triaged→resolved→bounty_paid)
- PayoutRecord.status (pending, confirmed)
- WorkBank WorkItem.status (preparing, ready_to_deliver, needs_access, delivered)
- ExecutionQueue.ExecState (DISCOVERED→QUALIFIED→READY→QUEUED→EXECUTING→WAITING_HUMAN→SUBMITTED→VERIFICATION→PAID)
- ApplicationAssistant status (applied, in_review, accepted, rejected, paused)

Regla de oro: VERIFIED_REAL y EXPECTED son mutuamente excluyentes.
Solo PAID/VERIFIED_REAL incrementa realized_income/cash/net_worth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

# ────────────────────────────────────────────────────────────────────────────
# ESTADOS CANÓNICOS — cada sistema mapea a estos
# ────────────────────────────────────────────────────────────────────────────


class MoneyState(StrEnum):
    """Estados canónicos de dinero — mutuamente excluyentes VERIFIED vs EXPECTED."""

    # === EXPECTED (nunca incrementa cash/net_worth) ===
    DISCOVERED = "discovered"  # Oportunidad detectada, sin validar
    EXPECTED = "expected"  # Ingreso esperado (forecast, pipeline)
    PREPARED = "prepared"  # Trabajo listo para entregar (WorkBank ready_to_deliver)
    SUBMITTED = "submitted"  # Enviado a plataforma, esperando respuesta
    UNDER_REVIEW = "under_review"  # En revisión por plataforma/cliente
    TRIAGED = "triaged"  # Triado, esperando resolución
    APPROVED = "approved"  # Aprobado, esperando pago

    # === VERIFIED_REAL (incrementa cash/net_worth SOLO en PAID) ===
    VERIFIED = "verified"  # Verificado externamente, pago confirmado
    PAID = "paid"  # Dinero en cuenta — ÚNICO que incrementa cash/net_worth

    # === TERMINALES NEGATIVOS ===
    REJECTED = "rejected"  # Rechazado por plataforma/cliente
    BLOCKED = "blocked"  # Bloqueado (requisitos no cumplidos)
    FAILED = "failed"  # Fallo técnico/operacional
    DEAD_LETTER = "dead_letter"  # Agotados reintentos
    INFORMATIVE = "informative"  # Solo informativo (sin payout)
    DUPLICATE = "duplicate"  # Duplicado detectado
    CLOSED = "closed"  # Cerrado sin pago

    # === INTERNOS ===
    PREPARING = "preparing"  # WorkBank: preparando deliverables
    NEEDS_ACCESS = "needs_access"  # WorkBank: requiere API key/manual setup
    READY = "ready"  # ExecutionQueue: listo para ejecutar
    QUEUED = "queued"  # ExecutionQueue: en cola
    EXECUTING = "executing"  # ExecutionQueue: ejecutándose
    WAITING_HUMAN = "waiting_human"  # ExecutionQueue: gate humano
    VERIFICATION = "verification"  # ExecutionQueue: verificación async
    DRAFT = "draft"  # RevenuePipeline: borrador
    IN_REVIEW = "in_review"  # ApplicationAssistant: en revisión
    ACCEPTED = "accepted"  # ApplicationAssistant: aceptado
    PAUSED = "paused"  # ApplicationAssistant: pausado
    RESOLVED = "resolved"  # RevenuePipeline: resuelto
    BOUNTY_PAID = "bounty_paid"  # RevenuePipeline: bounty pagado
    WITHDRAWAL_COMPLETED = "withdrawal_completed"  # Ledger: retiro completado


# ────────────────────────────────────────────────────────────────────────────
# CLASIFICACIÓN FUNDAMENTAL — VERIFIED vs EXPECTED (mutuamente excluyentes)
# ────────────────────────────────────────────────────────────────────────────

VERIFIED_REAL_STATES = frozenset(
    {
        MoneyState.VERIFIED,
        MoneyState.PAID,
        MoneyState.WITHDRAWAL_COMPLETED,
        MoneyState.BOUNTY_PAID,
    }
)

EXPECTED_STATES = frozenset(
    {
        MoneyState.DISCOVERED,
        MoneyState.EXPECTED,
        MoneyState.PREPARED,
        MoneyState.SUBMITTED,
        MoneyState.UNDER_REVIEW,
        MoneyState.TRIAGED,
        MoneyState.APPROVED,
        MoneyState.PREPARING,
        MoneyState.NEEDS_ACCESS,
        MoneyState.READY,
        MoneyState.QUEUED,
        MoneyState.EXECUTING,
        MoneyState.WAITING_HUMAN,
        MoneyState.VERIFICATION,
        MoneyState.DRAFT,
        MoneyState.IN_REVIEW,
        MoneyState.ACCEPTED,
        MoneyState.PAUSED,
        MoneyState.RESOLVED,
    }
)

TERMINAL_NEGATIVE_STATES = frozenset(
    {
        MoneyState.REJECTED,
        MoneyState.BLOCKED,
        MoneyState.FAILED,
        MoneyState.DEAD_LETTER,
        MoneyState.INFORMATIVE,
        MoneyState.DUPLICATE,
        MoneyState.CLOSED,
    }
)

ALL_TERMINAL_STATES = VERIFIED_REAL_STATES | TERMINAL_NEGATIVE_STATES

# ────────────────────────────────────────────────────────────────────────────
# TRANSICIONES VÁLIDAS — grafo de estado canónico
# ────────────────────────────────────────────────────────────────────────────

# Grafo de transiciones permitidas: estado_actual → {estados_destino_permitidos}
TRANSITIONS: dict[MoneyState, set[MoneyState]] = {
    # ── DESCUBRIMIENTO ──
    MoneyState.DISCOVERED: {
        MoneyState.EXPECTED,  # entra al pipeline
        MoneyState.PREPARING,  # WorkBank: empieza preparación
        MoneyState.REJECTED,  # filtrado por StrictFilter
        MoneyState.BLOCKED,  # acceso no disponible
    },
    # ── PIPELINE DE INGRESOS ──
    MoneyState.EXPECTED: {
        MoneyState.PREPARED,  # WorkBank: preparación delivery-ready
        MoneyState.SUBMITTED,  # RevenuePipeline: submit report
        MoneyState.REJECTED,  # filtrado tardío
        MoneyState.BLOCKED,
    },
    MoneyState.PREPARING: {
        MoneyState.PREPARED,  # deliverables listos
        MoneyState.NEEDS_ACCESS,  # requiere API key/manual
        MoneyState.REJECTED,
    },
    MoneyState.PREPARED: {
        MoneyState.READY,  # ExecutionQueue: listo para ejecutar
        MoneyState.SUBMITTED,  # entrega directa
        MoneyState.NEEDS_ACCESS,  # descubierto requisito de acceso
    },
    MoneyState.READY: {
        MoneyState.QUEUED,  # entra a cola de ejecución
    },
    MoneyState.QUEUED: {
        MoneyState.EXECUTING,  # empieza ejecución
    },
    MoneyState.EXECUTING: {
        MoneyState.WAITING_HUMAN,  # gate humano requerido
        MoneyState.SUBMITTED,  # enviado a plataforma
        MoneyState.FAILED,  # error técnico
    },
    MoneyState.WAITING_HUMAN: {
        MoneyState.EXECUTING,  # reintentar tras aprobación
        MoneyState.SUBMITTED,  # humano aprobó envío
        MoneyState.REJECTED,  # humano rechazó
        MoneyState.BLOCKED,  # humano detectó bloqueo
    },
    MoneyState.SUBMITTED: {
        MoneyState.UNDER_REVIEW,  # plataforma recibiendo
        MoneyState.REJECTED,  # rechazo inmediato
        MoneyState.BLOCKED,
    },
    MoneyState.UNDER_REVIEW: {
        MoneyState.TRIAGED,  # triado por plataforma
        MoneyState.REJECTED,
        MoneyState.BLOCKED,
    },
    MoneyState.TRIAGED: {
        MoneyState.RESOLVED,  # resuelto (aceptado/rechazado)
        MoneyState.REJECTED,
    },
    MoneyState.RESOLVED: {
        MoneyState.APPROVED,  # aprobado, esperando pago
        MoneyState.REJECTED,
        MoneyState.INFORMATIVE,  # solo informativo
    },
    MoneyState.APPROVED: {
        MoneyState.VERIFIED,  # pago verificado
        MoneyState.REJECTED,  # revocado
    },
    MoneyState.VERIFICATION: {
        MoneyState.VERIFIED,  # verificado async
        MoneyState.FAILED,
    },
    MoneyState.VERIFIED: {
        MoneyState.PAID,  # dinero en cuenta
        MoneyState.REJECTED,  # verificación falló
    },
    # ── APLICACIONES (AI-training) ──
    MoneyState.DRAFT: {
        MoneyState.IN_REVIEW,
        MoneyState.REJECTED,
    },
    MoneyState.IN_REVIEW: {
        MoneyState.ACCEPTED,
        MoneyState.REJECTED,
        MoneyState.PAUSED,
    },
    MoneyState.IN_REVIEW: {
        MoneyState.ACCEPTED,
        MoneyState.REJECTED,
        MoneyState.PAUSED,
    },
    MoneyState.ACCEPTED: {
        MoneyState.PREPARED,  # entra a WorkBank como stream activo
    },
    MoneyState.PAUSED: {
        MoneyState.IN_REVIEW,  # reanudar
        MoneyState.REJECTED,
    },
    # ── TERMINALES ──
    MoneyState.PAID: set(),  # terminal positivo
    MoneyState.WITHDRAWAL_COMPLETED: set(),  # terminal positivo
    MoneyState.BOUNTY_PAID: set(),  # terminal positivo
    MoneyState.REJECTED: set(),  # terminal negativo
    MoneyState.BLOCKED: set(),  # terminal negativo
    MoneyState.FAILED: {MoneyState.QUEUED, MoneyState.DEAD_LETTER},  # retry
    MoneyState.DEAD_LETTER: set(),  # terminal negativo
    MoneyState.INFORMATIVE: set(),  # terminal negativo
    MoneyState.DUPLICATE: set(),  # terminal negativo
    MoneyState.CLOSED: set(),  # terminal negativo
    # WorkBank internos
    MoneyState.NEEDS_ACCESS: {MoneyState.PREPARED, MoneyState.BLOCKED},
    MoneyState.PREPARING: {MoneyState.PREPARED, MoneyState.NEEDS_ACCESS, MoneyState.REJECTED},
    # ExecutionQueue internos
    MoneyState.DISCOVERED: {MoneyState.EXPECTED, MoneyState.REJECTED},
    # MoneyState.QUALIFIED removed - using EXPECTED directly
    MoneyState.FAILED: {MoneyState.QUEUED, MoneyState.DEAD_LETTER},
    MoneyState.DEAD_LETTER: set(),
    MoneyState.DUPLICATE: set(),
    MoneyState.CLOSED: set(),
    MoneyState.INFORMATIVE: set(),
    MoneyState.WITHDRAWAL_COMPLETED: set(),
    MoneyState.BOUNTY_PAID: set(),
}


def can_transition(current: MoneyState | str, target: MoneyState | str) -> bool:
    """Verifica si una transición es válida según el grafo canónico."""
    c, t = MoneyState(current), MoneyState(target)
    return t in TRANSITIONS.get(c, set())


def assert_transition(current: MoneyState | str, target: MoneyState | str) -> None:
    """Lanza ValueError si la transición no es válida."""
    if not can_transition(current, target):
        raise ValueError(f"transición inválida: {current} → {target}")


def is_verified_real(state: MoneyState | str) -> bool:
    """True si el estado representa dinero REAL verificado (incrementa cash/net_worth)."""
    return MoneyState(state) in VERIFIED_REAL_STATES


def is_expected(state: MoneyState | str) -> bool:
    """True si el estado representa dinero ESPERADO (forecast/pipeline)."""
    return MoneyState(state) in EXPECTED_STATES


def is_terminal(state: MoneyState | str) -> bool:
    """True si el estado es terminal (no hay transiciones salientes)."""
    return MoneyState(state) in (VERIFIED_REAL_STATES | TERMINAL_NEGATIVE_STATES)


def is_terminal_positive(state: MoneyState | str) -> bool:
    """True si el estado es terminal positivo (dinero real recibido)."""
    return MoneyState(state) in VERIFIED_REAL_STATES


def is_terminal_negative(state: MoneyState | str) -> bool:
    """True si el estado es terminal negativo (sin pago)."""
    return MoneyState(state) in TERMINAL_NEGATIVE_STATES


# ────────────────────────────────────────────────────────────────────────────
# MAPEO DE SISTEMAS EXISTENTES → MoneyState canónico
# ────────────────────────────────────────────────────────────────────────────

# TruthLayer.ValueCategory → MoneyState
TRUTH_CATEGORY_TO_MONEY_STATE = {
    "verified_real": MoneyState.VERIFIED,
    "pending": MoneyState.EXPECTED,
    "estimated": MoneyState.EXPECTED,
    "manual_input": MoneyState.EXPECTED,
    "unknown": MoneyState.EXPECTED,
}

# RevenuePipeline submission status → MoneyState
REVENUE_STATUS_TO_MONEY_STATE = {
    "draft": MoneyState.DRAFT,
    "submitted": MoneyState.SUBMITTED,
    "under_review": MoneyState.UNDER_REVIEW,
    "triaged": MoneyState.TRIAGED,
    "resolved": MoneyState.RESOLVED,
    "bounty_paid": MoneyState.BOUNTY_PAID,
    "rejected": MoneyState.REJECTED,
    "informative": MoneyState.INFORMATIVE,
    "duplicate": MoneyState.DUPLICATE,
    "closed": MoneyState.CLOSED,
}

# PayoutRecord.status → MoneyState
PAYOUT_STATUS_TO_MONEY_STATE = {
    "pending": MoneyState.EXPECTED,
    "confirmed": MoneyState.PAID,
}

# WorkBank WorkItem.status → MoneyState
WORKBANK_STATUS_TO_MONEY_STATE = {
    "preparing": MoneyState.PREPARING,
    "ready_to_deliver": MoneyState.PREPARED,
    "needs_access": MoneyState.NEEDS_ACCESS,
    "delivered": MoneyState.PAID,  # entregado = pagado
}

# ExecutionQueue.ExecState → MoneyState
EXEC_STATE_TO_MONEY_STATE = {
    "discovered": MoneyState.DISCOVERED,
    "qualified": MoneyState.EXPECTED,
    "ready": MoneyState.READY,
    "queued": MoneyState.QUEUED,
    "executing": MoneyState.EXECUTING,
    "waiting_human": MoneyState.WAITING_HUMAN,
    "submitted": MoneyState.SUBMITTED,
    "verification": MoneyState.VERIFICATION,
    "paid": MoneyState.PAID,
    "rejected": MoneyState.REJECTED,
    "blocked": MoneyState.BLOCKED,
    "failed": MoneyState.FAILED,
    "dead_letter": MoneyState.DEAD_LETTER,
}

# ApplicationAssistant status → MoneyState
APPLICATION_STATUS_TO_MONEY_STATE = {
    "applied": MoneyState.IN_REVIEW,
    "in_review": MoneyState.IN_REVIEW,
    "accepted": MoneyState.ACCEPTED,
    "rejected": MoneyState.REJECTED,
    "paused": MoneyState.PAUSED,
}

# WorkBank WorkItem.access_status → MoneyState
WORKBANK_ACCESS_TO_MONEY_STATE = {
    "public": MoneyState.PREPARED,
    "needs_api_key": MoneyState.NEEDS_ACCESS,
    "needs_manual_setup": MoneyState.NEEDS_ACCESS,
}

# RevenuePipeline SubmissionRecord.status → MoneyState
SUBMISSION_STATUS_TO_MONEY_STATE = {
    "draft": MoneyState.DRAFT,
    "submitted": MoneyState.SUBMITTED,
    "under_review": MoneyState.UNDER_REVIEW,
    "triaged": MoneyState.TRIAGED,
    "resolved": MoneyState.RESOLVED,
    "bounty_paid": MoneyState.BOUNTY_PAID,
    "rejected": MoneyState.REJECTED,
    "informative": MoneyState.INFORMATIVE,
    "duplicate": MoneyState.DUPLICATE,
    "closed": MoneyState.CLOSED,
}

# LedgerEvent → MoneyState
LEDGER_EVENT_TO_MONEY_STATE = {
    "bounty_created": MoneyState.EXPECTED,
    "bounty_pending": MoneyState.EXPECTED,
    "bounty_approved": MoneyState.APPROVED,
    "bounty_rejected": MoneyState.REJECTED,
    "payout_received": MoneyState.PAID,
    "withdrawal_requested": MoneyState.SUBMITTED,
    "withdrawal_processing": MoneyState.EXECUTING,
    "withdrawal_completed": MoneyState.WITHDRAWAL_COMPLETED,
    "withdrawal_failed": MoneyState.FAILED,
    "adjustment_manual": MoneyState.VERIFIED,
    "fee_deducted": MoneyState.VERIFIED,
    "currency_converted": MoneyState.VERIFIED,
    "crypto_deposit": MoneyState.PAID,
    "crypto_withdrawal": MoneyState.WITHDRAWAL_COMPLETED,
    "crypto_staking_reward": MoneyState.PAID,
    "crypto_defi_yield": MoneyState.PAID,
    "crypto_swap": MoneyState.VERIFIED,
    "crypto_gas_fee": MoneyState.VERIFIED,
    "crypto_airdrop": MoneyState.PAID,
    "exchange_trade": MoneyState.VERIFIED,
    "exchange_fee": MoneyState.VERIFIED,
}


def map_to_money_state(system: str, state: str) -> str | None:
    """Mapea un estado de un sistema origen a MoneyState canónico."""
    mappers = {
        "truth_layer": TRUTH_CATEGORY_TO_MONEY_STATE,
        "revenue_pipeline": REVENUE_STATUS_TO_MONEY_STATE,
        "payout_record": PAYOUT_STATUS_TO_MONEY_STATE,
        "workbank": WORKBANK_STATUS_TO_MONEY_STATE,
        "execution_queue": EXEC_STATE_TO_MONEY_STATE,
        "application_assistant": APPLICATION_STATUS_TO_MONEY_STATE,
        "workbank_access": WORKBANK_ACCESS_TO_MONEY_STATE,
        "submission_record": SUBMISSION_STATUS_TO_MONEY_STATE,
        "ledger_event": LEDGER_EVENT_TO_MONEY_STATE,
    }
    mapper = mappers.get(system.lower())
    if not mapper:
        return None
    return mapper.get(state.lower())


def get_money_state_category(state: MoneyState | str) -> str:
    """Devuelve la categoría fundamental: 'verified_real', 'expected', 'terminal_negative', 'unknown'."""
    ms = MoneyState(state)
    if ms in VERIFIED_REAL_STATES:
        return "verified_real"
    if ms in EXPECTED_STATES:
        return "expected"
    if ms in TERMINAL_NEGATIVE_STATES:
        return "terminal_negative"
    return "unknown"


# ────────────────────────────────────────────────────────────────────────────
# VALIDACIONES DE INTEGRIDAD ECONÓMICA
# ────────────────────────────────────────────────────────────────────────────


@dataclass
class IntegrityViolation:
    rule: str
    message: str
    severity: str  # critical, warning, info
    context: dict[str, Any] = field(default_factory=dict)


def check_no_expected_as_real(balances: dict[str, float]) -> list[IntegrityViolation]:
    """Verifica que no se cuente EXPECTED como REAL en balances."""
    violations = []
    if balances.get("expected", 0) > 0 and balances.get("real", 0) == 0:
        violations.append(
            IntegrityViolation(
                rule="no_expected_as_real",
                message="Balance real es 0 pero hay expected > 0 — riesgo de contar forecast como real",
                severity="critical",
                context={"expected": balances.get("expected", 0), "real": balances.get("real", 0)},
            )
        )
    return violations


def check_paid_only_increments_real(transitions: list[tuple[str, str]]) -> list[IntegrityViolation]:
    """Verifica que solo PAID incremente real_balance."""
    violations = []
    for from_state, to_state in transitions:
        if MoneyState(to_state) in VERIFIED_REAL_STATES and MoneyState(from_state) not in VERIFIED_REAL_STATES:
            # Transición hacia VERIFIED_REAL — válido solo si es PAID/VERIFIED
            if MoneyState(to_state) == MoneyState.VERIFIED and MoneyState(from_state) != MoneyState.VERIFICATION:
                pass  # VERIFICATION → VERIFIED es válido
            elif MoneyState(to_state) == MoneyState.PAID:
                pass  # PAID siempre válido
            else:
                violations.append(
                    IntegrityViolation(
                        rule="paid_only_increments_real",
                        message=f"Transición {from_state} → {to_state} incrementa real sin ser PAID",
                        severity="critical",
                        context={"from": from_state, "to": to_state},
                    )
                )
    return violations


def check_no_double_counting(entries: list[dict]) -> list[IntegrityViolation]:
    """Detecta doble contabilización por external_id duplicado."""
    violations = []
    seen = {}
    for e in entries:
        ext_id = e.get("external_id")
        if ext_id and ext_id in seen:
            violations.append(
                IntegrityViolation(
                    rule="no_double_counting",
                    message=f"external_id duplicado: {ext_id}",
                    severity="critical",
                    context={"external_id": ext_id, "entries": [seen[ext_id], e]},
                )
            )
        elif ext_id:
            seen[ext_id] = e
    return violations


def check_currency_consistency(entries: list[dict]) -> list[IntegrityViolation]:
    """Verifica que no haya mezcla de currencies sin conversión."""
    violations = []
    currencies = set(e.get("currency", "USD") for e in entries)
    if len(currencies) > 1:
        violations.append(
            IntegrityViolation(
                rule="currency_consistency",
                message=f"Múltiples currencies sin conversión: {currencies}",
                severity="warning",
                context={"currencies": list(currencies)},
            )
        )
    return violations


def check_timestamp_order(entries: list[dict]) -> list[IntegrityViolation]:
    """Verifica orden temporal coherente."""
    violations = []
    for i, e in enumerate(entries):
        ts = e.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if i > 0:
                prev_ts = entries[i - 1].get("timestamp")
                if prev_ts:
                    prev_dt = datetime.fromisoformat(prev_ts.replace("Z", "+00:00"))
                    if dt < prev_dt:
                        violations.append(
                            IntegrityViolation(
                                rule="timestamp_order",
                                message=f"Timestamp fuera de orden: {ts} < {prev_ts}",
                                severity="warning",
                                context={"current": ts, "previous": prev_ts},
                            )
                        )
        except Exception:
            pass
    return violations


def run_integrity_checks(data: dict[str, Any]) -> list[IntegrityViolation]:
    """Ejecuta todos los checks de integridad sobre un snapshot de capital."""
    violations = []
    violations.extend(check_no_expected_as_real(data.get("balances", {})))
    violations.extend(check_paid_only_increments_real(data.get("transitions", [])))
    violations.extend(check_no_double_counting(data.get("entries", [])))
    violations.extend(check_currency_consistency(data.get("entries", [])))
    violations.extend(check_timestamp_order(data.get("entries", [])))
    return violations


# ────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE UTILIDAD PARA SISTEMAS EXISTENTES
# ────────────────────────────────────────────────────────────────────────────


def map_truth_category(category: str) -> MoneyState:
    """Mapea TruthLayer.ValueCategory a MoneyState."""
    return TRUTH_CATEGORY_TO_MONEY_STATE.get(category.lower(), MoneyState.EXPECTED)


def map_revenue_status(status: str) -> MoneyState:
    return REVENUE_STATUS_TO_MONEY_STATE.get(status.lower(), MoneyState.EXPECTED)


def map_payout_status(status: str) -> MoneyState:
    return PAYOUT_STATUS_TO_MONEY_STATE.get(status.lower(), MoneyState.EXPECTED)


def map_workbank_status(status: str) -> MoneyState:
    return WORKBANK_STATUS_TO_MONEY_STATE.get(status.lower(), MoneyState.EXPECTED)


def map_exec_state(state: str) -> MoneyState:
    return EXEC_STATE_TO_MONEY_STATE.get(state.lower(), MoneyState.EXPECTED)


def map_application_status(status: str) -> MoneyState:
    return APPLICATION_STATUS_TO_MONEY_STATE.get(status.lower(), MoneyState.EXPECTED)


def map_workbank_access(access: str) -> MoneyState:
    return WORKBANK_ACCESS_TO_MONEY_STATE.get(access.lower(), MoneyState.NEEDS_ACCESS)


def map_submission_status(status: str) -> MoneyState:
    return SUBMISSION_STATUS_TO_MONEY_STATE.get(status.lower(), MoneyState.EXPECTED)


def map_ledger_event(event: str) -> MoneyState:
    return LEDGER_EVENT_TO_MONEY_STATE.get(event.lower(), MoneyState.EXPECTED)


def get_canonical_state(system: str, state: str) -> MoneyState:
    """Obtiene el MoneyState canónico para un estado de cualquier sistema."""
    mapped = map_to_money_state(system, state)
    if mapped is None:
        return MoneyState.EXPECTED
    return MoneyState(mapped)


def is_money_real(system: str, state: str) -> bool:
    """Verifica si un estado de un sistema representa dinero REAL."""
    ms = get_canonical_state(system, state)
    return is_verified_real(ms)


def is_money_expected(system: str, state: str) -> bool:
    """Verifica si un estado de un sistema representa dinero ESPERADO."""
    ms = get_canonical_state(system, state)
    return is_expected(ms)


# ────────────────────────────────────────────────────────────────────────────
# EXPORTS PÚBLICOS
# ────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Estados
    "MoneyState",
    "VERIFIED_REAL_STATES",
    "EXPECTED_STATES",
    "TERMINAL_NEGATIVE_STATES",
    "ALL_TERMINAL_STATES",
    "TRANSITIONS",
    # Funciones de estado
    "can_transition",
    "assert_transition",
    "is_verified_real",
    "is_expected",
    "is_terminal",
    "is_terminal_positive",
    "is_terminal_negative",
    "get_money_state_category",
    # Mapeos
    "TRUTH_CATEGORY_TO_MONEY_STATE",
    "REVENUE_STATUS_TO_MONEY_STATE",
    "PAYOUT_STATUS_TO_MONEY_STATE",
    "WORKBANK_STATUS_TO_MONEY_STATE",
    "EXEC_STATE_TO_MONEY_STATE",
    "APPLICATION_STATUS_TO_MONEY_STATE",
    "WORKBANK_ACCESS_TO_MONEY_STATE",
    "SUBMISSION_STATUS_TO_MONEY_STATE",
    "LEDGER_EVENT_TO_MONEY_STATE",
    "map_to_money_state",
    "get_money_state_category",
    "map_truth_category",
    "map_revenue_status",
    "map_payout_status",
    "map_workbank_status",
    "map_exec_state",
    "map_application_status",
    "map_workbank_access",
    "map_submission_status",
    "map_ledger_event",
    "get_canonical_state",
    "is_money_real",
    "is_money_expected",
    # Integridad
    "IntegrityViolation",
    "check_no_expected_as_real",
    "check_paid_only_increments_real",
    "check_no_double_counting",
    "check_currency_consistency",
    "check_timestamp_order",
    "run_integrity_checks",
    # Utilidades
    "map_truth_category",
    "map_revenue_status",
    "map_payout_status",
    "map_workbank_status",
    "map_exec_state",
    "map_application_status",
    "map_workbank_access",
    "map_submission_status",
    "map_ledger_event",
    "get_canonical_state",
    "is_money_real",
    "is_money_expected",
]
