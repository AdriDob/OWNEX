"""Tests for MindriftExecutor — claim tasks, submit solutions, get tasks, and top-level claim()."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.opportunity.executors.mindrift_executor import MindriftExecutor, claim


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
    return MindriftExecutor({"token": "test-token", "base_url": "https://api.mindrift.io/v1"})


@pytest.fixture
def executor_no_token():
    return MindriftExecutor({"base_url": "https://api.mindrift.io/v1"})


class TestMindriftExecutorNoToken:
    def test_claim_task_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.claim_task("t1"))
        assert result.success is False
        assert "MINDRIFT_EMAIL" in result.error

    def test_submit_task_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.submit_task("t1", "http://sol.url"))
        assert result.success is False
        assert "MINDRIFT_EMAIL" in result.error


class TestMindriftExecutorClaimTask:
    def test_claim_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"task_id": "t1"})
            result = asyncio.run(executor.claim_task("t1"))
            assert result.success is True
            assert result.action == "claim_task"

    def test_claim_http_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(409, {"error": "already claimed"})
            result = asyncio.run(executor.claim_task("t1"))
            assert result.success is False


class TestMindriftExecutorSubmitTask:
    def test_submit_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"status": "submitted"})
            result = asyncio.run(executor.submit_task("t1", "http://sol.url", "solution desc"))
            assert result.success is True

    def test_submit_with_default_description(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"status": "submitted"})
            asyncio.run(executor.submit_task("t1", "http://sol.url"))
            _, kwargs = mock_http.return_value.post.call_args
            assert "OWNEX CoderAgent" in kwargs["json"]["description"]


class TestMindriftExecutorGetTasks:
    def test_get_tasks_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {"tasks": [{"id": "t1"}]})
            result = asyncio.run(executor.get_tasks("open"))
            assert result.success is True
            assert len(result.data["tasks"]) == 1


class TestMindriftExecutorHealth:
    def test_health_check(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, {})
            result = asyncio.run(executor.health_check())
            assert result.success is True


class TestMindriftClaimTopLevel:
    def test_claim_with_specific_task_id(self):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.post.return_value = _mock_response(201, {"task_id": "t1"})
            with patch.dict("os.environ", {"MINDRIFT_EMAIL": "test@test.com"}):
                result = asyncio.run(claim("t1"))
                assert result.success is True

    def test_claim_finds_first_available(self):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, [{"id": "t1"}, {"id": "t2"}])
            mock_http.return_value.post.return_value = _mock_response(201, {"task_id": "t1"})
            with patch.dict("os.environ", {"MINDRIFT_EMAIL": "test@test.com"}):
                result = asyncio.run(claim())
                assert result.success is True

    def test_claim_no_available_tasks(self):
        with patch("httpx.AsyncClient") as mock_http:
            mock_http.return_value = _MockClient()
            mock_http.return_value.get.return_value = _mock_response(200, [])
            with patch.dict("os.environ", {"MINDRIFT_EMAIL": "test@test.com"}):
                result = asyncio.run(claim())
                assert result.success is False
                assert result.error is not None and "No open tasks" in result.error
