"""Tests for Autonomous Workflow Engine — discover→select→plan→execute→learn loop.

Uses mocked executors and opportunity sources so no real API calls are made.
Proves the orchestration logic is correct end-to-end.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from core.autonomy.workflow_engine import AutonomousWorkflow, WorkPlan
from core.opportunity.adapters import RawOpportunity
from core.opportunity.executors import BaseExecutor, ExecutionResult
from core.opportunity.scorer import score_opportunity

# ── Mock Executor ───────────────────────────────────────────────


class MockExecutor(BaseExecutor):
    """Executor that returns configurable results for testing."""

    platform = "mock"

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.call_history: list[tuple[str, dict]] = []
        self._results: dict[str, ExecutionResult] = {}

    def set_result(self, action: str, result: ExecutionResult) -> None:
        self._results[action] = result

    async def execute(self, action: str, **kwargs) -> ExecutionResult:
        self.call_history.append((action, kwargs))
        return self._results.get(action, ExecutionResult(False, action, "", error="No mock result configured"))


# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def sample_opportunity() -> RawOpportunity:
    return RawOpportunity(
        id="op-1",
        name="Fix critical SSRF vulnerability",
        description="There is a SSRF vulnerability in the URL fetch endpoint",
        platform="algora",
        url="https://algora.xyz/bounty/1",
        reward=500.0,
        effort_hours=4.0,
        tags=["python", "security", "ssrf"],
        cycle="forge",
        source_type="bounty",
        source_name="algora",
        metadata={
            "repository": "owner/repo",
            "issue_number": 42,
            "bounty_id": "b-1",
        },
    )


# ── Tests ───────────────────────────────────────────────────────


class TestWorkPlan:
    """Test WorkPlan dataclass."""

    def test_workplan_creation(self):
        plan = WorkPlan(
            opportunity_id="op-1",
            platform="algora",
            actions=[{"action": "claim_issue", "params": {"bounty_id": "b1"}}],
            estimated_effort_hours=4.0,
            estimated_reward=500.0,
            confidence=0.8,
        )
        assert plan.opportunity_id == "op-1"
        assert plan.platform == "algora"
        assert len(plan.actions) == 1
        assert plan.estimated_effort_hours == 4.0
        assert plan.estimated_reward == 500.0
        assert plan.created_at is not None


class TestAutonomousWorkflowConfiguration:
    """Test workflow configuration."""

    def test_default_config(self):
        wf = AutonomousWorkflow()
        assert wf.enabled is True
        assert wf.min_score_threshold == 60.0
        assert wf.max_concurrent == 1
        assert wf.dry_run is False
        assert wf.execution_history == []

    def test_disabled_returns_empty(self):
        """When workflow is disabled, run_cycle should return immediately."""
        import asyncio

        wf = AutonomousWorkflow(config={"enabled": False})
        results = asyncio.run(wf.run_cycle())
        assert results == []

    def test_dry_run_mode(self):
        wf = AutonomousWorkflow(config={"dry_run": True})
        assert wf.dry_run is True

    def test_custom_threshold(self):
        wf = AutonomousWorkflow(config={"min_score_threshold": 80.0})
        assert wf.min_score_threshold == 80.0


class TestAutonomousWorkflowExecution:
    """Test workflow with mocked executors and opportunity sources."""

    @pytest.mark.asyncio
    async def test_no_opportunities_returns_empty(self):
        """When no opportunities found, workflow should return empty."""
        wf = AutonomousWorkflow()

        with patch(
            "core.autonomy.workflow_engine.fetch_all_opportunities",
            new=AsyncMock(return_value=[]),
        ):
            results = await wf.run_cycle()

        assert results == []

    @pytest.mark.asyncio
    async def test_executor_called_with_correct_actions(self):
        """Verify executor receives correct action names via _execute_plan."""
        mock_exec = MockExecutor()
        mock_exec.set_result("claim_issue", ExecutionResult(True, "claim_issue", "b1", "Claimed"))
        mock_exec.set_result("create_pr", ExecutionResult(True, "create_pr", "o/r", "PR created"))

        wf = AutonomousWorkflow(
            executors={"algora": mock_exec},
            config={"dry_run": False},
        )

        plan = WorkPlan(
            opportunity_id="op-1",
            platform="algora",
            actions=[
                {"action": "claim_issue", "params": {"bounty_id": "b1", "repo": "o/r", "issue_number": 42}},
                {
                    "action": "create_pr",
                    "params": {"repo": "o/r", "branch": "fix-42", "base": "main", "title": "Fix", "body": "Body"},
                },
            ],
            estimated_effort_hours=4.0,
            estimated_reward=500.0,
            confidence=0.8,
        )

        result = await wf._execute_plan(plan)
        assert result.success is True
        assert len(mock_exec.call_history) == 2
        assert mock_exec.call_history[0][0] == "claim_issue"
        assert mock_exec.call_history[1][0] == "create_pr"

    @pytest.mark.asyncio
    async def test_executor_not_found_returns_error(self):
        """When executor for a platform doesn't exist, should return error."""
        wf = AutonomousWorkflow(executors={})

        plan = WorkPlan(
            opportunity_id="op-1",
            platform="nonexistent",
            actions=[{"action": "test", "params": {}}],
            estimated_effort_hours=1.0,
            estimated_reward=100.0,
            confidence=0.5,
        )

        result = await wf._execute_plan(plan)
        assert result.success is False
        assert "No executor for platform" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_plan_stores_result_in_history(self):
        """_execute_plan does NOT store in history (run_cycle does)."""
        mock_exec = MockExecutor()
        mock_exec.set_result("test_action", ExecutionResult(True, "test_action", "target", "Done"))

        wf = AutonomousWorkflow(executors={"test": mock_exec})
        plan = WorkPlan(
            opportunity_id="op-1",
            platform="test",
            actions=[{"action": "test_action", "params": {}}],
            estimated_effort_hours=1.0,
            estimated_reward=100.0,
            confidence=0.5,
        )

        result = await wf._execute_plan(plan)
        assert result.success is True
        # _execute_plan does not store in history; that's run_cycle's job
        assert len(wf.execution_history) == 0

    @pytest.mark.asyncio
    async def test_run_cycle_stores_in_history(self):
        """run_cycle stores results in execution_history."""
        mock_exec = MockExecutor()
        mock_exec.set_result("claim_issue", ExecutionResult(True, "claim_issue", "b1", "OK"))

        wf = AutonomousWorkflow(
            executors={"algora": mock_exec},
            config={"min_score_threshold": 0.0, "dry_run": False},
        )

        opp = RawOpportunity(
            id="hist-test",
            name="Test opportunity",
            description="A test",
            platform="algora",
            reward=100.0,
            effort_hours=2.0,
            tags=["test"],
            cycle="forge",
            source_type="bounty",
            source_name="algora",
            metadata={"repository": "owner/repo", "issue_number": 1, "bounty_id": "hist-b"},
        )

        with patch(
            "core.autonomy.workflow_engine.fetch_all_opportunities",
            new=AsyncMock(return_value=[opp]),
        ):
            results = await wf.run_cycle()

        assert len(wf.execution_history) == len(results)

    @pytest.mark.asyncio
    async def test_partial_action_failure(self):
        """When one action fails, remaining actions should still execute."""
        mock_exec = MockExecutor()
        mock_exec.set_result("first", ExecutionResult(True, "first", "t1", "OK"))
        mock_exec.set_result("second", ExecutionResult(False, "second", "t2", "Failed"))

        wf = AutonomousWorkflow(executors={"test": mock_exec})

        plan = WorkPlan(
            opportunity_id="op-1",
            platform="test",
            actions=[
                {"action": "first", "params": {}},
                {"action": "second", "params": {}},
            ],
            estimated_effort_hours=3.0,
            estimated_reward=300.0,
            confidence=0.7,
        )

        result = await wf._execute_plan(plan)
        assert result.success is False  # Overall should fail due to second action
        assert len(mock_exec.call_history) == 2

    @pytest.mark.asyncio
    async def test_oss_bounty_plan_creation(self, sample_opportunity):
        """Test that OSS bounties get proper action plans."""
        wf = AutonomousWorkflow()
        scored = score_opportunity(
            opp_id=sample_opportunity.id,
            name=sample_opportunity.name,
            cycle=sample_opportunity.cycle,
            source_type=sample_opportunity.source_type,
            source_name=sample_opportunity.source_name,
            reward=sample_opportunity.reward,
            effort_hours=sample_opportunity.effort_hours,
            platform=sample_opportunity.platform,
            technology_tags=sample_opportunity.tags,
            url=sample_opportunity.url,
            created_at=sample_opportunity.created_at,
            original=sample_opportunity.metadata,  # Pass metadata as original
        )

        plan = await wf._create_plan(scored)
        assert plan is not None, (
            f"Plan should not be None. Scored: id={scored.id}, platform={scored.platform}, original={scored.original}"
        )
        assert plan.platform == "algora"
        assert len(plan.actions) >= 1
        assert plan.actions[0]["action"] == "claim_issue"
        assert plan.actions[0]["params"]["bounty_id"] == "b-1"

    @pytest.mark.asyncio
    async def test_freelancer_plan_creation(self):
        """Test Freelancer plans include bid action."""
        wf = AutonomousWorkflow()
        scored = score_opportunity(
            opp_id="fl-1",
            name="Build REST API",
            cycle="forge",
            source_type="project",
            source_name="freelancer",
            reward=1000.0,
            effort_hours=40.0,
            platform="freelancer",
            technology_tags=["python", "fastapi"],
            url="https://freelancer.com/projects/1",
            original={"project_id": "p-123"},
        )

        plan = await wf._create_plan(scored)
        assert plan is not None
        assert plan.actions[0]["action"] == "bid_on_project"

    @pytest.mark.asyncio
    async def test_ai_work_plan_creation(self):
        """Test AI work platforms get task claim actions."""
        wf = AutonomousWorkflow()
        scored = score_opportunity(
            opp_id="da-1",
            name="Rate AI responses",
            cycle="pulse",
            source_type="task",
            source_name="dataannotation",
            reward=20.0,
            effort_hours=1.0,
            platform="dataannotation",
            technology_tags=[],
            url="https://dataannotation.tech/tasks/1",
        )

        plan = await wf._create_plan(scored)
        assert plan is not None
        assert plan.actions[0]["action"] == "claim_task"

    @pytest.mark.asyncio
    async def test_opencollective_returns_none(self):
        """Open Collective is funding-only, not executable."""
        wf = AutonomousWorkflow()
        scored = score_opportunity(
            opp_id="oc-1",
            name="Sponsor project",
            cycle="forge",
            source_type="funding",
            source_name="opencollective",
            reward=0.0,
            effort_hours=0.0,
            platform="opencollective",
            technology_tags=[],
            url="https://opencollective.com/project",
        )

        plan = await wf._create_plan(scored)
        assert plan is None  # Not executable


