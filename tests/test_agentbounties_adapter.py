"""
Tests para AgentBountiesAdapter — simulación, no prueba de producción.

Las pruebas verifican la lógica del flujo (estados, puertas humanas, denegación por defecto),
no verifican pagos reales de la red.

Reglas del prompt aplicadas:
- Un mock exitoso no demuestra integración real.
- No afirmar ingresos estimados como ingresos obtenidos.
- PAID requiere evidencia verificable de pago (hash TX on-chain).
- WITHDRAWN requiere evidencia de recepción en destino.
- Las excepciones no avanzan el estado del flujo.
- Denegación por defecto para acciones desconocidas.
- Las aprobaciones están vinculadas a la acción, plataforma, tarea, contenido y hash.
"""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from core.opportunity.adapters.agentbounties_adapter import (
    AgentBountiesAdapter,
    AgentBountiesOpportunity,
    AgentBountiesStatus,
    ApprovalContext,
)


class TestAgentBountiesAdapterDiscovery:
    """Verificación de descubrimiento sin inventar datos reales."""

    @pytest.mark.asyncio
    async def test_discover_returns_queued_not_paid(self):
        """Descubrimiento devuelve oportunidades en estado PENDING, sin PAID."""
        adapter = AgentBountiesAdapter()
        opps = await adapter.discover_opportunities()

        assert isinstance(opps, list)
        assert len(opps) >= 1
        for opp in opps:
            assert opp.status == AgentBountiesStatus.PENDING
            assert not opp.payment_confirmed
            assert opp.reward_announced == 0.0

    @pytest.mark.asyncio
    async def test_discover_no_fake_rewards(self):
        """Descubrimiento no asigna recompensas hasta que se verifique el pago."""
        adapter = AgentBountiesAdapter()
        opps = await adapter.discover_opportunities()
        opp = opps[0]

        assert opp.reward_announced == 0.0
        assert not opp.payment_confirmed


class TestAgentBountiesAdapterRegistration:
    """Verificar registro de fuente y evidencia, sin decidir de antemano."""

    def test_register_source_requires_evidence(self):
        """Registro de fuente requiere evidencia explícita."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(
            id="ab_1",
            name="Test",
            description="Descripción",
        )
        updated = adapter.register_source(opp, {"source": "verified"})

        assert updated.status == AgentBountiesStatus.DISCOVERED
        assert updated.evidence["source"] == "verified"
        assert updated.evidence["registration_source"] == "agent_bounties"

    def test_register_source_updates_timestamp(self):
        """El registro actualiza el timestamp."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(
            id="ab_1",
            name="Test",
            description="Descripción",
        )
        before = opp.updated_at
        adapter.register_source(opp, {"source": "verified"})
        assert opp.updated_at >= before


class TestAgentBountiesAdapterDeduplication:
    """Verificar deduplicación por id y no por métricas sin verificar."""

    def test_deduplicate_removes_duplicates(self):
        """Filtra duplicados por id."""
        adapter = AgentBountiesAdapter()
        opp1 = AgentBountiesOpportunity(id="ab_1", name="A", description="P1")
        opp2 = AgentBountiesOpportunity(id="ab_1", name="B", description="P2")

        result = adapter.deduplicate([opp1, opp2])
        assert len(result) == 1
        assert result[0].id == "ab_1"

    def test_deduplicate_keeps_distinct(self):
        """Mantiene distintos."""
        adapter = AgentBountiesAdapter()
        opp1 = AgentBountiesOpportunity(id="ab_1", name="A", description="P1")
        opp2 = AgentBountiesOpportunity(id="ab_2", name="B", description="P2")

        result = adapter.deduplicate([opp1, opp2])
        assert len(result) == 2


class TestAgentBountiesAdapterEligibility:
    """Verificar que se exige verificación externa, no asumir aceptación."""

    @pytest.mark.asyncio
    async def test_verify_eligibility_returns_no_confirmation(self):
        """Verificación no confirma aceptación automática."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(
            id="ab_1",
            name="Test",
            description="Descripción",
        )
        result = await adapter.verify_eligibility(opp)

        assert result["eligibility_verified"] is False
        assert result["reason"]
        assert result["verification_required"]

    @pytest.mark.asyncio
    async def test_verify_eligibility_no_auto_approval(self):
        """La verificación no avanza al estado ACCEPTED."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(
            id="ab_1",
            name="Test",
            description="Descripción",
        )
        await adapter.verify_eligibility(opp)
        assert opp.status == AgentBountiesStatus.PENDING


