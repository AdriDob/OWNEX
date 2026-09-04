"""Tests for Web3/Blockchain Direct Work Adapters and Executors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from api.adapters.direct_work_immunefi import ImmunefiDweAdapter
from api.adapters.direct_work_code4rena import Code4renaDweAdapter
from core.opportunity.executors import get_executors
from cores.direct_work_engine.models import WorkPlatform


class MockAsyncClient:
    """Mock AsyncClient that can be used as async context manager."""

    def __init__(self, responses: list[dict]):
        self.responses = responses
        self.call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url: str, **kwargs):
        if self.call_count < len(self.responses):
            resp_data = self.responses[self.call_count]
            self.call_count += 1
        else:
            resp_data = {"status_code": 404, "json": {}}

        mock_resp = MagicMock()
        mock_resp.status_code = resp_data.get("status_code", 200)
        mock_resp.json = MagicMock(return_value=resp_data.get("json", []))
        return mock_resp


def make_mock_client_factory(responses: list[dict]):
    """Factory that creates a mock AsyncClient class."""

    def factory(*args, **kwargs):
        return MockAsyncClient(responses)

    return factory


class TestImmunefiDweAdapter:
    """Tests for Immunefi Discovery Adapter."""

    def test_adapter_creation(self) -> None:
        adapter = ImmunefiDweAdapter()
        assert adapter.source.name == "immunefi"
        assert adapter.source.platform == WorkPlatform.IMMUNEFI
        assert adapter.source.tier == 1
        assert adapter.source.analysis_cadence_hours == 6

    @pytest.mark.asyncio
    async def test_validate_connection_mock(self) -> None:
        adapter = ImmunefiDweAdapter()
        with patch("httpx.AsyncClient", make_mock_client_factory([{"status_code": 200, "json": {}}])):
            result = await adapter.validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_fetch_opportunities_mock(self) -> None:
        adapter = ImmunefiDweAdapter()
        mock_program = {
            "id": "1inch-SmartContracts",
            "name": "1inch Smart Contracts",
            "description": "DeFi protocol on Ethereum",
            "assets": [{"name": "Ethereum"}, {"name": "Polygon"}],
            "networks": ["ethereum", "polygon"],
            "rewards": [{"asset": "USDC", "max": 500000, "min": 1000}],
            "scope": [{"type": "smart_contract", "url": "https://github.com/1inch"}],
        }

        with patch("httpx.AsyncClient", make_mock_client_factory([{"status_code": 200, "json": [mock_program]}])):
            opportunities = await adapter.fetch_opportunities()
            assert len(opportunities) == 1
            opp = opportunities[0]
            assert opp.platform == WorkPlatform.IMMUNEFI
            assert "1inch" in opp.title
            assert opp.payment > 0
            assert opp.currency == "USD"
            assert opp.payment_method.value == "crypto"
            assert opp.employment_type.value == "bounty"
            assert opp.entry_mechanism.value == "assessment"
            # technology_tags extracted from rewards/assets (mock dependent)
            assert isinstance(opp.technology_tags, list)


class TestCode4renaDweAdapter:
    """Tests for Code4rena Discovery Adapter."""

    def test_adapter_creation(self) -> None:
        adapter = Code4renaDweAdapter()
        assert adapter.source.name == "code4rena"
        assert adapter.source.platform == WorkPlatform.CODE4RENA
        assert adapter.source.tier == 1
        assert adapter.source.analysis_cadence_hours == 12

    @pytest.mark.asyncio
    async def test_validate_connection_mock(self) -> None:
        adapter = Code4renaDweAdapter()
        with patch("httpx.AsyncClient", make_mock_client_factory([{"status_code": 200, "json": {}}])):
            result = await adapter.validate_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_fetch_opportunities_mock(self) -> None:
        adapter = Code4renaDweAdapter()
        mock_contest = {
            "id": "2024-03-example",
            "name": "Example Protocol Audit",
            "description": "Audit of Example Protocol smart contracts",
            "language": "Solidity",
            "repo": "https://github.com/example/protocol",
            "scope": "Contracts in src/",
            "totalPrizes": 200000,
            "maxReward": 50000,
            "minReward": 1000,
        }

        with patch("httpx.AsyncClient", make_mock_client_factory([{"status_code": 200, "json": [mock_contest]}])):
            opportunities = await adapter.fetch_opportunities()
            assert len(opportunities) == 1
            opp = opportunities[0]
            assert opp.platform == WorkPlatform.CODE4RENA
            assert "Example Protocol" in opp.title
            assert opp.payment > 0
            assert opp.currency == "USD"
            assert opp.payment_method.value == "crypto"
            assert opp.employment_type.value == "bounty"
            assert opp.entry_mechanism.value == "assessment"
            # technology_tags extracted from language/category (mock dependent)
            assert isinstance(opp.technology_tags, list)


class TestCode4renaExecutor:
    """Tests for Code4rena Executor."""

    def test_executor_creation(self) -> None:
        executors = get_executors({"code4rena": {"token": "test-token"}})
        assert "code4rena" in executors
        executor = executors["code4rena"]
        assert executor.platform == "code4rena"

    def test_executor_without_token(self) -> None:
        executors = get_executors({})
        assert "code4rena" in executors
        executor = executors["code4rena"]
        assert executor.config.get("token") is None


class TestImmunefiExecutor:
    """Tests for Immunefi Executor (already exists in core)."""

    def test_executor_creation(self) -> None:
        executors = get_executors({"immunefi": {"token": "test-key"}})
        assert "immunefi" in executors
        executor = executors["immunefi"]
        assert executor.platform == "immunefi"

    def test_executor_without_token(self) -> None:
        executors = get_executors({})
        assert "immunefi" in executors
        executor = executors["immunefi"]
        assert executor.config.get("token") is None


class TestWeb3AdaptersIntegration:
    """Integration tests for web3 adapters in the engine."""

    def test_build_default_adapters_includes_web3(self) -> None:
        from api.adapters.legacy import build_default_adapters

        adapters = build_default_adapters()
        platform_names = {a.source.platform.value for a in adapters}
        assert "immunefi" in platform_names
        assert "code4rena" in platform_names

    def test_engine_registers_web3_adapters(self) -> None:
        from api.routers import direct_work as dw

        engine = dw.get_engine()
        registered = engine.discovery.get_registered_platforms()
        assert WorkPlatform.IMMUNEFI in registered
        assert WorkPlatform.CODE4RENA in registered
