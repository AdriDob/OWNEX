"""Execution Mirror — puente WorkBank ↔ ExecutionQueue ↔ Pago (Parte 2, FINAL RELEASE).

Verifica la integración cerrada:
    prepare (paquete)  → QUEUED
    approve (human gate) → SUBMITTED (cadena completa, idempotente)
    pago confirmado     → VERIFICATION→PAID (+ evento payout)
    pago rechazado      → VERIFICATION→REJECTED
    sin confirmación    → SUBMITTED estable (honestidad económica)

El espejo es best-effort: NUNCA rompe el flujo del Work Bank.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.execution_queue import ExecState, ExecutionQueueStore
from core.execution_queue.mirror import (
    mirror_payment_result,
    mirror_workbank_approved,
    mirror_workbank_packaged,
    mirror_workbank_prepared,
)


@pytest.fixture()
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ExecutionQueueStore:
    s = ExecutionQueueStore(tmp_path / "mirror_queue.json")
    monkeypatch.setattr("core.execution_queue.mirror._get_store", lambda: s)
    return s


class TestWorkBankMirrorLifecycle:
    def test_prepare_then_approve_reaches_submitted(self, store: ExecutionQueueStore) -> None:
        mirror_workbank_prepared("wb-1", {"source": "workbank", "reward": 120})
        assert store.get("wb-1")["state"] == ExecState.READY.value

        mirror_workbank_packaged("wb-1")
        assert store.get("wb-1")["state"] == ExecState.QUEUED.value

        mirror_workbank_approved("wb-1")
        assert store.get("wb-1")["state"] == ExecState.SUBMITTED.value

    def test_paid_only_via_verification(self, store: ExecutionQueueStore) -> None:
        mirror_workbank_prepared("wb-2", {})
        mirror_workbank_packaged("wb-2")
        mirror_workbank_approved("wb-2")

        mirror_payment_result("wb-2", paid=True, amount=120.0)
        item = store.get("wb-2")
        assert item["state"] == ExecState.PAID.value
        assert "verification" in item["history"], "PAID debe pasar por VERIFICATION"

    def test_rejected_payment_lands_failed(self, store: ExecutionQueueStore) -> None:
        """Pago rechazado: la máquina canónica solo permite VERIFICATION→FAILED
        (FAILED proyecta a Stage.REJECTED $0 vía stage_from_exec_state)."""
        mirror_workbank_prepared("wb-3", {})
        mirror_workbank_packaged("wb-3")
        mirror_workbank_approved("wb-3")

        mirror_payment_result("wb-3", paid=False)
        assert store.get("wb-3")["state"] == ExecState.FAILED.value

    def test_no_confirmation_keeps_submitted_honest(self, store: ExecutionQueueStore) -> None:
        """Sin confirmación de pago NO se avanza (dinero solo en PAID)."""
        mirror_workbank_prepared("wb-4", {})
        mirror_workbank_approved("wb-4")  # salta packaged (flujo legacy)
        before = store.get("wb-4")["state"]
        assert before == ExecState.SUBMITTED.value

        # Sin llamada a mirror_payment_result: el estado no cambia solo.
        assert store.get("wb-4")["state"] == ExecState.SUBMITTED.value


class TestMirrorIdempotencyAndSafety:
    def test_double_approve_is_noop(self, store: ExecutionQueueStore) -> None:
        mirror_workbank_prepared("idem-1", {})
        mirror_workbank_packaged("idem-1")
        mirror_workbank_approved("idem-1")
        history_len = len(store.get("idem-1")["history"])

        mirror_workbank_approved("idem-1")  # re-aplicar
        assert store.get("idem-1")["state"] == ExecState.SUBMITTED.value
        assert len(store.get("idem-1")["history"]) == history_len  # sin duplicados

    def test_unknown_item_payment_does_not_raise(self, store: ExecutionQueueStore) -> None:
        mirror_payment_result("fantasma", paid=True)  # no existe → log + return

    def test_mirror_never_raises_on_broken_store(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        class _Broken:
            def get(self, _):
                raise RuntimeError("boom")

            def add(self, *_):
                raise RuntimeError("boom")

        monkeypatch.setattr("core.execution_queue.mirror._get_store", lambda: _Broken())
        # Ninguna llamada debe propagar la excepción (best-effort contract).
        mirror_workbank_prepared("x", {})
        mirror_workbank_packaged("x")
        mirror_workbank_approved("x")
        mirror_payment_result("x", paid=True)


class TestRouterWiring:
    def test_deliver_endpoints_drive_queue_states(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routers.direct_work import router as dw_router
        from cores.direct_work_engine.workbank import WorkBank

        bank = WorkBank(tmp_path / "wb.json")
        monkeypatch.setattr("api.routers.direct_work.get_workbank", lambda: bank)
        queue = ExecutionQueueStore(tmp_path / "q.json")
        monkeypatch.setattr("core.execution_queue.mirror._get_store", lambda: queue)

        app = FastAPI()
        app.include_router(dw_router)
        client = TestClient(app)

        from tests.test_income_chain_e2e import _opp

        summary = bank.daily_cycle([_opp(id="wire-1", payment=90.0)], target=1)
        assert summary["ready_to_deliver"] >= 1

        prep = client.post("/direct-work/workbank/wire-1/deliver/prepare")
        assert prep.status_code == 200
        assert queue.get("wire-1") is not None, "prepare debe espejar al queue"
        assert queue.get("wire-1")["state"] in (
            ExecState.QUEUED.value,
            ExecState.READY.value,
        )

        done = client.post("/direct-work/workbank/wire-1/deliver/approve")
        assert done.status_code == 200
        assert queue.get("wire-1")["state"] == ExecState.SUBMITTED.value
