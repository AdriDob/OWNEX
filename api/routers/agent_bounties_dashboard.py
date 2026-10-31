"""
API Router for Agent Bounties Pilot Dashboard.

Exposed to the user for monitoring, approval, and control of the pilot.

States exposed:
- PENDING: No disponible sin credenciales.
- DISCOVERED: Oportunidad registrada.
- VERIFICATION: Pago registrado, esperando verificación en red.
- PAID: Pago verificado en cadena.
- WITHDRAWN: Retiro confirmado en destino.
- BLOCKED: Requiere intervención humana o recursos externos.

Not exposed:
- Comandos de pago reales.
- Verificación en red (requiere conexión a red y keys).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from core.opportunity.payment_trail import (
    OpportunityTrail,
    PaymentState,
    SourceRegistry,
    get_all_trails,
    get_trail,
    register_trail,
)

router = APIRouter(prefix="/agent-bounties", tags=["agent-bounties-pilot"])


# ── Estado inicial del piloto (sin credenciales) ───────────────────────────────


def _get_initial_trail() -> OpportunityTrail:
    """Obtener la traza inicial del piloto, sin credenciales y sin datos externos."""
    trail = OpportunityTrail(
        opportunity_id="ab_pilot_001",
        name="Agent Bounties Pilot — Estado inicial",
        platform="agent_bounties",
        url="https://agentbounties.app",
        reward_announced=0.0,
        reward_confirmed=0.0,
        effort_hours=0.0,
        status=PaymentState.PENDING,
        evidence={
            "source_verified": False,
            "reason": "Pendiente de credenciales y API verificada",
            "verification_required": [
                "obtener API key de agentbounties.app",
                "verificar conexión a red",
                "verificar política de automatización",
                "verificar elegibilidad desde Argentina",
                "obtener aprobación humana",
            ],
            "expected_next_action": "el usuario configura la fuente y autoriza la verificación",
        },
    )
    register_trail(trail.opportunity_id, trail)
    return trail


# ── Estado actual ─────────────────────────────────────────────────────────────


@router.get("/status")
async def get_pilot_status() -> dict[str, Any]:
    """
    Estado actual del piloto.

    Solo expone:
    - Ubicación del estado.
    - Lo que falta para avanzar.
    - Lo que requiere intervención del usuario.
    - Evidencia disponible.

    No expone comandos de pago reales, solo el estado del flujo.
    """
    trail = get_trail("ab_pilot_001")
    if trail is None:
        trail = _get_initial_trail()

    return {
        "success": True,
        "pilot_id": trail.opportunity_id,
        "status": trail.status,
        "updated_at": trail.updated_at.isoformat(),
        "reward_announced": trail.reward_announced,
        "reward_confirmed": trail.reward_confirmed,
        "evidence_required": trail.evidence.get("verification_required", []),
        "human_approval_required": trail.status
        in {
            PaymentState.WAITING_HUMAN,
            PaymentState.VERIFICATION,
            PaymentState.PAID,
            PaymentState.WITHDRAWN,
        },
        "human_approved": trail.human_approved,
        "human_approved_by": trail.human_approved_by,
        "pending_actions": _get_pending_actions(trail),
        "next_action": _get_next_action(trail),
        "next_action_explanation": _get_next_action_explanation(trail),
        "evidence": trail.evidence,
    }


def _get_pending_actions(trail: OpportunityTrail) -> list[str]:
    """Acciones pendientes para avanzar."""
    actions: list[str] = []
    if trail.status == PaymentState.PENDING:
        actions.append("Configurar API key de agentbounties.app y credenciales")
        actions.append("Verificar conexión a red y reducir rama de acceso")
        actions.append("Obtener aprobación humana para iniciar la verificación")
    elif trail.status == PaymentState.DISCOVERED:
        actions.append("Registrar evidencia de descubrimiento")
        actions.append("Verificar requisitos de elegibilidad")
    elif trail.status == PaymentState.VERIFICATION:
        actions.append("Verificar hash de pago en red")
        actions.append("Confirmar estado de verificación")
    elif trail.status == PaymentState.PAID:
        actions.append("Registrar retiro al destino")
        actions.append("Verificar recepción del retiro")
    return actions


def _get_next_action(trail: OpportunityTrail) -> str | None:
    """Acción siguiente del flujo, según estado."""
    if trail.status == PaymentState.PENDING:
        return "Configurar fuente y requisitos de acceso"
    elif trail.status == PaymentState.DISCOVERED:
        return "Verificar elegibilidad de la oportunidad"
    elif trail.status == PaymentState.WAITING_HUMAN:
        return "Esperar aprobación humana"
    elif trail.status == PaymentState.SUBMITTED:
        return "Verificar respuesta de la plataforma"
    elif trail.status == PaymentState.VERIFICATION:
        return "Verificar pago en red"
    elif trail.status == PaymentState.PAID:
        return "Registrar retiro y confirmar recepción"
    return None


def _get_next_action_explanation(trail: OpportunityTrail) -> str:
    """Explicación de la acción siguiente."""
    if trail.status == PaymentState.PENDING:
        return "El piloto está en estado PENDING. No hay credenciales ni API verificadas. Requiere configuración del usuario."
    elif trail.status == PaymentState.DISCOVERED:
        return "Oportunidad registrada. Verificar requisitos de elegibilidad antes de continuar."
    elif trail.status == PaymentState.WAITING_HUMAN:
        return "Esperando aprobación humana para continuar."
    return "No hay acción pendiente. El flujo está completado o en estado terminal."


# ── Estado y evidencia del flujo ──────────────────────────────────────────────


@router.get("/trail/{opportunity_id}")
async def get_trail_status(opportunity_id: str) -> dict[str, Any]:
    """
    Estado y evidencia del flujo para una oportunidad específica.

    Solo expone lo que se puede verificar sin acciones externas.
    """
    trail = get_trail(opportunity_id)
    if trail is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    return {
        "success": True,
        "opportunity_id": trail.opportunity_id,
        "current_state": trail.status,
        "updated_at": trail.updated_at.isoformat(),
        "reward_confirmed": trail.reward_confirmed,
        "payment_hash": trail.payment_hash,
        "payment_verified": trail.payment_verified,
        "withdrawal_confirmed": trail.withdrawal_confirmed,
        "evidence": trail.evidence,
        "human_approved": trail.human_approved,
    }


# ── Listado de oportunidades ───────────────────────────────────────────────────


@router.get("/opportunities")
async def list_pilot_opportunities() -> dict[str, Any]:
    """
    Listar las oportunidades registradas en el piloto.

    Solo expone las oportunidades registradas.
    """
    trails = get_all_trails()
    return {
        "success": True,
        "count": len(trails),
        "opportunities": [
            {
                "opportunity_id": t.opportunity_id,
                "name": t.name,
                "platform": t.platform,
                "status": t.status,
                "reward_announced": t.reward_announced,
                "reward_confirmed": t.reward_confirmed,
                "updated_at": t.updated_at.isoformat(),
            }
            for t in trails
        ],
    }


# ── Registro manual de estado (para el usuario) ───────────────────────────────


@router.post("/trail/{opportunity_id}/status")
async def update_trail_status(opportunity_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Registrar estado manualmente con evidencia.

    Solo es called por el usuario o por agente con aprobación humana vigente.
    """
    from core.opportunity.payment_trail import PaymentState, transition

    trail = get_trail(opportunity_id)
    if trail is None:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    next_state = payload.get("status")
    if next_state is None:
        raise HTTPException(status_code=400, detail="Falta el campo 'status'")

    try:
        next_state_enum = PaymentState(next_state)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Estado inválido: {next_state}"
        ) from None

    evidence = payload.get("evidence", {})
    transition(trail, next_state_enum, evidence)

    return {
        "success": True,
        "opportunity_id": trail.opportunity_id,
        "previous_state": trail.status,
        "new_state": trail.status,
        "updated_at": trail.updated_at.isoformat(),
        "evidence": trail.evidence,
    }


