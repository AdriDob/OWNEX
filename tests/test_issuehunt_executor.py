"""Tests for IssueHuntExecutor — claim issues, submit PRs, get bounties."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.opportunity.executors.issuehunt_executor import IssueHuntExecutor


class _MockClient:
    """Mock httpx.AsyncClient that works correctly with async with."""

    def __init__(self, post_response=None, get_response=None):
        self.post = AsyncMock(return_value=post_response)
        self.get = AsyncMock(return_value=get_response)

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
    return IssueHuntExecutor({"token": "test-token", "github_token": "test-gh-token"})


@pytest.fixture
def executor_no_token():
    return IssueHuntExecutor({"github_token": "test-gh-token"})


class TestIssueHuntExecutorNoToken:
    def test_claim_issue_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.claim_issue("b1", "owner/repo", 42))
        assert result.success is False
        assert "ISSUEHUNT_TOKEN" in result.error

    def test_submit_pr_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.submit_pr("b1", "http://pr.url"))
        assert result.success is False
        assert "ISSUEHUNT_TOKEN" in result.error

    def test_get_bounty_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.get_bounty("b1"))
        assert result.success is False
        assert "ISSUEHUNT_TOKEN" in result.error


class TestIssueHuntExecutorClaim:
    def test_claim_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(post_response=_mock_response(200, {"claim_id": "c1"}))
            result = asyncio.run(executor.claim_issue("b1", "owner/repo", 42))
            assert result.success is True
            assert "Claimed bounty b1" in result.message

    def test_claim_api_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(post_response=_mock_response(400, {"error": "already claimed"}))
            result = asyncio.run(executor.claim_issue("b1", "owner/repo", 42))
            assert result.success is False
            assert "already claimed" in result.error

    def test_claim_network_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(post_response=_mock_response(500, {"error": "server error"}))
            result = asyncio.run(executor.claim_issue("b1", "owner/repo", 42))
            assert result.success is False

    def test_claim_passes_repo_and_issue(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(post_response=_mock_response(200, {"claim_id": "c1"}))
            asyncio.run(executor.claim_issue("b1", "owner/repo", 42))
            call = mock_http.return_value.post
            _, kwargs = call.call_args
            assert kwargs["json"]["repository"] == "owner/repo"
            assert kwargs["json"]["issue_number"] == 42


class TestIssueHuntExecutorSubmitPR:
    def test_submit_pr_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(post_response=_mock_response(200, {"submission_id": "s1"}))
            result = asyncio.run(executor.submit_pr("b1", "http://pr.url"))
            assert result.success is True
            assert "Submitted PR" in result.message

    def test_submit_pr_passes_pr_url(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(post_response=_mock_response(200, {"submission_id": "s1"}))
            asyncio.run(executor.submit_pr("b1", "http://pr.url"))
            call = mock_http.return_value.post
            _, kwargs = call.call_args
            assert kwargs["json"]["pull_request_url"] == "http://pr.url"


class TestIssueHuntExecutorGetBounty:
    def test_get_bounty_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(get_response=_mock_response(200, {"id": "b1", "amount": 500}))
            result = asyncio.run(executor.get_bounty("b1"))
            assert result.success is True
            assert result.data["id"] == "b1"

    def test_get_bounty_not_found(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(get_response=_mock_response(404, {"error": "not found"}))
            result = asyncio.run(executor.get_bounty("nonexistent"))
            assert result.success is False


class TestIssueHuntExecutorDispatch:
    def test_unknown_action(self, executor):
        result = asyncio.run(executor.execute("nonexistent"))
        assert result.success is False
        assert "Unknown action" in result.error

    def test_dispatch_claim(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient(post_response=_mock_response(200, {"claim_id": "c1"}))
            result = asyncio.run(executor.execute("claim_issue", bounty_id="b1", repo="a/b", issue_number=1))
            assert result.success is True
