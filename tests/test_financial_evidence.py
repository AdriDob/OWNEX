"""Evidence rules: no verified money without proof (weekly review P0)."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from cores.financial.truth_layer import ValueCategory, _withdrawal_has_evidence, classify_value
from cores.financial.withdrawal import (
    ConfirmationMethod,
    ProofAttachment,
    complete_withdrawal,
    create_withdrawal,
)
from cores.ledger import LedgerEvent


def _mk_withdrawal(**kw):
    return create_withdrawal(
        amount=100.0,
        currency="USD",
        platform="test_platform",
        target_account="bank-1",
        method="bank",
        **kw,
    )


class TestWithdrawalEvidence:
    def test_complete_without_evidence_rejected(self):
        w = _mk_withdrawal()
        assert complete_withdrawal(w.id, confirmation=ConfirmationMethod.MANUAL_PROOF) is None
        assert w.status.value != "completed"

    def test_complete_unconfirmed_rejected_even_with_hash(self):
        w = _mk_withdrawal()
        assert (
            complete_withdrawal(
                w.id,
                confirmation=ConfirmationMethod.UNCONFIRMED,
                tx_hash="0xabc",
            )
            is None
        )

    def test_complete_with_tx_hash_ok(self):
        w = _mk_withdrawal()
        done = complete_withdrawal(
            w.id,
            confirmation=ConfirmationMethod.MANUAL_PROOF,
            tx_hash="0xdeadbeef",
        )
        assert done is not None
        assert done.status.value == "completed"
        assert done.tx_hash == "0xdeadbeef"

    def test_complete_with_proof_ok(self):
        w = _mk_withdrawal()
        done = complete_withdrawal(
            w.id,
            confirmation=ConfirmationMethod.MANUAL_PROOF,
            proof=[ProofAttachment(type="screenshot", value="img-1")],
        )
        assert done is not None
        assert done.status.value == "completed"


class TestTruthLayerWithdrawalClassification:
    def _entry(self, **meta):
        return SimpleNamespace(
            source="withdrawal_tracker",
            event=LedgerEvent.WITHDRAWAL_COMPLETED,
            metadata=meta,
        )

    def test_unconfirmed_not_verified(self):
        assert not _withdrawal_has_evidence(self._entry(confirmation="unconfirmed"))

    def test_manual_proof_without_evidence_not_verified(self):
        assert not _withdrawal_has_evidence(self._entry(confirmation="manual_proof"))

    def test_tx_hash_counts_as_verified(self):
        assert _withdrawal_has_evidence(self._entry(confirmation="manual_proof", tx_hash="0x1", has_proof=False))

    def test_proof_counts_as_verified(self):
        assert _withdrawal_has_evidence(self._entry(confirmation="manual_proof", has_proof=True))

    def test_event_map_still_verified_real_for_other_flows(self):
        # classify_value itself is unchanged; the downgrade happens in
        # TruthLayer.get_state via _withdrawal_has_evidence.
        assert classify_value("external_api", LedgerEvent.PAYOUT_RECEIVED) == ValueCategory.VERIFIED_REAL


class TestQueueTransitionEvidenceGate:
    @pytest.fixture()
    def item(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OWNEX_EXECUTION_QUEUE_PATH", str(tmp_path / "q.json"))
        from core.execution_queue.models import ExecutionQueueStore

        store = ExecutionQueueStore()
        store.add("exec-test1", {"kind": "coder"})
        return "exec-test1"

    @pytest.mark.parametrize("target", ["executing", "submitted", "verification", "paid"])
    def test_manual_transition_to_evidence_gated_state_blocked(self, item, target):
        from api.routers.execution_queue import TransitionRequest, transition_item

        with pytest.raises(HTTPException) as exc:
            transition_item(item, TransitionRequest(target_state=target))
        assert exc.value.status_code == 400
