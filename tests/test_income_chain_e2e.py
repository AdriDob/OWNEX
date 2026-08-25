"""E2E del ciclo de ingreso OWNEX (FEATURE COMPLETE gate, 2026-08-25).

Cadena completa sin servicios externos:
    discover → score/recommend → work bank (select+prepare)
    → human gate (approve) → revenue ledger (EXPECTED ≠ PENDING ≠ PAID).

Reglas verificadas:
- El dinero esperado jamás se cuenta como cobrado (completed_amount solo PAID).
- El human gate es obligatorio antes de la entrega (prepare no entrega).
- La proyección económica (OpportunityStage) y el ciclo canónico (ExecState)
  comparten la única tabla de conversión SSOT.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routers.direct_work import router as direct_work_router
from cores.direct_work_engine.discovery import BaseDiscoveryAdapter, DiscoverySource, UniversalDiscovery
from cores.direct_work_engine.models import Opportunity, OpportunityCategory, WorkPlatform
from cores.revenue_tracker.revenue_tracker import (
    BarrierType,
    PaymentMethod,
    PaymentPlatform,
    PaymentStatus,
    RevenueOpportunity,
    RevenueTracker,
)

app = FastAPI()
app.include_router(direct_work_router)
client = TestClient(app)


def _opp(**overrides) -> Opportunity:
    data = {
        "id": "e2e-1",
        "title": "Fix login rate-limit bypass",
        "platform": "opire",
        "category": "dev_bounty",
        "specialization": "backend",
        "remote": True,
        "payment": 120.0,
        "currency": "USD",
        "payment_method": "paypal",
        "payment_proven": True,
        "time_to_payout_days": 5,
    }
    data.update(overrides)
    return Opportunity(**data)


class _FakeAdapter(BaseDiscoveryAdapter):
    """Fuente determinista: cero red, cero flakiness."""

    def __init__(self, opportunities: list[Opportunity]) -> None:
        super().__init__(
            DiscoverySource(
                name="fake-e2e",
                platform=WorkPlatform.OPIRE,
                categories=[OpportunityCategory.DEV_BOUNTY],
                enabled=True,
                tier=1,
            )
        )
        self._items = opportunities

    async def fetch_opportunities(self) -> list[Opportunity]:
        return list(self._items)

    async def validate_connection(self) -> bool:
        return True


def _val(x) -> str:
    """Enum-aware serializer (patrón del router)."""
    return str(getattr(x, "value", x))


class TestIncomeChainE2E:
    def test_full_chain_discover_to_revenue(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # ── 1. DISCOVERY (adapter fake registrado en el discovery real) ──
        discovery = UniversalDiscovery()
        discovery.register_adapter(_FakeAdapter([_opp(id="e2e-1"), _opp(id="e2e-2", payment=80.0)]))
        found = asyncio.run(discovery.discover_all())
        assert len(found) == 2

        # ── 2. SCORE + RANK + RECOMMENDATION vía API real ──
        resp = client.post(
            "/direct-work/recommend",
            json={
                "opportunities": [
                    {
                        "id": o.id,
                        "title": o.title,
                        "platform": _val(o.platform),
                        "category": _val(o.category),
                        "specialization": _val(o.specialization),
                        "remote": o.remote,
                        "payment": o.payment,
                        "currency": o.currency,
                        "payment_method": _val(o.payment_method),
                        "payment_proven": o.payment_proven,
                    }
                    for o in found
                ],
                "profile": {"name": "Adriel", "country": "Argentina", "skills": ["python"]},
                "limit": 5,
            },
        )
        assert resp.status_code == 200
        ranked = resp.json()["ranked"]
        assert ranked, "el recommender debe producir un ranking"

        # ── 3. WORK BANK: select + prepare (ciclo real con store tmp) ──
        from cores.direct_work_engine.workbank import WorkBank

        bank = WorkBank(tmp_path / "workbank.json")
        monkeypatch.setattr("api.routers.direct_work.get_workbank", lambda: bank)
        summary = bank.daily_cycle(found, target=1)
        assert summary["ready_to_deliver"] >= 1

        ready = client.get("/direct-work/deliver/pending")
        assert ready.status_code == 200
        pending_ids = {i["id"] for i in ready.json()["items"]}
        assert "e2e-1" in pending_ids or "e2e-2" in pending_ids
        target_id = "e2e-1" if "e2e-1" in pending_ids else "e2e-2"

        # ── 4/5. HUMAN GATE: preparar genera paquete pero NO entrega ──
        prep = client.post(f"/direct-work/workbank/{target_id}/deliver/prepare")
        assert prep.status_code == 200
        assert prep.json()["package_path"]
        prepared_item = bank.get_item(target_id)
        assert prepared_item is not None and prepared_item.status != "delivered"

        approved = client.post(f"/direct-work/workbank/{target_id}/deliver/approve")
        assert approved.status_code == 200
        assert approved.json()["status"] == "delivered"
        delivered_item = bank.get_item(target_id)
        assert delivered_item is not None and delivered_item.ready_to_deliver is False

        # ── 6. REVENUE LEDGER: EXPECTED ≠ PENDING ≠ PAID ──
        tracker = RevenueTracker()
        tracker.add_payment_method(
            PaymentMethod(platform=PaymentPlatform.PAYPAL, account_id="pm-paypal", name="PayPal", currency="USD")
        )
        reward = Decimal("120.00")
        tracker.create_opportunity(
            RevenueOpportunity(
                id=target_id,
                platform="opire",
                title="Fix login rate-limit bypass",
                description="e2e",
                amount=reward,
                currency="USD",
                status=PaymentStatus.PENDING,
                barriers=[BarrierType.NONE],
                success_rate=0.6,
            )
        )
        # EXPECTED (potencial) nunca iguala al monto nominal ni al cobrado
        expected = tracker.get_total_potential_earnings()
        assert expected == reward * Decimal("0.6")

        # Gate del ledger: solo se registra un cobro de algo en revisión
        # (submission ya entregada y aceptada a revisión por la plataforma).
        assert tracker.update_opportunity_status(target_id, PaymentStatus.REVIEWING)

        # Cobro real: transacción PENDING → oportunidad REVIEWING → PAID
        tx = tracker.process_payment(target_id, PaymentPlatform.PAYPAL, "pm-paypal", reward, "USD")
        assert tx is not None and tx.status == PaymentStatus.PENDING
        metrics_before = tracker.get_platform_metrics("opire")
        assert metrics_before is not None
        assert metrics_before.completed_amount == Decimal("0")

        assert tracker.update_opportunity_status(target_id, PaymentStatus.PAID)
        metrics_after = tracker.get_platform_metrics("opire")
        assert metrics_after is not None
        assert metrics_after.completed_amount == reward
        assert metrics_after.pending_amount == Decimal("0")
        assert metrics_after.total_amount >= metrics_after.completed_amount

    def test_exec_state_to_stage_bridge_is_lossless_forward(self) -> None:
        from core.execution_queue import ExecState
        from cores.revenue_tracker.revenue_tracker import stage_from_exec_state

        # Dinero solo existe en PAID; bloqueo/fallo/dead-letter son REJECTED ($0).
        assert stage_from_exec_state(ExecState.DISCOVERED).value == "discovered"
        assert stage_from_exec_state(ExecState.WAITING_HUMAN).value == "in_progress"
        assert stage_from_exec_state(ExecState.SUBMITTED).value == "submitted"
        assert stage_from_exec_state(ExecState.VERIFICATION).value == "submitted"
        assert stage_from_exec_state(ExecState.PAID).value == "paid"
        for loss in (ExecState.REJECTED, ExecState.BLOCKED, ExecState.FAILED, ExecState.DEAD_LETTER):
            assert stage_from_exec_state(loss).value == "rejected"

        # Unknown honesto: jamás inventa etapa.
        assert stage_from_exec_state("estado-fantasma").value == "discovered"

    def test_paid_only_via_verification_transition(self) -> None:
        from core.execution_queue import ExecState, ExecutionQueueStore, assert_transition

        with pytest.raises(ValueError):
            assert_transition(ExecState.SUBMITTED, ExecState.PAID)

        store = ExecutionQueueStore(Path(__file__).parent / "_tmp_eq_e2e.json")
        try:
            store.add("item-x")
            store.transition("item-x", ExecState.QUALIFIED)
            with pytest.raises(ValueError):
                store.transition("item-x", ExecState.PAID)  # atajo prohibido
            store.transition("item-x", ExecState.READY)
            store.transition("item-x", ExecState.QUEUED)
            store.transition("item-x", ExecState.EXECUTING)
            store.transition("item-x", ExecState.WAITING_HUMAN)
            store.transition("item-x", ExecState.SUBMITTED)
            store.transition("item-x", ExecState.VERIFICATION)
            item = store.transition("item-x", ExecState.PAID)
            assert item["state"] == ExecState.PAID.value
            assert item["history"][-1] == ExecState.PAID.value
        finally:
            (Path(__file__).parent / "_tmp_eq_e2e.json").unlink(missing_ok=True)
