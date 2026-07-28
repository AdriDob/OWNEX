"""Tests for FreelancerExecutor — bid, submit deliverables, milestones, list bids."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.opportunity.executors.freelancer_executor import FreelancerExecutor


class _MockClient:
    def __init__(self):
        self.post = AsyncMock()
        self.get = AsyncMock()

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
    return FreelancerExecutor({"api_token": "test-token", "user_id": "123"})


@pytest.fixture
def executor_no_token():
    return FreelancerExecutor({"user_id": "123"})


class TestFreelancerExecutorNoToken:
    def test_bid_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.bid_on_project(1, 100.0, 7, "fix bug"))
        assert result.success is False
        assert "FREELANCER_API_TOKEN" in result.error

    def test_submit_deliverable_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.submit_deliverable(1))
        assert result.success is False
        assert "FREELANCER_API_TOKEN" in result.error

    def test_request_milestone_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.request_milestone_release(1, 1))
        assert result.success is False
        assert "FREELANCER_API_TOKEN" in result.error

    def test_get_project_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.get_project(1))
        assert result.success is False
        assert "FREELANCER_API_TOKEN" in result.error

    def test_list_bids_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.list_my_bids())
        assert result.success is False
        assert "FREELANCER_API_TOKEN" in result.error


class TestFreelancerExecutorBid:
    def test_bid_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"bid_id": "b1", "status": "active"})
            result = asyncio.run(executor.bid_on_project(42, 500.0, 14, "I can fix this", 100.0))
            assert result.success is True
            assert "Bid $500.0" in result.message

    def test_bid_uses_correct_endpoint(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"bid_id": "b1"})
            asyncio.run(executor.bid_on_project(42, 500.0, 14, "desc"))
            url = mock_http.return_value.post.call_args[0][0]
            assert "projects/42/bids" in url

    def test_bid_passes_correct_payload(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"bid_id": "b1"})
            asyncio.run(executor.bid_on_project(42, 500.0, 14, "I can fix this", 50.0))
            _, kwargs = mock_http.return_value.post.call_args
            assert kwargs["json"]["amount"] == 500.0
            assert kwargs["json"]["milestone_percentage"] == 50.0

    def test_bid_api_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(400, {"error": "insufficient balance"})
            result = asyncio.run(executor.bid_on_project(42, 500.0, 14, "desc"))
            assert result.success is False


class TestFreelancerExecutorDeliverable:
    def test_submit_deliverable_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"deliverable_id": "d1"})
            result = asyncio.run(
                executor.submit_deliverable(42, files=[{"name": "fix.py", "url": "http://..."}], message="done")
            )
            assert result.success is True
            assert result.data["deliverable_id"] == "d1"


class TestFreelancerExecutorMilestone:
    def test_milestone_release_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(200, {"status": "released"})
            result = asyncio.run(executor.request_milestone_release(42, 1))
            assert result.success is True
            assert "Milestone 1 release requested" in result.message


class TestFreelancerExecutorGetProject:
    def test_get_project_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {"id": 42, "title": "Fix bug"})
            result = asyncio.run(executor.get_project(42))
            assert result.success is True
            assert result.data["title"] == "Fix bug"


class TestFreelancerExecutorListBids:
    def test_list_bids_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {"bids": []})
            result = asyncio.run(executor.list_my_bids())
            assert result.success is True

    def test_list_bids_with_status_filter(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {"bids": []})
            asyncio.run(executor.list_my_bids("active"))
            call = mock_http.return_value.get.call_args
            assert call[1]["params"]["status"] == "active"


class TestFreelancerExecutorDispatch:
    def test_unknown_action(self, executor):
        result = asyncio.run(executor.execute("nonexistent"))
        assert result.success is False
        assert "Unknown action" in result.error

    def test_dispatch_bid(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"bid_id": "b1"})
            result = asyncio.run(
                executor.execute("bid_on_project", project_id=1, bid_amount=100, period=7, description="desc")
            )
            assert result.success is True