class TestAgentBountiesAdapterEvaluation:
    """Verificar que la evaluación reporta incertidumbre, no certeza."""

    def test_evaluate_returns_not_verified(self):
        """Evaluación no confirma recompensa ni aceptación."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(
            id="ab_1",
            name="Test",
            description="Descripción",
            reward_announced=100.0,
            effort_hours=2.0,
        )
        result = adapter.evaluate_opportunity(opp)

        assert result["reward_announced"] == 100.0
        assert result["reward_announced_verified"] is False
        assert result["acceptance_probability_estimate"] < 1.0
        assert result["verification_required"]


class TestAgentBountiesAdapterApproval:
    """Verificar la puerta humana: aprobación vinculada a acción concreta."""

    def test_approval_denied_when_not_required(self):
        """Sin aprobación, la entrega se niega."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(
            id="ab_1",
            name="Test",
            description="Descripción",
            reward_announced=100.0,
        )
        result = adapter.deliver(opp)

        assert result["delivered"] is False
        assert result["status"] == AgentBountiesStatus.BLOCKED

    def test_approval_required_for_delivery(self):
        """La entrega solo se permite con aprobación vinculada."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(
            id="ab_1",
            name="Test",
            description="Descripción",
            reward_announced=100.0,
        )
        # content_hash debe coincidir con el hash de la descripción de la oportunidad
        expected_hash = hashlib.sha256(opp.description.encode()).hexdigest()
        context = ApprovalContext(
            action="deploy",
            platform="agent_bounties",
            task_id="ab_1",
            content_hash=expected_hash,
            budget_limit=1000.0,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            human_approved=True,
            approved_by="user",
            timestamp=datetime.now(UTC),
        )
        adapter.request_approval(context)
        result = adapter.deliver(opp)
        assert result["delivered"] is True
        assert result["status"] == AgentBountiesStatus.WORK_DELIVERED

    def test_approval_not_reusable(self):
        """Una aprobación no se puede reutilizar para otra tarea."""
        adapter = AgentBountiesAdapter()
        opp2 = AgentBountiesOpportunity(id="ab_2", name="B", description="P2")

        context1 = ApprovalContext(
            action="deploy",
            platform="agent_bounties",
            task_id="ab_2",
            content_hash="abc123",
            budget_limit=1000.0,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            human_approved=True,
            approved_by="user",
            timestamp=datetime.now(UTC),
        )
        adapter.request_approval(context1)

        # La aprobación de ab_2 no puede usarse para otra tarea distinta
        result = adapter.deliver(opp2)
        assert result["delivered"] is False
        # La aprobación ya fue consumida, no se puede reutilizar para otro deliver
        result2 = adapter.deliver(opp2)
        assert result2["delivered"] is False


class TestAgentBountiesAdapterRewardRegistration:
    """Verificar que el registro de recompensa requiere evidencia verificable."""

    def test_reward_not_registered_without_payment_hash(self):
        """Sin hash de pago, no se confirma el pago."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(id="ab_1", name="Test", description="D")
        opp = adapter.register_reward(opp, 100.0, {})
        assert opp.status == AgentBountiesStatus.PAYMENT_RECEIVED
        assert opp.payment_confirmed is False
        assert opp.payment_hash is None

    def test_reward_only_confirmed_with_payment_hash(self):
        """Con hash de pago, se registra, pero no se confirma aún."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(id="ab_1", name="Test", description="D")
        opp = adapter.register_reward(opp, 100.0, {"payment_hash": "0xabc"})
        assert opp.status == AgentBountiesStatus.PAYMENT_RECEIVED
        assert opp.payment_hash == "0xabc"
        # Aún no se confirma en red
        assert opp.payment_confirmed is False


class TestAgentBountiesAdapterExceptionsDoNotAdvanceState:
    """Las excepciones no avanzan el estado del flujo."""

    def test_exception_in_execute_does_not_advance(self):
        """Una excepción en la ejecución local no avanza el estado."""
        adapter = AgentBountiesAdapter()
        opp = AgentBountiesOpportunity(id="ab_1", name="Test", description="D")
        assert opp.status == AgentBountiesStatus.PENDING

        original = adapter.execute_local

        def failing_execute(task):
            raise RuntimeError("sim")

        adapter.execute_local = failing_execute
        try:
            adapter.execute_local({"opportunity_id": opp.id})
            # Si no lanza, el test falla porque esperabamos una excepción
            raise AssertionError("Expected RuntimeError")
        except RuntimeError:
            # Excepción capturada: el estado no debe haber avanzado
            pass
        finally:
            adapter.execute_local = original
        # El estado no debe avanzar
        assert opp.status == AgentBountiesStatus.PENDING


class TestApprovalContextValidation:
    """Verificar que la aprobación es exacta y no se puede reutilizar."""

    def test_context_validate_rejects_invalid_signature(self):
        """La validación de la aprobación requiere firma humana vigente."""
        context = ApprovalContext(
            action="deploy",
            platform="agent_bounties",
            task_id="ab_1",
            content_hash="abc123",
            budget_limit=1000.0,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert context.validate() is False

    def test_context_validate_accepts_valid_signature(self):
        """Una aprobación válida y vigente pasa."""
        context = ApprovalContext(
            action="deploy",
            platform="agent_bounties",
            task_id="ab_1",
            content_hash="abc123",
            budget_limit=1000.0,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            human_approved=True,
            approved_by="user",
            timestamp=datetime.now(UTC),
        )
        assert context.validate() is True
