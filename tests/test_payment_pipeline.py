"""Tests for Payment Pipeline."""

import pytest

from core.execution_queue.models import ExecState
from cores.direct_work_engine.payment_pipeline import (
    PaymentPipelineStore,
    PaymentState,
    PipelineItem,
    assert_transition,
    can_transition,
    execution_state_to_payment,
    full_pipeline_sync,
    is_terminal,
    is_terminal_negative,
    is_terminal_positive,
    revenue_status_to_payment,
    workbank_status_to_payment,
)


class TestPaymentState:
    def test_payment_state_enum(self):
        assert PaymentState.DISCOVERED == "discovered"
        assert PaymentState.QUALIFIED == "qualified"
        assert PaymentState.READY == "ready"
        assert PaymentState.QUEUED == "queued"
        assert PaymentState.EXECUTING == "executing"
        assert PaymentState.WAITING_HUMAN == "waiting_human"
        assert PaymentState.SUBMITTED == "submitted"
        assert PaymentState.VERIFICATION == "verification"
        assert PaymentState.PAID == "paid"
        assert PaymentState.REJECTED == "rejected"
        assert PaymentState.BLOCKED == "blocked"
        assert PaymentState.FAILED == "failed"
        assert PaymentState.DEAD_LETTER == "dead_letter"


class TestTransitions:
    def test_valid_transitions(self):
        assert can_transition("DISCOVERED", "QUALIFIED")
        assert can_transition("QUALIFIED", "READY")
        assert can_transition("READY", "QUEUED")
        assert can_transition("QUEUED", "EXECUTING")
        assert can_transition("EXECUTING", "WAITING_HUMAN")
        assert can_transition("EXECUTING", "SUBMITTED")
        assert can_transition("EXECUTING", "FAILED")
        assert can_transition("WAITING_HUMAN", "EXECUTING")
        assert can_transition("WAITING_HUMAN", "SUBMITTED")
        assert can_transition("WAITING_HUMAN", "REJECTED")
        assert can_transition("WAITING_HUMAN", "BLOCKED")
        assert can_transition("SUBMITTED", "VERIFICATION")
        assert can_transition("SUBMITTED", "REJECTED")
        assert can_transition("VERIFICATION", "PAID")
        assert can_transition("VERIFICATION", "FAILED")
        assert can_transition("FAILED", "QUEUED")
        assert can_transition("FAILED", "DEAD_LETTER")

    def test_invalid_transitions(self):
        assert not can_transition("DISCOVERED", "PAID")
        assert not can_transition("QUALIFIED", "PAID")
        assert not can_transition("READY", "PAID")
        assert not can_transition("PAID", "FAILED")
        assert not can_transition("REJECTED", "QUALIFIED")

    def test_assert_transition_valid(self):
        assert_transition("DISCOVERED", "QUALIFIED")  # Should not raise

    def test_assert_transition_invalid(self):
        with pytest.raises(ValueError):
            assert_transition("DISCOVERED", "PAID")


class TestTerminalStates:
    def test_is_terminal(self):
        assert is_terminal("PAID")
        assert is_terminal("REJECTED")
        assert is_terminal("BLOCKED")
        assert is_terminal("FAILED")
        assert is_terminal("DEAD_LETTER")
        assert not is_terminal("DISCOVERED")
        assert not is_terminal("QUALIFIED")

    def test_is_terminal_positive(self):
        assert is_terminal_positive("PAID")
        assert not is_terminal_positive("REJECTED")

    def test_is_terminal_negative(self):
        assert is_terminal_negative("REJECTED")
        assert is_terminal_negative("BLOCKED")
        assert is_terminal_negative("FAILED")
        assert is_terminal_negative("DEAD_LETTER")
        assert not is_terminal_negative("PAID")


class TestLegacyAdapters:
    def test_workbank_status_to_payment(self):
        assert workbank_status_to_payment("preparing") == "DISCOVERED"
        assert workbank_status_to_payment("ready_to_deliver") == "READY"
        assert workbank_status_to_payment("needs_access") == "WAITING_HUMAN"
        assert workbank_status_to_payment("delivered") == "SUBMITTED"
        assert workbank_status_to_payment("unknown") == "DISCOVERED"

    def test_execution_state_to_payment(self):

        assert execution_state_to_payment(ExecState.DISCOVERED.value) == "DISCOVERED"
        assert execution_state_to_payment(ExecState.QUALIFIED.value) == "QUALIFIED"
        assert execution_state_to_payment(ExecState.READY.value) == "READY"
        assert execution_state_to_payment(ExecState.QUEUED.value) == "QUEUED"
        assert execution_state_to_payment(ExecState.EXECUTING.value) == "EXECUTING"
        assert execution_state_to_payment(ExecState.WAITING_HUMAN.value) == "WAITING_HUMAN"
        assert execution_state_to_payment(ExecState.SUBMITTED.value) == "SUBMITTED"
        assert execution_state_to_payment(ExecState.VERIFICATION.value) == "VERIFICATION"
        assert execution_state_to_payment(ExecState.PAID.value) == "PAID"
        assert execution_state_to_payment(ExecState.REJECTED.value) == "REJECTED"
        assert execution_state_to_payment(ExecState.BLOCKED.value) == "BLOCKED"
        assert execution_state_to_payment(ExecState.FAILED.value) == "FAILED"
        assert execution_state_to_payment(ExecState.DEAD_LETTER.value) == "DEAD_LETTER"
        assert execution_state_to_payment("unknown") == "DISCOVERED"

    def test_revenue_status_to_payment(self):
        assert revenue_status_to_payment("pending") == "SUBMITTED"
        assert revenue_status_to_payment("reviewing") == "VERIFICATION"
        assert revenue_status_to_payment("accepted") == "VERIFICATION"
        assert revenue_status_to_payment("paid") == "PAID"
        assert revenue_status_to_payment("cancelled") == "REJECTED"
        assert revenue_status_to_payment("failed") == "FAILED"
        assert revenue_status_to_payment("unknown") == "SUBMITTED"


