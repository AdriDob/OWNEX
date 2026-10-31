"""
Payment Adapters — verificación de métodos de cobro.

Este módulo define cómo OWNEX verifica y registra los métodos de cobro disponibles
para recibir pagos, sin almacenar secretos.

Métodos soportados:
- stripe_connect: estado argentino no confirmado; requiere verificar plataforma y beneficiario
- wise: Wise (UK)
- paypal: PayPal
- bank_transfer: Bancos argentinos (transferencia bancaria)
- crypto_usdc: USDC / crypto
- manual_bank: Recibo bancario manual

Reglas del prompt aplicadas:
- No almacenar secretos en logs, commits ni artefactos.
- Verificar método mediante documentación oficial y siguiendo las reglas del prompt.
- No ejecutar acciones externas irreversibles sin la aprobación humana requerida.
- Las transiciones de estado requieren evidencia explícita.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from core.opportunity.payment_methods import (
    PaymentMethodStatus as EligibilityStatus,
)
from core.opportunity.payment_methods import (
    PaymentMethodType,
    get_payment_method,
)

logger = logging.getLogger("ownex.payment_methods")


class PaymentAdapter:
    """
    Adaptador de cobro.

    Verifica la disponibilidad de un método de cobro y registra el estado.
    No almacena secretos, solo verifica mediante documentación oficial.

    Reglas del prompt aplicadas:
    - Denegación por defecto: sin verificación, no se asume disponibilidad.
    - Aprobación humana: si el método requiere aprobación, se registra.
    - Evidencia explícita: cada transición registra la causa.
    - Sin secrets: no guarda claves, tokens ni credenciales.
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.verified_methods: dict[PaymentMethodType, PaymentMethodStatus] = {}

    # ── Métodos de verificación ─────────────────────────────────────────────

    def verify_method(self, method_type: PaymentMethodType) -> PaymentVerification:
        """
        Verificar un método de cobro.

        Luego verifica mediante documentación oficial y devuelve el estado.
        Si el método requiere aprobación humana, se registra.
        """
        method = get_payment_method(method_type)
        if method is None:
            return PaymentVerification(
                method_type=method_type,
                status=EligibilityStatus.UNSUPPORTED,
                verified=False,
                verification_notes="Método no reconocido en el registro canónico",
            )

        # Reutilizar la verificación individual mientras viva el adaptador.
        recorded_status = self.verified_methods.get(method_type)
        status = recorded_status.status if recorded_status else method.eligibility
        verified = recorded_status.verified if recorded_status else status == EligibilityStatus.VERIFIED
        if status in {EligibilityStatus.REQUIRES_HUMAN, EligibilityStatus.ACCOUNT_PENDING}:
            verification_notes = f"Requiere confirmación humana: {', '.join(method.requirements)}"
        elif verified:
            verification_notes = f"Confirmación registrada. {method.verification_notes}"
        else:
            verification_notes = f"Disponibilidad no confirmada ({status.value}). {method.verification_notes}"

        verification = PaymentVerification(
            method_type=method_type,
            status=status,
            verified=verified,
            verification_notes=verification_notes,
            evidence=recorded_status.evidence if recorded_status else {},
        )

        if recorded_status is None:
            self.verified_methods[method_type] = PaymentMethodStatus(method_type=method_type, status=status, verified=verified)

        return verification

    # ── Métodos de consulta ─────────────────────────────────────────────────

    def is_method_available(self, method_type: PaymentMethodType) -> bool:
        """
        Verificar si un método de cobro está disponible sin secretos.
        """
        verification = self.verify_method(method_type)
        return verification.verified

    def get_method_status(self, method_type: PaymentMethodType) -> PaymentMethodStatus | None:
        """
        Obtener el estado de un método de cobro.
        """
        return self.verified_methods.get(method_type)

    def get_verified_methods(self) -> list[PaymentMethodType]:
        """Obtener los métodos verificados."""
        return [m for m, s in self.verified_methods.items() if s.status == EligibilityStatus.VERIFIED]

    def get_all_statuses(self) -> list[PaymentMethodStatus]:
        """Obtener los estados de todos los métodos verificados."""
        return list(self.verified_methods.values())

    # ── Registro de estado ──────────────────────────────────────────────────

    def record_verification_result(
        self,
        method_type: PaymentMethodType,
        verified: bool,
        evidence: dict[str, Any],
    ) -> PaymentVerification:
        """
        Registrar el resultado de la verificación.

        Si el método no está verificado, se mantiene la evidencia.
        """
        method = get_payment_method(method_type)
        if method is None:
            return self.verify_method(method_type)
        if verified and not all(evidence.get(key) for key in ("source", "reference", "verified_by")):
            raise ValueError("Una verificación positiva requiere source, reference y verified_by")

        status = EligibilityStatus.VERIFIED if verified else EligibilityStatus.UNKNOWN
        safe_evidence = {key: str(evidence[key]) for key in ("source", "reference", "verified_by") if evidence.get(key)}
        verification = PaymentVerification(
            method_type=method_type,
            status=status,
            verified=verified,
            verification_notes=(
                f"Confirmación manual registrada por {safe_evidence['verified_by']}" if verified else "Elegibilidad no confirmada"
            ),
            evidence=safe_evidence,
            verification_date=datetime.now(UTC),
        )
        self.verified_methods[method_type] = PaymentMethodStatus(
            method_type=method_type,
            status=status,
            verified=verified,
            evidence=safe_evidence,
        )
        return verification


# Estado del adaptador de cobro (registro de estado del adapter)
class PaymentAdapterStatus(StrEnum):
    """Estado del adaptador de cobro."""

    VERIFIED = "verified"
    PENDING_VERIFICATION = "pending_verification"
    BLOCKED = "blocked"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


@dataclass
class PaymentVerification:
    """
    Resultado de la verificación de un método de cobro.

    Contiene lo que se verificó, el estado y la evidencia.
    """

    method_type: PaymentMethodType
    status: EligibilityStatus
    verified: bool
    verification_notes: str
    evidence: dict[str, Any] = field(default_factory=dict)
    verification_date: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "method_type": self.method_type.value,
            "status": self.status.value,
            "verified": self.verified,
            "verification_notes": self.verification_notes,
            "evidence": self.evidence,
            "verification_date": self.verification_date.isoformat(),
        }


@dataclass
class PaymentMethodStatus:
    """
    Estado de método de pago en el contexto del adaptador.

    Representa un método y su estado de elegibilidad.
    """

    method_type: PaymentMethodType
    status: EligibilityStatus
    verified: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method_type": self.method_type.value,
            "status": self.status.value,
            "verified": self.verified,
            "evidence": self.evidence,
        }