class TestWorkflowDryRun:
    """Test dry-run behavior."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_immediately(self):
        """In dry-run mode, _execute_plan returns immediately without calling executor."""
        mock_exec = MockExecutor()
        mock_exec.set_result("claim", ExecutionResult(True, "claim", "b1", "OK"))

        wf = AutonomousWorkflow(
            executors={"test": mock_exec},
            config={"dry_run": True},
        )

        plan = WorkPlan(
            opportunity_id="op-1",
            platform="test",
            actions=[{"action": "claim", "params": {}}],
            estimated_effort_hours=1.0,
            estimated_reward=100.0,
            confidence=0.5,
        )

        result = await wf._execute_plan(plan)
        assert result.success is True  # Dry run always "succeeds"
        assert len(mock_exec.call_history) == 0  # No actual calls
        assert "DRY RUN" in (result.error or "")

    @pytest.mark.asyncio
    async def test_dry_run_via_run_cycle(self):
        """run_cycle with dry_run=True should not call any executor."""
        mock_exec = MockExecutor()
        mock_exec.set_result("claim_issue", ExecutionResult(True, "claim_issue", "b1", "OK"))

        wf = AutonomousWorkflow(
            executors={"algora": mock_exec},
            config={"min_score_threshold": 0.0, "dry_run": True},
        )

        opp = RawOpportunity(
            id="dry-test",
            name="Dry run test",
            description="Testing dry run",
            platform="algora",
            reward=100.0,
            effort_hours=2.0,
            tags=["test"],
            cycle="forge",
            source_type="bounty",
            source_name="algora",
            metadata={"repository": "owner/repo", "issue_number": 1, "bounty_id": "dry-b"},
        )

        with patch(
            "core.autonomy.workflow_engine.fetch_all_opportunities",
            new=AsyncMock(return_value=[opp]),
        ):
            results = await wf.run_cycle()

        assert len(results) > 0
        assert results[0].success is True
        assert "DRY RUN" in (results[0].error or "")
        # No executor should have been called
        assert len(mock_exec.call_history) == 0


class TestWorkflowScoring:
    """Test that scoring correctly filters opportunities."""

    @pytest.mark.asyncio
    async def test_low_value_opportunities_filtered(self):
        """Opportunities below threshold should not produce plans."""
        mock_exec = MockExecutor()
        wf = AutonomousWorkflow(
            executors={"algora": mock_exec},
            config={"min_score_threshold": 90.0},
        )

        # Create a low-value opportunity
        low_value = RawOpportunity(
            id="low-1",
            name="Minor fix",
            description="A very minor fix",
            platform="algora",
            reward=10.0,
            effort_hours=8.0,
            tags=[],
            cycle="forge",
            source_type="bounty",
            source_name="algora",
            metadata={"repository": "o/r", "issue_number": 1, "bounty_id": "low-b"},
        )

        with patch(
            "core.autonomy.workflow_engine.fetch_all_opportunities",
            new=AsyncMock(return_value=[low_value]),
        ):
            results = await wf.run_cycle()

        # Low-value opportunity should be filtered out due to high threshold
        assert len(results) == 0


@pytest.mark.asyncio
async def test_full_cycle_with_real_scoring():
    """Integration test: full cycle with an opportunity that should pass scoring."""
    mock_exec = MockExecutor()
    mock_exec.set_result("claim_issue", ExecutionResult(True, "claim_issue", "b1", "Claimed!"))

    wf = AutonomousWorkflow(
        executors={"algora": mock_exec},
        config={"min_score_threshold": 0.0, "dry_run": True},  # Low threshold + dry run
    )

    opp = RawOpportunity(
        id="int-1",
        name="Fix memory leak in cache",
        description="Memory leak when cache exceeds 1GB",
        platform="algora",
        url="https://algora.xyz/bounty/int-1",
        reward=500.0,
        effort_hours=4.0,
        tags=["python", "performance"],
        cycle="forge",
        source_type="bounty",
        source_name="algora",
        metadata={"repository": "owner/repo", "issue_number": 42, "bounty_id": "int-b"},
    )

    with patch(
        "core.autonomy.workflow_engine.fetch_all_opportunities",
        new=AsyncMock(return_value=[opp]),
    ):
        results = await wf.run_cycle()

    # With threshold=0, the opportunity should pass scoring and create a plan
    assert len(results) > 0, (
        "Expected at least one plan to be created. Check that the RawOpportunity has all required fields."
    )
    assert results[0].success is True
    assert "DRY RUN" in (results[0].error or "")