# ── Registro de fuentes priorizadas ───────────────────────────────────────────


@router.get("/sources")
async def list_sources() -> dict[str, Any]:
    """
    Listar las fuentes priorizadas con el estado de verificación actual.

    Util para el Daily Brief y el monitoreo del piloto.
    """
    summary = SourceRegistry.get_status_summary()
    return {
        "success": True,
        "sources": summary["sources"],
        "total_sources": summary["total_sources"],
        "sources_with_payout_eligibility_verified": summary["sources_with_payout_eligibility_verified"],
        "sources_blocked_by_country": summary["sources_blocked_by_country"],
        "sources_blocked_by_no_work": summary["sources_blocked_by_no_work"],
        "sources_unverified": summary["sources_unverified"],
    }


@router.get("/sources/{source_slug}/status")
async def get_source_status(source_slug: str) -> dict[str, Any]:
    """
    Estado de verificación de una fuente concreta.

    Expone:
    - Estado de integración técnica.
    - Estado de trabajo disponible.
    - Método de pago.
    - Estado de elegibilidad.
    - Notas de verificación.
    """
    found = SourceRegistry.find_by_source(source_slug)
    if not found:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    slug, name, state = found
    return {
        "success": True,
        "slug": slug,
        "name": name,
        "status": state["status"],
        "priority": state["priority"],
        "verification_notes": state["verification_notes"],
        "expected_first_paid": state["expected_first_paid"],
        "time_to_first_paid": state["time_to_first_paid"],
        "payout_country_supported": state["payout_country_supported"],
        "work_available": state["work_available"],
        "payment_method": state["payment_method"],
        "integration_technical": state["integration_technical"],
    }


# ── Daily Brief del piloto ────────────────────────────────────────────────────


@router.get("/daily-brief")
async def get_daily_brief() -> dict[str, Any]:
    """
    Daily Brief del piloto: estado actual, fuentes priorizadas, bloqueos,
    costos, próximos pasos permitidos y pruebas ejecutadas.

    No expone claves ni presenta resultados sin evidencia de una fuente conectada.
    """
    summary = SourceRegistry.get_status_summary()
    return {
        "success": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "pilot_id": "ab_pilot_001",
        "overview": {
            "total_sources": summary["total_sources"],
            "sources_with_payout_eligibility_verified": summary["sources_with_payout_eligibility_verified"],
            "sources_blocked_by_country": summary["sources_blocked_by_country"],
            "sources_blocked_by_no_work": summary["sources_blocked_by_no_work"],
            "sources_unverified": summary["sources_unverified"],
        },
        "sources": summary["sources"],
        "daily_brief_confirmed": [],
        "protocols": [],
        "criterio_exito": [
            "Fuente verificada y oportunidad elegible identificada",
            "Primera traza registrada",
            "Bloqueo documentado si no hay tarea válida",
            "No se exige PAID para cerrar el día",
            "Prohibido simular actividad o ingresos para cumplir el objetivo",
        ],
        "costos_incurridos": [],
        "próximos_pasos_permitidos": [
            "Conectar una fuente autorizada y consultar oportunidades vigentes",
            "Verificar recompensa, condiciones, actividad del repo y vía de pago",
            "Revisar requisitos de pago y elegibilidad",
            "Solicitar aprobación humana antes de cualquier acción externa",
        ],
        "evidencias": [],
        "pruebas_ejecutadas": [],
    }
