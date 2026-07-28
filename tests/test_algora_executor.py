"""Tests for AlgoraExecutor — claim issues, create PRs, submit PRs, get bounties."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.opportunity.executors.algora_executor import AlgoraExecutor


class _MockClient:
    """Mock httpx.AsyncClient that works correctly with async with."""

    def __init__(self):
        self.post = AsyncMock()
        self.get = AsyncMock()
        self.patch = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _mock_response(status: int, json_data: dict | None = None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or {}
    resp.text = str(json_data or {})
    return resp


@pytest.fixture
def executor():
    return AlgoraExecutor({"token": "test-token", "github_token": "test-gh-token"})


@pytest.fixture
def executor_no_token():
    return AlgoraExecutor({"github_token": "test-gh-token"})


@pytest.fixture
def executor_no_gh_token():
    return AlgoraExecutor({"token": "test-token"})


class TestAlgoraExecutorNoToken:
    def test_claim_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.claim_issue("b1", "owner/repo", 1))
        assert result.success is False
        assert "ALGORA_TOKEN" in result.error

    def test_submit_pr_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.submit_pr("b1", "http://pr.url"))
        assert result.success is False
        assert "ALGORA_TOKEN" in result.error

    def test_get_bounty_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.get_bounty("b1"))
        assert result.success is False
        assert "ALGORA_TOKEN" in result.error

    def test_create_pr_fails_without_github_token(self, executor_no_gh_token):
        result = asyncio.run(executor_no_gh_token.create_pr("owner/repo", "fix-bug", "main", "Fix bug", "desc"))
        assert result.success is False
        assert "GITHUB_TOKEN" in result.error


class TestAlgoraExecutorClaim:
    def test_claim_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(
                200, {"claim_id": "c1", "expires_at": "2026-08-01"}
            )
            result = asyncio.run(executor.claim_issue("b1", "owner/repo", 1))
            assert result.success is True
            assert result.data["claim_id"] == "c1"

    def test_claim_api_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(400, {"error": "already claimed"})
            result = asyncio.run(executor.claim_issue("b1", "owner/repo", 1))
            assert result.success is False

    def test_claim_network_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.side_effect = TimeoutError("request timed out")
            result = asyncio.run(executor.claim_issue("b1", "owner/repo", 1))
            assert result.success is False


class TestAlgoraExecutorSubmitPR:
    def test_submit_pr_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(200, {"submission_id": "s1", "status": "pending"})
            result = asyncio.run(executor.submit_pr("b1", "http://pr.url"))
            assert result.success is True
            assert result.data["submission_id"] == "s1"


class TestAlgoraExecutorGetBounty:
    def test_get_bounty_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {"id": "b1", "amount": 1000})
            result = asyncio.run(executor.get_bounty("b1"))
            assert result.success is True

    def test_get_bounty_not_found(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(404, {"error": "not found"})
            result = asyncio.run(executor.get_bounty("nonexistent"))
            assert result.success is False


class TestAlgoraExecutorCreatePR:
    def test_create_pr_base_ref_not_found(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(404, {"error": "not found"})
            result = asyncio.run(executor.create_pr("owner/repo", "fix-bug", "main", "Fix", "desc"))
            assert result.success is False
            assert "Base ref not found" in result.error

    def test_create_pr_without_files(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {"object": {"sha": "abc123"}})
            mock_http.return_value.post.side_effect = [
                _mock_response(201, {"ref": "refs/heads/new-branch"}),
                _mock_response(201, {"number": 1, "html_url": "http://pr.url"}),
            ]
            result = asyncio.run(executor.create_pr("owner/repo", "new-branch", "main", "Title", "Body"))
            assert result.success is True

    def test_create_pr_passes_correct_params(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {"object": {"sha": "abc123"}})
            mock_http.return_value.post.return_value = _mock_response(201, {"number": 42, "html_url": "http://pr.url"})
            result = asyncio.run(executor.create_pr("owner/repo", "fix-bug", "main", "Fix bug", "A fix"))
            assert result.success is True
            _, kwargs = mock_http.return_value.post.call_args
            assert kwargs["json"]["title"] == "Fix bug"
            assert kwargs["json"]["head"] == "fix-bug"
            assert kwargs["json"]["base"] == "main"
            assert kwargs["json"]["body"] == "A fix"


class TestAlgoraExecutorDispatch:
    def test_unknown_action(self, executor):
        result = asyncio.run(executor.execute("nonexistent"))
        assert result.success is False
        assert "Unknown action" in result.error

    def test_dispatch_claim(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(200, {"claim_id": "c1"})
            result = asyncio.run(executor.execute("claim_issue", bounty_id="b1", repo="a/b", issue_number=1))
            assert result.success is True
