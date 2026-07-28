"""Tests for OpireExecutor — claim bounties, submit work, get bounties."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.opportunity.executors.opire_executor import OpireExecutor


@pytest.fixture
def executor():
    return OpireExecutor({"token": "test-token", "base_url": "https://api.opire.dev/v1"})


@pytest.fixture
def executor_no_token():
    return OpireExecutor({"base_url": "https://api.opire.dev/v1"})


def _mock_response(status: int, json_data: dict | None = None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or {}
    resp.text = str(json_data or {})
    return resp


def _setup_client(patch_obj, response):
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    patch_obj.return_value = client
    return client


class TestOpireExecutorNoToken:
    def test_claim_bounty_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.claim_bounty("b1"))
        assert result.success is False
        assert "OPIRE_TOKEN" in result.error

    def test_submit_work_fails_without_token(self, executor_no_token):
        result = asyncio.run(executor_no_token.submit_work("b1", "http://pr.url"))
        assert result.success is False
        assert "OPIRE_TOKEN" in result.error


class TestOpireExecutorClaimBounty:
    def test_claim_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(201, {"claim_id": "c1"}))
            result = asyncio.run(executor.claim_bounty("b1"))
            assert result.success is True
            assert result.action == "claim_bounty"
            assert result.target == "b1"

    def test_claim_http_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(400, {"error": "bad request"}))
            result = asyncio.run(executor.claim_bounty("b1"))
            assert result.success is False
            assert "HTTP 400" in result.error

    def test_claim_network_error(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=ConnectionError("network unreachable"))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = client
            result = asyncio.run(executor.claim_bounty("b1"))
            assert result.success is False

    def test_claim_uses_correct_endpoint(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            client = AsyncMock()
            client.post = AsyncMock(return_value=_mock_response(201, {"claim_id": "c1"}))
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = client
            asyncio.run(executor.claim_bounty("b1"))
            client.post.assert_called_once()
            url = client.post.call_args[0][0]
            assert "bounties/b1/claim" in url


class TestOpireExecutorSubmitWork:
    def test_submit_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(201, {"status": "submitted"}))
            result = asyncio.run(executor.submit_work("b1", "http://pr.url", "fix: resolved issue"))
            assert result.success is True
            assert result.action == "submit_work"

    def test_submit_with_default_description(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            client = AsyncMock()
            resp = _mock_response(201, {"status": "submitted"})
            client.post = AsyncMock(return_value=resp)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = client
            asyncio.run(executor.submit_work("b1", "http://pr.url"))
            _, kwargs = client.post.call_args
            assert "OWNEX CoderAgent" in kwargs["json"]["description"]

    def test_submit_uses_correct_endpoint(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            client = AsyncMock()
            resp = _mock_response(201, {"status": "submitted"})
            client.post = AsyncMock(return_value=resp)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = client
            asyncio.run(executor.submit_work("b1", "http://pr.url"))
            url = client.post.call_args[0][0]
            assert "bounties/b1/submit" in url


class TestOpireExecutorGetBounties:
    def test_get_bounties_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(200, {"bounties": []}))
            result = asyncio.run(executor.get_bounties("open"))
            assert result.success is True
            assert result.action == "get_bounties"

    def test_get_bounties_filters_by_status(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            client = AsyncMock()
            resp = _mock_response(200, {"bounties": []})
            client.get = AsyncMock(return_value=resp)
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = client
            asyncio.run(executor.get_bounties("claimed"))
            assert client.get.call_args[1]["params"]["status"] == "claimed"


class TestOpireExecutorGetBounty:
    def test_get_bounty_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(200, {"id": "b1"}))
            result = asyncio.run(executor.get_bounty("b1"))
            assert result.success is True

    def test_get_bounty_not_found(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(404, {"error": "not found"}))
            result = asyncio.run(executor.get_bounty("nonexistent"))
            assert result.success is False


class TestOpireExecutorHealthCheck:
    def test_health_check_success(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(200, {"status": "ok"}))
            result = asyncio.run(executor.health_check())
            assert result.success is True

    def test_health_check_down(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(503, {}))
            result = asyncio.run(executor.health_check())
            assert result.success is False


class TestOpireExecutorDispatch:
    def test_execute_unknown_action(self, executor):
        result = asyncio.run(executor.execute("nonexistent"))
        assert result.success is False
        assert "Unknown action" in result.error

    def test_execute_claim_bounty(self, executor):
        with patch("httpx.AsyncClient") as mock_http:
            _setup_client(mock_http, _mock_response(201, {}))
            result = asyncio.run(executor.execute("claim_bounty", bounty_id="b1"))
            assert result.success is True
