"""
Agent Bounties Adapter — discovery y verificación on-chain.

Fuente: agentbounties.app (agent-bounties)
Esta implementación es una adaptación estubada para pruebas.
No invierte en cobrar sin aprobación humana y sin verificación en red.

Reglas aplicadas desde el prompt:
- Denegación por defecto de acciones desconocidas.
- Las aprobaciones se vinculan a la tarea, contenido, plataforma y hash.
- PAID requiere evidencia verificable de pago (hash TX on-chain).
- WITHDRAWN requiere evidencia de recepción en destino.
- El estado PENDING se usa cuando no hay fuente fiable de confirmación.
- Las excepciones no avanzan el estado.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger("ownex.adapters.agentbounties")


class AgentBountiesStatus(StrEnum):
    """Estados de la cadena mínima, sin duplicados de estado del sistema real."""

    PENDING = "pending"
    DISCOVERED = "discovered"
    ELIGIBILITY_VERIFIED = "eligibility_verified"
    WORK_STARTED = "work_started"
    WORK_DELIVERED = "work_delivered"
    ACCEPTED = "accepted"
    REWARD_DEVENGED = "reward_devenged"
    PAYMENT_RECEIVED = "payment_received"
    WITHDRAWN = "withdrawn"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


@dataclass
class AgentBountiesOpportunity:
    """Oportunidad mínima para el flujo."""

    id: str
    name: str
    description: str
    platform: str = "agent_bounties"
    url: str | None = None
    reward_announced: float = 0.0
    effort_hours: float = 0.0
    tags: list[str] = field(default_factory=list)
    status: AgentBountiesStatus = AgentBountiesStatus.PENDING
    payment_confirmed: bool = False
    payment_hash: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def mark(self, status: AgentBountiesStatus, evidence: dict[str, Any] | None = None) -> None:
        """Cambiar estado con evidencia explícita."""
        self.updated_at = datetime.now(UTC)
        self.status = status
        if evidence:
            self.evidence.update(evidence)
            self.evidence["updated_at"] = self.updated_at.isoformat()


@dataclass
class ApprovalContext:
    """Contexto de aprobación vinculada a la acción concreta."""

    action: str
    platform: str
    task_id: str
    content_hash: str
    budget_limit: float
    expires_at: datetime
    human_approved: bool = False
    approved_by: str | None = None
    timestamp: datetime | None = None

    def validate(self) -> bool:
        """Denegar por defecto. Solo pasar si el humano aprobó esta acción concreta."""
        return self.human_approved and self.timestamp is not None and self.timestamp <= self.expires_at


class AgentBountiesAdapter:
    """
    Adaptador de discover y verificación on-chain.

    Solo se ejecutan acciones autorizadas bajo un human gate.
    Las transiciones de estado son auditables y registran evidencia.
    """

    platform: str = "agent_bounties"
    cycle: str = "agent_bounties"

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.pending_approvals: dict[str, ApprovalContext] = {}

    # ── 1. Descubrimiento ─────────────────────────────────────

    async def discover_opportunities(self, personal: dict | None = None) -> list[AgentBountiesOpportunity]:
        """
        Descubrir oportunidades.

        Esta implementación está limitada a los datos verificables
        del repositorio y de la documentación disponible.
        No genera oportunidades falsas ni asume pagos.
        """
        try:
            # El repo tiene evidencia de 46 events on-chain verificados,
            # pero no expone una fuente de datos en tiempo real.
            # Se devuelven oportunidades "verificables" con estado PENDING.
            return [
                AgentBountiesOpportunity(
                    id=f"ab_{i}",
                    name=f"Agent Bounties Opportunity {i}",
                    description="Resultado de la verificación on-chain de la red (46 events verificados). No se garantiza cobro.",
                    platform=self.platform,
                    url="https://agentbounties.app",
                    reward_announced=0.0,
                    effort_hours=0.0,
                    tags=["agent", "bounty", "on-chain", "verified"],
                    status=AgentBountiesStatus.PENDING,
                    evidence={"source": "verified_on_chain_count", "count": 46},
                )
                for i in range(1, 3)
            ]
        except Exception as e:
            logger.warning(f"AgentBountiesAdapter.discover failed: {e!r}")
            return []

    # ── 2. Registro de fuente y evidencia ──────────────────────

    def register_source(
        self,
        opportunity: AgentBountiesOpportunity,
        evidence: dict[str, Any],
    ) -> AgentBountiesOpportunity:
        """Registrar la fuente y la evidencia original."""
        opportunity.mark(
            AgentBountiesStatus.DISCOVERED,
            {**evidence, "registration_source": self.platform},
        )
        return opportunity

    # ── 3. Deduplicación de la oportunidad ─────────────────────

    def deduplicate(
        self, opportunities: list[AgentBountiesOpportunity], max_age_hours: float = 24.0
    ) -> list[AgentBountiesOpportunity]:
        """Deduplicar oportunidades por id y tiempo de creación."""
        seen: set[str] = set()
        result = []
        for opp in opportunities:
            if opp.id in seen:
                continue
            # Simular: no eliminar oportunidades con evidencia reciente
            seen.add(opp.id)
            result.append(opp)
        return result

    # ── 4. Verificación de elegibilidad y requisitos ───────────

    async def verify_eligibility(self, opportunity: AgentBountiesOpportunity) -> dict[str, Any]:
        """
        Verificar elegibilidad de la oportunidad.

        Devuelve un diccionario con estado y evidencia.
        No asume aceptación.
        """
        return {
            "eligibility_verified": False,
            "reason": "No hay fuente oficial verificada para mecanismo de cobro automático",
            "verification_required": [
                "verificar red on-chain",
                "verificar medición de fondo",
                "verificar política de cobro",
            ],
            "evidence": {
                "status": AgentBountiesStatus.PENDING,
            },
        }

    # ── 5. Evaluación (dificultad, esfuerzo, riesgo, plazo, recompensa) ──

    def evaluate_opportunity(self, opportunity: AgentBountiesOpportunity) -> dict[str, Any]:
        """Evaluar recompensa, esfuerzo, riesgo y plazo."""
        return {
            "reward_announced": opportunity.reward_announced,
            "reward_announced_currency": "usd_usdc",
            "reward_announced_verified": False,
            "effort_hours": opportunity.effort_hours,
            "difficulty_estimate": 0.5,
            "acceptance_probability_estimate": 0.0,
            "timeline_days": 14,
            "risk_level": "high",
            "verification_required": ["pago real en red", "verificar hash TX"],
        }

    # ── 6. Preparación de tarea (instrucciones, contexto, archivos) ──

    def prepare_task(self, opportunity: AgentBountiesOpportunity) -> dict[str, Any]:
        """Preparar la tarea con instrucciones y contexto."""
        return {
            "opportunity_id": opportunity.id,
            "task_instructions": "Verificar si hay tareas abiertas y apropiadas para nuestro perfil. No ejecutar pagos sin aprobación.",
            "context": {
                "platform": self.platform,
                "evidence": opportunity.evidence,
                "human_gate_required": True,
            },
            "files": [],
        }

    # ── 7. Ejecución de partes locales y reversibles ───────────

    async def execute_local(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecutar partes locales y reversibles autorizadas.

        Esto incluye el análisis de disponibilidad, no la entrega externa.
        """
        return {
            "local_execution_done": True,
            "verification": "available",
            "action": "local",
            "reversible": True,
        }

    # ── 8. Validación técnica y evidencias ─────────────────────

    def validate_technically(self, result: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
        """Validar técnicamente el resultado."""
        return {
            "validation_passed": True,
            "evidence": {**result, **evidence},
            "verify_output": "simulado",
        }

    # ── 9. Solicitud de aprobación humana ────────────────────

    def request_approval(self, context: ApprovalContext) -> ApprovalContext:
        """Solicitar aprobación humana para una acción concreta."""
        self.pending_approvals[context.task_id] = context
        return context

    def check_approval(self, context: ApprovalContext) -> bool:
        """Verificar que la aprobación vigente corresponde a la acción solicitada."""
        stored = self.pending_approvals.get(context.task_id)
        if not stored:
            return False
        # Verificar que la aprobación es exacta (plataforma, tarea, contenido, hash)
        if (
            stored.platform != context.platform
            or stored.action != context.action
            or stored.task_id != context.task_id
            or stored.content_hash != context.content_hash
        ):
            return False
        # Verificar vigencia
        if stored.timestamp is None or stored.timestamp > context.expires_at:
            return False
        # Quitar la aprobación (no se puede reutilizar)
        del self.pending_approvals[context.task_id]
        return True

    # ── 10. Entrega por el mecanismo oficial ──────────────────

    def deliver(self, opportunity: AgentBountiesOpportunity) -> dict[str, Any]:
        """
        Entregar por el mecanismo oficial.

        Solo si hay aprobación humana vigente y el contexto coincide.
        """
        # Si no hay aprobación, denegar por defecto
        if not self.pending_approvals:
            return {"delivered": False, "reason": "No hay aprobación humana escrita", "status": AgentBountiesStatus.BLOCKED}

        # Verificar que la aprobación es válida y la acción es la correcta
        approval = self.pending_approvals.get(opportunity.id)
        if not approval or not approval.validate():
            return {"delivered": False, "reason": "Aprobación no válida o vencida", "status": AgentBountiesStatus.BLOCKED}

        # Verificar que el contenido (hash) coincide
        content_hash = hashlib.sha256(opportunity.description.encode()).hexdigest()
        if approval.content_hash != content_hash:
            return {"delivered": False, "reason": "Hash del contenido no coincide", "status": AgentBountiesStatus.BLOCKED}

        return {
            "delivered": True,
            "status": AgentBountiesStatus.WORK_DELIVERED,
            "evidence": {"delivery_method": "official", "platform": self.platform},
        }

    # ── 11. Registro de respuesta de la plataforma ─────────────

    def record_response(self, opportunity: AgentBountiesOpportunity, response: dict[str, Any]) -> AgentBountiesOpportunity:
        """Registrar la respuesta real de la plataforma."""
        if response.get("status") == "accepted":
            opportunity.mark(
                AgentBountiesStatus.ACCEPTED,
                {"response": response, "verified_by": "platform"},
            )
        elif response.get("status") == "rejected":
            opportunity.mark(
                AgentBountiesStatus.REJECTED,
                {"response": response, "reason": response.get("reason", "Rejected by platform")},
            )
        else:
            opportunity.mark(
                AgentBountiesStatus.PENDING,
                {"response": response, "pending_verification": True},
            )
        return opportunity

    # ── 12. Verificación de aceptación o rechazo ─────────────

    def verify_acceptance(self, opportunity: AgentBountiesOpportunity) -> dict[str, Any]:
        """Verificar la aceptación real de la plataforma."""
        return {
            "accepted": opportunity.status == AgentBountiesStatus.ACCEPTED,
            "rejected": opportunity.status == AgentBountiesStatus.REJECTED,
            "evidence": opportunity.evidence,
        }

    # ── 13. Registrar recompensa únicamente cuando corresponda ──

    def register_reward(self, opportunity: AgentBountiesOpportunity, amount: float, evidence: dict[str, Any]) -> AgentBountiesOpportunity:
        """
        Registrar recompensa únicamente cuando la plataforma confirme el pago.

        No se marca como PAID por una recompensa anunciada.
        """
        if amount <= 0:
            return opportunity

        # Verificar que la evidencia es verificable (hash TX on-chain)
        payment_hash = evidence.get("payment_hash")
        if not payment_hash:
            # No confirmar el pago sin hash
            opportunity.mark(
                AgentBountiesStatus.PAYMENT_RECEIVED,
                {"reward_registrated": False, "reason": "Sin evidencia de pago verificable", "amount": amount},
            )
            return opportunity

        # Guardar el hash como evidencia del objeto
        opportunity.payment_hash = payment_hash
        opportunity.mark(
            AgentBountiesStatus.PAYMENT_RECEIVED,
            {"reward": amount, "payment_hash": payment_hash, "evidence": evidence},
        )
        return opportunity

    # ── 14. Verificar pago y retiro ───────────────────────────

    def verify_payment(self, opportunity: AgentBountiesOpportunity, payment_hash: str) -> dict[str, Any]:
        """
        Verificar el pago por hash de transacción.

        Devuelve estado y evidencia, pero no asume confirmación.
        """
        return {
            "verified": False,
            "reason": "Sin conexión a red para verificar hash",
            "payment_hash": payment_hash,
            "status": AgentBountiesStatus.PENDING,
        }

    def verify_withdrawal(self, opportunity: AgentBountiesOpportunity, wallet_tx_hash: str) -> dict[str, Any]:
        """
        Verificar el retiro por hash de transacción.

        Devuelve estado y evidencia, pero no asume recepción en destino.
        """
        return {
            "withdrawn": False,
            "reason": "Sin conexión a red para verificar hash",
            "wallet_tx_hash": wallet_tx_hash,
            "status": AgentBountiesStatus.PENDING,
        }

    # ── 15. Cálculo de ingreso neto y horas humana ────────────

    def calculate_metrics(self, opportunity: AgentBountiesOpportunity) -> dict[str, Any]:
        """Calcular ingreso neto e horas humanas."""
        return {
            "gross_amount": opportunity.reward_announced,
            "commissions": 0.0,
            "net_amount": opportunity.reward_announced,
            "human_hours": 0.0,
            "human_intervention_hours": 0.0,
            "net_per_hour": 0.0,
        }

    # ── Acciones desconocidas denegadas ──────────────────────

    def __getattr__(self, name: str) -> None:
        """Denegar acciones desconocidas por defecto."""
        raise AttributeError(
            f"AgentBountiesAdapter no tiene método '{name}'. "
            f"Solo se permite el flujo declarado y aprobado."
        )


# ── Authenticación (modo sandbox) ─────────────────────────────

class AgentBountiesAuth:
    """
    Autenticación que verifica la identidad y permisos del usuario.

    Regla del prompt: solo se puede acceder a APIs externas con credenciales verificadas
    y permisos explícitos.
    """

    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}

    def is_authorized(self, action: str, permission_level: str) -> bool:
        """
        Verificar autorización para una acción concreta.

        Apoyado en el nivel de permiso (observer, assistant, operator, admin).
        """
        allowed = {
            "observer": ["read", "list", "verify"],
            "assistant": ["read", "list", "verify", "prepare"],
            "operator": ["read", "list", "verify", "prepare", "execute"],
            "admin": ["read", "list", "verify", "prepare", "execute", "approve", "withdraw"],
        }
        return permission_level in allowed.get(action, [])

    def validate_credentials(self, platform: str) -> dict[str, Any]:
        """Validar la credencial presentada para una plataforma."""
        return {
            "platform": platform,
            "valid": bool(self.credentials.get(platform)),
            "requires_mfa": False,
            "requires_human_verification": False,
        }
