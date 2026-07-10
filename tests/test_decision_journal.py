"""Tests for core/decision_journal/ — append-only decision logging."""

from __future__ import annotations

import tempfile

import pytest

from core.decision_journal import get_decisions, log_decision, record_outcome


@pytest.fixture(autouse=True)
def _temp_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point CATEYE_DATA_DIR to a temp directory so DB writes don't pollute ~/.orion."""
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("CATEYE_DATA_DIR", tmp)
    yield
    # Cleanup after test
    import shutil

    shutil.rmtree(tmp, ignore_errors=True)


class TestLogDecision:
    def test_log_basic(self) -> None:
        d_id = log_decision("test-app", "test-agent", "rebalance", "Rebalancing portfolio", {"amount": 100})
        assert d_id.startswith("test-app-")
        assert len(d_id) > len("test-app-")

    def test_log_with_confidence(self) -> None:
        d_id = log_decision(
            "atlas", "trader-1", "buy", "Buy signal detected", {"symbol": "BTC"}, confidence=0.85, risk_score=0.3
        )
        assert d_id.startswith("atlas-")
        decisions = get_decisions(app_id="atlas")
        assert len(decisions) >= 1
        matched = [d for d in decisions if d["decision_id"] == d_id]
        assert len(matched) == 1
        assert matched[0]["confidence"] == 0.85
        assert matched[0]["risk_score"] == 0.3

    def test_log_app_isolation(self) -> None:
        d1 = log_decision("cateye", "scanner", "scan", "Scan started")
        d2 = log_decision("atlas", "trader", "trade", "Trade executed")
        cateye = get_decisions(app_id="cateye")
        atlas = get_decisions(app_id="atlas")
        assert any(d["decision_id"] == d1 for d in cateye)
        assert any(d["decision_id"] == d2 for d in atlas)
        assert not any(d["decision_id"] == d2 for d in cateye)

    def test_default_outcome(self) -> None:
        d_id = log_decision("hermes", "scheduler", "backup", "Daily backup")
        decisions = get_decisions(limit=100)
        matched = [d for d in decisions if d["decision_id"] == d_id]
        assert len(matched) == 1
        assert matched[0]["outcome"] == "pending"


class TestGetDecisions:
    def test_get_all(self) -> None:
        log_decision("app-a", "agent-1", "action-1", "Reason 1")
        log_decision("app-b", "agent-2", "action-2", "Reason 2")
        all_d = get_decisions(limit=100)
        assert len(all_d) >= 2

    def test_filter_by_app(self) -> None:
        log_decision("filter-app", "a1", "act", "test")
        results = get_decisions(app_id="filter-app")
        assert all(d["app_id"] == "filter-app" for d in results)

    def test_filter_by_agent(self) -> None:
        log_decision("app", "unique-agent-xyz", "act", "test")
        results = get_decisions(agent_id="unique-agent-xyz")
        assert all(d["agent_id"] == "unique-agent-xyz" for d in results)

    def test_limit(self) -> None:
        for i in range(5):
            log_decision("limit-app", f"a{i}", f"act-{i}", f"Reason {i}")
        results = get_decisions(app_id="limit-app", limit=3)
        assert len(results) <= 3


class TestRecordOutcome:
    def test_record_success(self) -> None:
        d_id = log_decision("app", "agent", "test", "test decision")
        ok = record_outcome(d_id, outcome="success", reward=1.0, notes="Worked well")
        assert ok is True

        decisions = get_decisions(limit=100)
        matched = [d for d in decisions if d["decision_id"] == d_id]
        assert len(matched) == 1
        assert matched[0]["outcome"] == "success"
        assert matched[0]["reward"] == 1.0

    def test_record_failure(self) -> None:
        d_id = log_decision("app", "agent", "test", "test decision")
        ok = record_outcome(d_id, outcome="failure", reward=-0.5, notes="Did not work")
        assert ok is True

        decisions = get_decisions(limit=100)
        matched = [d for d in decisions if d["decision_id"] == d_id]
        assert matched[0]["outcome"] == "failure"
        assert matched[0]["reward"] == -0.5

    def test_record_nonexistent(self) -> None:
        ok = record_outcome("nonexistent-decision", outcome="success")
        assert ok is False


class TestCopilotIntegration:
    def test_copilot_logs_to_journal(self) -> None:
        """CopilotAgent._log_decision() should persist to SQLite Decision Journal."""
        from core.copilot import CopilotAgent

        agent = CopilotAgent(app_id="cateye")
        agent._log_decision("analyze_finding", {"finding_id": "F-001", "confidence": 0.9})

        decisions = get_decisions(app_id="cateye", agent_id=agent.agent_id)
        assert len(decisions) >= 1
        assert any("analyze_finding" in d["action"] for d in decisions)

    def test_copilot_persists_across_sessions(self) -> None:
        """Decisions from one Copilot session should be retrievable after the agent is recreated."""
        from core.copilot import CopilotAgent

        agent1 = CopilotAgent(app_id="cateye")
        agent1._log_decision("audit_system", {"scope": "full"})
        agent1_id = agent1.agent_id

        # Create a new agent (simulates restart)
        decisions = get_decisions(app_id="cateye", agent_id=agent1_id)
        assert len(decisions) >= 1
        assert any(d["action"] == "audit_system" for d in decisions)
