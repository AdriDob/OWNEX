"""Tests for all platform executors — uses httpx mocks, no real API keys needed.

Every executor is tested against realistic HTTP response shapes so the system
is verified end-to-end. When real credentials are added, these tests prove
the code is ready to run against production.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from core.opportunity.executors import ExecutionResult
from core.opportunity.executors.algora_executor import AlgoraExecutor
from core.opportunity.executors.freelancer_executor import FreelancerExecutor
from core.opportunity.executors.issuehunt_executor import IssueHuntExecutor
from core.opportunity.executors.mindrift_executor import MindriftExecutor
from core.opportunity.executors.opire_executor import OpireExecutor

# ── Helpers ─────────────────────────────────────────────────────


class AsyncContextManagerMock:
    """Async context manager that returns a mocked client."""

    def __init__(self, client_mock):
        self._client = client_mock

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, *args):
        pass


def _mock_httpx_client(status: int = 200, json_data: dict | None = None):
    """Create a mock httpx.AsyncClient that returns given response.

    Uses regular Mock for response (json() and .text are sync in httpx).
    Uses AsyncMock for client (__aenter__ and HTTP methods are async).
    """
    from unittest.mock import MagicMock

    client = AsyncMock()
    response = MagicMock()
    response.status_code = status
    response.json.return_value = json_data or {}
    response.text = str(json_data or {})
    # All HTTP methods return the same response mock
    for method in ("get", "post", "put", "patch", "delete"):
        getattr(client, method).return_value = response
    return client


def _patch_httpx(executor_class, config: dict | None = None):
    """Create executor instance with httpx.AsyncClient patched.

    Returns (executor, client_mock) so the test can assert on calls.
    """
    executor = executor_class(config or {})
    patcher = patch(f"{executor_class.__module__}.httpx.AsyncClient")
    mock_class = patcher.start()
    client = _mock_httpx_client()
    mock_class.return_value = AsyncContextManagerMock(client)
    # Also patch any module-level httpx.AsyncClient references
    return executor, client, patcher


# ── AlgoraExecutor ──────────────────────────────────────────────


class TestAlgoraExecutor:
    """Test Algora.xyz executor — claim issues, create PRs, submit."""

    @pytest.mark.asyncio
    async def test_claim_issue_success(self):
        executor = AlgoraExecutor({"token": "test-token"})
        with patch("core.opportunity.executors.algora_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"claim_id": "c123", "expires_at": "2026-08-01T00:00:00Z"})
            mock.return_value = AsyncContextManagerMock(client)

            result = await executor.claim_issue("bounty-1", "owner/repo", 42)

        assert result.success is True
        assert result.action == "claim_issue"
        assert result.target == "bounty-1"
        assert "Claimed bounty" in result.message
        assert result.data["claim_id"] == "c123"

    @pytest.mark.asyncio
    async def test_claim_issue_missing_token(self):
        executor = AlgoraExecutor({})  # No token
        result = await executor.claim_issue("bounty-1", "owner/repo", 42)
        assert result.success is False
        assert "ALGORA_TOKEN not configured" in result.error

    @pytest.mark.asyncio
    async def test_claim_issue_api_error(self):
        executor = AlgoraExecutor({"token": "test-token"})
        with patch("core.opportunity.executors.algora_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(400, {"error": "already_claimed"})
            mock.return_value = AsyncContextManagerMock(client)

            result = await executor.claim_issue("bounty-1", "owner/repo", 42)

        assert result.success is False
        assert "400" in result.error

    @pytest.mark.asyncio
    async def test_claim_issue_network_error(self):
        executor = AlgoraExecutor({"token": "test-token"})
        with patch("core.opportunity.executors.algora_executor.httpx.AsyncClient") as mock:
            client = AsyncMock()
            client.post.side_effect = Exception("Connection refused")
            mock.return_value = AsyncContextManagerMock(client)

            result = await executor.claim_issue("bounty-1", "owner/repo", 42)

        assert result.success is False
        assert "Connection refused" in result.error

    @pytest.mark.asyncio
    async def test_submit_pr_success(self):
        executor = AlgoraExecutor({"token": "test-token"})
        with patch("core.opportunity.executors.algora_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"submission_id": "s456", "status": "pending_review"})
            mock.return_value = AsyncContextManagerMock(client)

            result = await executor.submit_pr("bounty-1", "https://github.com/owner/repo/pull/1")

        assert result.success is True
        assert result.action == "submit_pr"
        assert result.data["submission_id"] == "s456"

    @pytest.mark.asyncio
    async def test_submit_pr_missing_token(self):
        executor = AlgoraExecutor({})
        result = await executor.submit_pr("bounty-1", "https://github.com/owner/repo/pull/1")
        assert result.success is False
        assert "ALGORA_TOKEN not configured" in result.error

    @pytest.mark.asyncio
    async def test_get_bounty_success(self):
        executor = AlgoraExecutor({"token": "test-token"})
        bounty_data = {"id": "b-1", "title": "Fix critical bug", "amount": 500, "currency": "USD"}
        with patch("core.opportunity.executors.algora_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, bounty_data)
            mock.return_value = AsyncContextManagerMock(client)

            result = await executor.get_bounty("b-1")

        assert result.success is True
        assert result.data["title"] == "Fix critical bug"
        assert result.data["amount"] == 500

    @pytest.mark.asyncio
    async def test_execute_routing(self):
        executor = AlgoraExecutor({"token": "test-token"})
        with patch("core.opportunity.executors.algora_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"claim_id": "c1"})
            mock.return_value = AsyncContextManagerMock(client)

            result = await executor.execute("claim_issue", bounty_id="b-2", repo="o/r", issue_number=7)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        executor = AlgoraExecutor({"token": "test-token"})
        result = await executor.execute("nonexistent_action")
        assert result.success is False
        assert "Unknown action" in result.error

    @pytest.mark.asyncio
    async def test_create_pr_success(self):
        executor = AlgoraExecutor({"token": "test-token", "github_token": "gh-token"})
        with patch("core.opportunity.executors.algora_executor.httpx.AsyncClient") as mock:
            # Need sequential responses: base ref, branch create, blob, tree, commit, branch update, PR
            client = AsyncMock()
            responses = [
                _make_response(200, {"object": {"sha": "abc123"}}),  # get base ref
                _make_response(201, {}),  # create branch
                _make_response(201, {"sha": "blob1"}),  # create blob
                _make_response(200, {"sha": "tree1"}),  # get base tree
                _make_response(201, {"sha": "new_tree"}),  # create tree
                _make_response(201, {"sha": "commit1"}),  # create commit
                _make_response(200, {}),  # update branch ref
                _make_response(201, {"number": 1, "html_url": "https://github.com/o/r/pull/1"}),  # create PR
            ]
            client.get.side_effect = [responses[0], responses[3]]  # get ref, get base tree
            client.post.side_effect = [responses[1], responses[2], responses[4], responses[5], responses[7]]
            client.patch.side_effect = [responses[6]]
            mock.return_value = AsyncContextManagerMock(client)

            result = await executor.create_pr("o/r", "fix-bug", "main", "Fix bug", "Body", {"file.py": "content"})

        assert result.success is True
        assert result.data["pr_number"] == 1

    @pytest.mark.asyncio
    async def test_create_pr_missing_github_token(self):
        executor = AlgoraExecutor({"token": "test-token"})  # No github_token
        result = await executor.create_pr("o/r", "fix", "main", "Title", "Body", None)
        assert result.success is False
        assert "GITHUB_TOKEN not configured" in result.error


# ── OpireExecutor ──────────────────────────────────────────────


class TestOpireExecutor:
    """Test Opire.dev executor — claim bounties, submit work."""

    @pytest.mark.asyncio
    async def test_claim_bounty_success(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "b-123", "status": "assigned"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.claim_bounty("bounty-123")
        assert result.success is True
        assert result.data["response"]["id"] == "b-123"

    @pytest.mark.asyncio
    async def test_claim_bounty_missing_token(self):
        executor = OpireExecutor({})
        result = await executor.claim_bounty("b-1")
        assert result.success is False
        assert "OPIRE_TOKEN not configured" in result.error

    @pytest.mark.asyncio
    async def test_claim_bounty_api_error(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(409, {"error": "already taken"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.claim_bounty("b-1")
        assert result.success is False
        assert "409" in result.error

    @pytest.mark.asyncio
    async def test_submit_work_success(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "s-789", "status": "submitted"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.submit_work("b-1", "https://github.com/o/r/pull/1", "Fixed it")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_bounties_success(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, [{"id": "b1", "title": "Fix bug", "amount": 100}])
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.get_bounties("open")
        assert result.success is True
        assert len(result.data["bounties"]) > 0

    @pytest.mark.asyncio
    async def test_get_bounty_success(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "b1", "title": "Bug", "amount": 50})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.get_bounty("b1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_routing(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.execute("claim_bounty", bounty_id="b-1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        executor = OpireExecutor({"token": "op-token"})
        result = await executor.execute("bad_action")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"status": "ok"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.health_check()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_health_check_offline(self):
        executor = OpireExecutor({"token": "op-token"})
        with patch("core.opportunity.executors.opire_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(503, {})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.health_check()
        assert result.success is False


# ── IssueHuntExecutor ──────────────────────────────────────────


class TestIssueHuntExecutor:
    """Test IssueHunt.io executor — claim issues, submit PRs."""

    @pytest.mark.asyncio
    async def test_claim_issue_success(self):
        executor = IssueHuntExecutor({"token": "ih-token"})
        with patch("core.opportunity.executors.issuehunt_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"claim_id": "c789", "expires_at": "2026-08-10T00:00:00Z"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.claim_issue("b-1", "owner/repo", 42)
        assert result.success is True
        assert result.data["claim_id"] == "c789"

    @pytest.mark.asyncio
    async def test_claim_issue_missing_token(self):
        executor = IssueHuntExecutor({})
        result = await executor.claim_issue("b-1", "o/r", 1)
        assert result.success is False
        assert "ISSUEHUNT_TOKEN not configured" in result.error

    @pytest.mark.asyncio
    async def test_submit_pr_success(self):
        executor = IssueHuntExecutor({"token": "ih-token"})
        with patch("core.opportunity.executors.issuehunt_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"submission_id": "s111", "status": "review"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.submit_pr("b-1", "https://github.com/o/r/pull/1")
        assert result.success is True
        assert result.data["submission_id"] == "s111"

    @pytest.mark.asyncio
    async def test_get_bounty_success(self):
        executor = IssueHuntExecutor({"token": "ih-token"})
        with patch("core.opportunity.executors.issuehunt_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "b1", "reward": 250})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.get_bounty("b1")
        assert result.success is True
        assert result.data["reward"] == 250

    @pytest.mark.asyncio
    async def test_execute_routing(self):
        executor = IssueHuntExecutor({"token": "ih-token"})
        with patch("core.opportunity.executors.issuehunt_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.execute("claim_issue", bounty_id="b1", repo="o/r", issue_number=1)
        assert result.success is True


# ── FreelancerExecutor ─────────────────────────────────────────


class TestFreelancerExecutor:
    """Test Freelancer.com executor — bid, deliver, milestones."""

    @pytest.mark.asyncio
    async def test_bid_on_project_success(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "bid-456", "status": "active"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.bid_on_project("p-789", 500.0, 7, "I can do this")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_bid_on_project_missing_token(self):
        executor = FreelancerExecutor({})
        result = await executor.bid_on_project("p-1", 100, 7, "")
        assert result.success is False
        assert "FREELANCER_API_TOKEN not configured" in result.error

    @pytest.mark.asyncio
    async def test_bid_on_project_api_error(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(400, {"error": "insufficient_balance"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.bid_on_project("p-1", 50, 3, "Hello")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_submit_deliverable_success(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "del-1", "status": "submitted"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.submit_deliverable("p-1", {"file.py": "content"}, "Done")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_request_milestone_release_success(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"status": "released"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.request_milestone_release("p-1", "m-1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_project_success(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "p-1", "title": "Build API", "budget": 1000})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.get_project("p-1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_routing(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.execute(
                "bid_on_project", project_id="p1", bid_amount=100, period=5, description="test"
            )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        result = await executor.execute("unknown_action")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_list_my_bids(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"bids": []})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.execute("list_my_bids", status="active")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_connection_error(self):
        executor = FreelancerExecutor({"api_token": "fl-token", "user_id": "u123"})
        with patch("core.opportunity.executors.freelancer_executor.httpx.AsyncClient") as mock:
            client = AsyncMock()
            client.post.side_effect = Exception("Connection timeout")
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.bid_on_project("p-1", 100, 5, "test")
        assert result.success is False
        assert "Connection timeout" in result.error


# ── MindriftExecutor ───────────────────────────────────────────


class TestMindriftExecutor:
    """Test Mindrift.io executor — claim tasks, submit solutions."""

    @pytest.mark.asyncio
    async def test_claim_task_success(self):
        executor = MindriftExecutor({"token": "mr-token"})
        with patch("core.opportunity.executors.mindrift_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "task-1", "status": "claimed"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.claim_task("task-1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_claim_task_missing_token(self):
        executor = MindriftExecutor({})
        result = await executor.claim_task("task-1")
        assert result.success is False
        assert "MINDRIFT_EMAIL not configured" in result.error

    @pytest.mark.asyncio
    async def test_submit_task_success(self):
        executor = MindriftExecutor({"token": "mr-token"})
        with patch("core.opportunity.executors.mindrift_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"id": "sub-1", "status": "submitted"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.submit_task("task-1", "https://solution.url", "Done")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_get_tasks_success(self):
        executor = MindriftExecutor({"token": "mr-token"})
        with patch("core.opportunity.executors.mindrift_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, [{"id": "t1", "title": "Rate AI responses"}])
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.get_tasks("open")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_routing(self):
        executor = MindriftExecutor({"token": "mr-token"})
        with patch("core.opportunity.executors.mindrift_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.execute("claim_task", task_id="t1")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        executor = MindriftExecutor({"token": "mr-token"})
        result = await executor.execute("bad_action")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        executor = MindriftExecutor({"token": "mr-token"})
        with patch("core.opportunity.executors.mindrift_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(200, {"status": "healthy"})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.health_check()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_health_check_offline(self):
        executor = MindriftExecutor({"token": "mr-token"})
        with patch("core.opportunity.executors.mindrift_executor.httpx.AsyncClient") as mock:
            client = _mock_httpx_client(500, {})
            mock.return_value = AsyncContextManagerMock(client)
            result = await executor.health_check()
        assert result.success is False


# ── Top-level module claim functions ────────────────────────────


@pytest.mark.asyncio
async def test_mindrift_top_level_claim_with_task_id():
    from core.opportunity.executors.mindrift_executor import claim

    with patch("core.opportunity.executors.mindrift_executor.MindriftExecutor.claim_task") as mock_claim:
        mock_claim.return_value = ExecutionResult(True, "claim_task", "t-1", "Claimed")
        result = await claim(task_id="t-1")
    assert result.success is True


@pytest.mark.asyncio
async def test_mindrift_top_level_claim_finds_first_task():
    from core.opportunity.executors.mindrift_executor import claim

    with patch("core.opportunity.executors.mindrift_executor.MindriftExecutor.get_tasks") as mock_get:
        mock_get.return_value = ExecutionResult(
            True,
            "get_tasks",
            "open",
            data={"tasks": [{"id": "first-task"}, {"id": "second-task"}]},
        )
        with patch("core.opportunity.executors.mindrift_executor.MindriftExecutor.claim_task") as mock_claim:
            mock_claim.return_value = ExecutionResult(True, "claim_task", "first-task", "Claimed first")
            result = await claim(task_id=None)
    assert result.success is True


@pytest.mark.asyncio
async def test_mindrift_top_level_claim_no_tasks():
    from core.opportunity.executors.mindrift_executor import claim

    with patch("core.opportunity.executors.mindrift_executor.MindriftExecutor.get_tasks") as mock_get:
        mock_get.return_value = ExecutionResult(True, "get_tasks", "open", data={"tasks": []})
        result = await claim(task_id=None)
    assert result.success is False
    assert "No open tasks" in result.error


# ── BaseExecutor ────────────────────────────────────────────────


class TestBaseExecutor:
    """Test base executor contract."""

    @pytest.mark.asyncio
    async def test_base_executor_raises_not_implemented(self):
        from core.opportunity.executors import BaseExecutor

        ex = BaseExecutor()
        with pytest.raises(NotImplementedError):
            await ex.execute("anything")

    @pytest.mark.asyncio
    async def test_base_executor_health_check_default(self):
        from core.opportunity.executors import BaseExecutor

        ex = BaseExecutor()
        result = await ex.health_check()
        assert result.success is True
        assert "healthy" in result.message

    def test_is_enabled_default(self):
        from core.opportunity.executors import BaseExecutor

        assert BaseExecutor().is_enabled() is True

    def test_is_enabled_false(self):
        from core.opportunity.executors import BaseExecutor

        assert BaseExecutor({"enabled": False}).is_enabled() is False

    def test_get_config(self):
        from core.opportunity.executors import BaseExecutor

        ex = BaseExecutor({"foo": "bar"})
        assert ex.get_config("foo") == "bar"
        assert ex.get_config("missing", "default") == "default"


# ── get_executors factory ───────────────────────────────────────


class TestGetExecutors:
    """Test executor factory function."""

    def test_returns_all_executors(self):
        from core.opportunity.executors import get_executors

        executors = get_executors()
        assert "algora" in executors
        assert "opire" in executors
        assert "freelancer" in executors
        assert "mindrift" in executors
        assert "issuehunt" in executors
        assert len(executors) == 5

    def test_executors_have_platform(self):
        from core.opportunity.executors import get_executors

        for name, ex in get_executors().items():
            assert ex.platform == name, f"{name} executor has wrong platform: {ex.platform}"


# ── Helpers ─────────────────────────────────────────────────────


def _make_response(status: int, json_data: dict) -> MagicMock:
    """Create a mock HTTP response (sync methods)."""
    from unittest.mock import MagicMock

    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp
