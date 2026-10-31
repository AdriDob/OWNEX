"""
API Router for Payment Methods — métodos de pago disponibles para el piloto.

Expone el registro de métodos de cobro sin secretos, con estado verificable.
No permite ninguna acción externa que requiera credenciales.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from core.opportunity.adapters.payment_adapter import (
    PaymentAdapter,
)
from core.opportunity.payment_methods import (
    PaymentMethodType,
    get_payment_method,
    get_payment_methods,
)

router = APIRouter(prefix="/payment-methods", tags=["payment-methods"])


# ── Instancia del adaptador ────────────────────────────────────────────────────

_payment_adapter = PaymentAdapter(config={})


# ── Métodos de pago disponibles ──────────────────────────────────────────────

@router.get("/")
async def list_payment_methods() -> dict[str, Any]:
    """
    Listar todos los métodos de pago registrados.

    Sin secretos. Solo métodos verificados y su estado.
    """
    methods = get_payment_methods()
    return {
        "success": True,
        "count": len(methods),
        "methods": [m.to_dict() for m in methods],
    }


@router.get("/{method_type}")
async def get_payment_method_details(method_type: str) -> dict[str, Any]:
    """
    Detalles de un método de pago específico.

    Sin secretos. Solo verifica disponibilidad y estado.
    """
    try:
        method_type_enum = PaymentMethodType(method_type)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Método de pago no reconocido: {method_type}",
        ) from None

    method = get_payment_method(method_type_enum)
    if method is None:
        raise HTTPException(
            status_code=404,
            detail=f"Método de pago no encontrado: {method_type}",
        )

    # Actualizar estado del adaptador (sin credenciales)
    adapter = _payment_adapter
    verification = adapter.verify_method(method_type_enum)

    return {
        "success": True,
        "method_type": method_type_enum.value,
        "name": method.name,
        "provider": method.provider,
        "description": method.description,
        "payout_currency": method.payout_currency,
        "min_amount": method.min_amount,
        "max_amount": method.max_amount,
        "fees": method.fees,
        "eligibility": method.eligibility.value,
        "requirements": method.requirements,
        "verification_notes": method.verification_notes,
        "verified_at": method.verified_at.isoformat() if method.verified_at else None,
        "created_at": method.created_at.isoformat(),
        "updated_at": method.updated_at.isoformat(),
        "adapter_status": verification.status.value,
        "adapter_verified": verification.verified,
        "adapter_notes": verification.verification_notes,
    }


@router.get("/status")
async def get_payment_methods_status() -> dict[str, Any]:
    """
    Estado de los métodos de pago disponibles para el usuario.

    Sin secretos. Solo verifica disponibilidad y estado.
    """
    adapter = _payment_adapter
    return {
        "success": True,
        "verified_methods": adapter.get_verified_methods(),
        "all_statuses": [s.status.value for s in adapter.get_all_statuses()],
        "total_methods": len(get_payment_methods()),
        "verified_count": len(adapter.get_verified_methods()),
        "verified_percentage": round(
            len(adapter.get_verified_methods()) / max(len(get_payment_methods()), 1) * 100, 1
        ),
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
    }