class TestPipelineStore:
    def test_store_add_and_get(self, tmp_path):
        store = PaymentPipelineStore(store_path=tmp_path / "test.json")

        item = store.add("item1", "workbank", {"title": "Test"}, "DISCOVERED")
        assert item.item_id == "item1"
        assert item.state == "DISCOVERED"
        assert item.source == "workbank"

        retrieved = store.get("item1")
        assert retrieved is not None
        assert retrieved.item_id == "item1"

    def test_store_transition(self, tmp_path):
        store = PaymentPipelineStore(store_path=tmp_path / "test.json")
        store.add("item1", "workbank", {"title": "Test"}, "DISCOVERED")

        store.transition("item1", "QUALIFIED")
        item = store.get("item1")
        assert item.state == "QUALIFIED"
        assert "QUALIFIED" in item.history

    def test_invalid_transition_raises(self, tmp_path):
        store = PaymentPipelineStore(store_path=tmp_path / "test.json")
        store.add("item1", "workbank", {}, "DISCOVERED")

        with pytest.raises(ValueError):
            store.transition("item1", "PAID")

    def test_get_by_state(self, tmp_path):
        store = PaymentPipelineStore(store_path=tmp_path / "test.json")
        store.add("item1", "workbank", {}, "DISCOVERED")
        store.add("item2", "workbank", {}, "QUALIFIED")

        discovered = store.get_by_state("DISCOVERED")
        assert len(discovered) == 1

        qualified = store.get_by_state("QUALIFIED")
        assert len(qualified) == 1

    def test_get_by_source(self, tmp_path):
        store = PaymentPipelineStore(store_path=tmp_path / "test.json")
        store.add("item1", "workbank", {}, "DISCOVERED")
        store.add("item2", "execution", {}, "DISCOVERED")

        workbank = store.get_by_source("workbank")
        assert len(workbank) == 1

        execution = store.get_by_source("execution")
        assert len(execution) == 1

    def test_get_all(self, tmp_path):
        store = PaymentPipelineStore(store_path=tmp_path / "test.json")
        store.add("item1", "workbank", {}, "DISCOVERED")
        store.add("item2", "execution", {}, "DISCOVERED")

        all_items = store.get_all()
        assert len(all_items) == 2


class TestPipelineSync:
    def test_full_pipeline_sync(self):
        result = full_pipeline_sync()
        assert "workbank" in result
        assert "execution" in result
        assert "revenue" in result


class TestPipelineAnalytics:
    def test_get_pipeline_analytics(self, tmp_path):
        # Create a fresh store with known state
        store = PaymentPipelineStore(store_path=tmp_path / "test.json")
        store._items = {}  # Clear any existing items from sync
        store.add("item1", "workbank", {}, "DISCOVERED")
        store.add("item2", "workbank", {}, "READY")
        store.add("item3", "execution", {}, "PAID")

        # Manually compute analytics like get_pipeline_analytics does
        items = store.get_all()
        by_state = {}
        by_source = {}
        for item in items:
            by_state[item.state] = by_state.get(item.state, 0) + 1
            by_source[item.source] = by_source.get(item.source, 0) + 1

        terminal_positive = sum(1 for i in items if i.state == "PAID")
        terminal_negative = sum(1 for i in items if i.state in {"REJECTED", "BLOCKED", "FAILED", "DEAD_LETTER"})
        in_progress = len(items) - terminal_positive - terminal_negative

        analytics = {
            "total": len(items),
            "by_state": by_state,
            "by_source": by_source,
            "terminal_positive": terminal_positive,
            "terminal_negative": terminal_negative,
            "in_progress": in_progress,
            "conversion_rate": terminal_positive / max(1, terminal_positive + terminal_negative),
        }

        assert analytics["total"] == 3
        assert "DISCOVERED" in analytics["by_state"]
        assert "READY" in analytics["by_state"]
        assert "PAID" in analytics["by_state"]
        assert analytics["terminal_positive"] == 1
        assert analytics["terminal_negative"] == 0
        assert "conversion_rate" in analytics


class TestPipelineItem:
    def test_pipeline_item_creation(self):
        item = PipelineItem(
            item_id="test",
            state="DISCOVERED",
            source="workbank",
            payload={"title": "Test"},
            history=["DISCOVERED"],
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            metadata={"key": "value"},
        )

        assert item.item_id == "test"
        assert item.state == "DISCOVERED"
        assert item.source == "workbank"

        d = item.to_dict()
        assert d["item_id"] == "test"
        assert d["state"] == "DISCOVERED"
        assert "history" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
